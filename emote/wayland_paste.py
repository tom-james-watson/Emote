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
    def __init__(self, on_ready=None, on_unavailable=None):
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._discard_token = threading.Event()
        self._requests = queue.SimpleQueue()
        self._thread = None
        self._on_ready = on_ready
        self._on_unavailable = on_unavailable

    @property
    def is_ready(self):
        return self._ready.is_set()

    def ensure_started(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def paste(self):
        """Queue a shortcut only while the portal has an active keyboard."""
        if not self._ready.is_set():
            return False
        self._requests.put(True)
        return True

    def close(self, discard_token=False):
        self._ready.clear()
        self._stop.set()
        if discard_token:
            self._discard_token.set()
            try:
                clear_restore_token()
            except OSError as exc:
                print("Failed to remove Wayland auto-paste permission:", exc)

    def _run(self):
        try:
            from libei import ei, portal

            session = portal.RemoteDesktopSession.negotiate(
                devices=portal.DeviceType.KEYBOARD,
                persist_mode=portal.PersistMode.UNTIL_REVOKED,
                restore_token=load_restore_token(),
            )
            with session:
                if self._stop.is_set():
                    return
                try:
                    save_restore_token(session.restore_token)
                except OSError as exc:
                    print("Failed to save Wayland auto-paste permission:", exc)

                if self._stop.is_set():
                    return
                sender = ei.Sender.create_for_fd(session.eis_fd, name="Emote")
                try:
                    self._serve(sender, ei)
                    if not self._stop.is_set():
                        raise RuntimeError(
                            "the desktop ended the keyboard control session"
                        )
                finally:
                    self._ready.clear()
                    sender.release()
        except Exception as exc:
            self._ready.clear()
            if not self._stop.is_set():
                print(
                    "Wayland auto-paste unavailable; emoji remains on clipboard:", exc
                )
                if self._on_unavailable:
                    self._on_unavailable(self, exc)
        finally:
            if self._discard_token.is_set():
                try:
                    clear_restore_token()
                except OSError as exc:
                    print("Failed to remove Wayland auto-paste permission:", exc)

    def _serve(self, sender, ei):
        device = None
        first_keyboard_deadline = time.monotonic() + 10
        while not self._stop.is_set():
            readable, _, _ = select.select([sender.fd], [], [], 0.1)
            if readable:
                sender.dispatch()
                for event in sender.events:
                    if event.event_type == ei.EventType.DISCONNECT:
                        return
                    if event.event_type == ei.EventType.SEAT_ADDED:
                        seat = event.seat
                        if ei.DeviceCapability.KEYBOARD in seat.capabilities:
                            seat.bind((ei.DeviceCapability.KEYBOARD,))
                    elif event.event_type == ei.EventType.DEVICE_RESUMED:
                        candidate = event.device
                        if ei.DeviceCapability.KEYBOARD in candidate.capabilities:
                            device = candidate
                            first_keyboard_deadline = None
                            was_ready = self._ready.is_set()
                            self._ready.set()
                            if not was_ready and self._on_ready:
                                self._on_ready(self)
                    elif event.event_type in (
                        ei.EventType.DEVICE_PAUSED,
                        ei.EventType.DEVICE_REMOVED,
                    ):
                        if event.device == device:
                            device = None
                            self._ready.clear()

            if first_keyboard_deadline and time.monotonic() > first_keyboard_deadline:
                raise TimeoutError("the desktop did not provide a keyboard device")

            while True:
                try:
                    self._requests.get_nowait()
                except queue.Empty:
                    break
                if device is not None:
                    self._send_paste(device)

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
