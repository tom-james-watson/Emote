"""Paste through the RemoteDesktop portal and libei on Wayland."""

import os
from pathlib import Path
import queue
import select
import tempfile
import threading
import time

from emote import user_data

KEY_LEFTCTRL = 29
KEY_V = 47
TOKEN_PATH = Path(user_data.DATA_DIR) / "remote-desktop-token"


class PermissionNotSavedError(RuntimeError):
    pass


class SessionEndedError(RuntimeError):
    pass


def load_restore_token():
    try:
        return TOKEN_PATH.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None
    except OSError as exc:
        print("Failed to read Wayland auto-paste permission:", exc)
        return None


def save_restore_token(token):
    if token is None:
        clear_restore_token()
        return

    # A restore token is a standing permission to inject input. Keep it private.
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=TOKEN_PATH.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            os.chmod(temporary_path, 0o600)
            temporary_file.write(token)
        temporary_path.replace(TOKEN_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def clear_restore_token():
    TOKEN_PATH.unlink(missing_ok=True)


class WaylandPaste:
    def __init__(self, on_ready=None, on_unavailable=None, keep_session_open=False):
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._state_lock = threading.Lock()
        self._requests = queue.SimpleQueue()
        self._thread = None
        self._on_ready = on_ready
        self._on_unavailable = on_unavailable
        self._keep_session_open = keep_session_open

    @property
    def is_ready(self):
        return self._ready.is_set()

    def ensure_started(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def paste(self):
        """Queue a paste after the initial permission request has finished."""
        if not self._ready.is_set():
            return False
        self._requests.put(True)
        return True

    def close(self, discard_token=False):
        with self._state_lock:
            self._ready.clear()
            self._stop.set()
            if discard_token:
                try:
                    clear_restore_token()
                except OSError as exc:
                    print("Failed to remove Wayland auto-paste permission:", exc)
        self._requests.put(None)

    def _run(self):
        try:
            if self._stop.is_set():
                return
            from libei import ei, portal

            # KDE shows a notification for every new remote-control session.
            if self._keep_session_open:
                self._open_session(ei, portal, paste=False)
                return
            if load_restore_token() is None:
                self._open_session(ei, portal, paste=False)
            with self._state_lock:
                if self._stop.is_set():
                    return
                self._ready.set()
            if self._on_ready:
                self._on_ready(self)

            while not self._stop.is_set():
                if self._requests.get() is None or self._stop.is_set():
                    return
                self._open_session(ei, portal, paste=True)
        except Exception as exc:
            self._ready.clear()
            if not self._stop.is_set():
                print(
                    "Wayland auto-paste unavailable; emoji remains on clipboard:", exc
                )
                if self._on_unavailable:
                    self._on_unavailable(self, exc)
        finally:
            self._ready.clear()

    def _open_session(self, ei, portal, paste):
        with portal.RemoteDesktopSession.negotiate(
            devices=portal.DeviceType.KEYBOARD,
            persist_mode=portal.PersistMode.UNTIL_REVOKED,
            restore_token=load_restore_token(),
        ) as session:
            with self._state_lock:
                if self._stop.is_set():
                    return
                save_restore_token(session.restore_token)
            if session.restore_token is None:
                raise PermissionNotSavedError("the desktop did not remember permission")
            sender = ei.Sender.create_for_fd(session.eis_fd, name="Emote")
            try:
                self._serve(sender, ei, paste)
            finally:
                sender.release()

    def _serve(self, sender, ei, paste):
        device = None
        announced_ready = False
        first_keyboard_deadline = time.monotonic() + 10
        while not self._stop.is_set():
            readable, _, _ = select.select([sender.fd], [], [], 0.1)
            if readable:
                sender.dispatch()
                for event in sender.events:
                    if event.event_type == ei.EventType.DISCONNECT:
                        raise SessionEndedError("the desktop ended keyboard control")
                    if event.event_type == ei.EventType.SEAT_ADDED:
                        seat = event.seat
                        if ei.DeviceCapability.KEYBOARD in seat.capabilities:
                            seat.bind((ei.DeviceCapability.KEYBOARD,))
                    elif event.event_type == ei.EventType.DEVICE_RESUMED:
                        candidate = event.device
                        if ei.DeviceCapability.KEYBOARD in candidate.capabilities:
                            device = candidate
                            first_keyboard_deadline = None
                    elif event.event_type in (
                        ei.EventType.DEVICE_PAUSED,
                        ei.EventType.DEVICE_REMOVED,
                    ):
                        if event.device == device:
                            device = None
                            first_keyboard_deadline = time.monotonic() + 10
                            if self._keep_session_open:
                                self._ready.clear()
                                announced_ready = False
                                # A held session can pause while the screen is locked.
                                first_keyboard_deadline = None

            if first_keyboard_deadline and time.monotonic() > first_keyboard_deadline:
                raise TimeoutError("the desktop did not provide a keyboard device")

            if device is not None:
                if self._keep_session_open:
                    with self._state_lock:
                        if self._stop.is_set():
                            return
                        self._ready.set()
                    if not announced_ready:
                        announced_ready = True
                        if self._on_ready:
                            self._on_ready(self)
                    try:
                        request = self._requests.get_nowait()
                    except queue.Empty:
                        continue
                    if request is None or self._stop.is_set():
                        return
                    self._send_paste(device)
                    continue
                if paste and not self._stop.is_set():
                    self._send_paste(device)
                    self._finish_input(sender, ei)
                return

    def _finish_input(self, sender, ei):
        try:
            ping = sender.new_ping()
        except ei.LibraryNotFoundError:
            # libei before 1.4 has no round-trip acknowledgement. Allow the
            # desktop to process the key releases before closing the session.
            self._stop.wait(0.15)
            return
        try:
            ping.send()
            deadline = time.monotonic() + 10
            while not self._stop.is_set():
                select.select([sender.fd], [], [], 0.1)
                sender.dispatch()
                for event in sender.events:
                    if event.event_type == ei.EventType.DISCONNECT:
                        raise SessionEndedError("the desktop ended keyboard control")
                    if (
                        event.event_type == ei.EventType.PONG
                        and event.pong.id == ping.id
                    ):
                        return
                if time.monotonic() > deadline:
                    raise TimeoutError("the desktop did not acknowledge the paste")
        finally:
            ping.release()

    @staticmethod
    def _send_paste(device):
        device.start_emulating()
        try:
            device.keyboard_key(KEY_LEFTCTRL, True).frame()
            device.keyboard_key(KEY_V, True).frame()
            device.keyboard_key(KEY_V, False).frame()
            device.keyboard_key(KEY_LEFTCTRL, False).frame()
        finally:
            device.stop_emulating()
