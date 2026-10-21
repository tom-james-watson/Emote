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


class ClipboardPermissionRequest:
    needs_portal = True
    cancelled = False

    def __init__(self, callback):
        self.callback = callback
        self._lock = threading.Lock()

    def finish(self, error=None):
        with self._lock:
            callback, self.callback = self.callback, None
        if callback is not None:
            callback(error)

    def use_portal(self, *_args):
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
        self._clipboard_request = None
        self._active_clipboard_lease = None

    @property
    def clipboard_pending(self):
        return self._clipboard_request is not None

    def request_clipboard(self, callback):
        lease = self._active_clipboard_lease
        if (
            lease is not None
            and not lease.finished.is_set()
            and not self._stop.is_set()
        ):
            callback(None)
            return

        def finished(error):
            self._clipboard_request = None
            callback(error)

        request = ClipboardPermissionRequest(finished)
        self._clipboard_request = request
        self._requests.put(request)

    @property
    def is_ready(self):
        return self._ready.is_set() and not self.clipboard_pending

    def ensure_started(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def paste(self, on_pasted=None):
        """Queue a paste after the initial permission request has finished."""
        if not self.is_ready:
            return False
        self._requests.put(on_pasted or True)
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
        if self._clipboard_request is not None:
            self._clipboard_request.finish(
                RuntimeError("Automatic paste was disabled.")
            )

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
                request = self._requests.get()
                if request is None or self._stop.is_set():
                    return
                self._open_session(ei, portal, paste=request)
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
        try:
            self._open_session_with_permission(ei, portal, paste)
        except Exception as error:
            if not isinstance(paste, ClipboardPermissionRequest):
                raise
            if self._keep_session_open:
                self._ready.clear()
            paste.finish(error)
            # Declining restoration must leave keyboard-only automatic paste usable.
            if self._keep_session_open and not self._stop.is_set():
                self._open_session(ei, portal, paste=False)

    def _open_session_with_permission(self, ei, portal, paste):
        lease = None
        upgrade = None
        if getattr(paste, "needs_portal", False):
            from emote import portal_clipboard

            session, lease = portal_clipboard.negotiate(portal, load_restore_token())
            self._active_clipboard_lease = lease
        else:
            session = portal.RemoteDesktopSession.negotiate(
                devices=portal.DeviceType.KEYBOARD,
                persist_mode=portal.PersistMode.UNTIL_REVOKED,
                restore_token=load_restore_token(),
            )
        try:
            with session:
                with self._state_lock:
                    if self._stop.is_set():
                        return
                    save_restore_token(session.restore_token)
                if session.restore_token is None:
                    raise PermissionNotSavedError(
                        "the desktop did not remember permission"
                    )
                if (
                    lease is not None
                    and not self._keep_session_open
                    and not isinstance(paste, ClipboardPermissionRequest)
                ):
                    paste.use_portal(lease.claim, lease.finished.set, lease.watch)
                sender = ei.Sender.create_for_fd(session.eis_fd, name="Emote")
                try:
                    upgrade = self._serve(
                        sender,
                        ei,
                        paste,
                        hold=self._keep_session_open,
                        lease=lease,
                    )
                finally:
                    sender.release()
                if (
                    lease is not None
                    and not self._keep_session_open
                    and not isinstance(paste, ClipboardPermissionRequest)
                ):
                    lease.wait(self._stop)
                    if lease.revoked:
                        raise SessionEndedError("the desktop ended clipboard access")
        finally:
            if lease is not None:
                lease.close()
                if self._active_clipboard_lease is lease:
                    self._active_clipboard_lease = None
        if upgrade is not None and not self._stop.is_set():
            # Replace KDE's keyboard-only session before asking for clipboard
            # access. Reuse the upgraded session, so consent is needed once.
            self._open_session(ei, portal, upgrade)
        elif isinstance(paste, ClipboardPermissionRequest):
            paste.finish(
                RuntimeError("Automatic paste was disabled.")
                if self._stop.is_set()
                else None
            )

    def _serve(self, sender, ei, paste, hold=None, lease=None):
        if hold is None:
            hold = self._keep_session_open
        pending = paste if hold and paste else None
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
                            if hold:
                                self._ready.clear()
                                announced_ready = False
                                # A held session can pause while the screen is locked.
                                first_keyboard_deadline = None

            if first_keyboard_deadline and time.monotonic() > first_keyboard_deadline:
                raise TimeoutError("the desktop did not provide a keyboard device")

            if device is not None:
                if hold:
                    with self._state_lock:
                        if self._stop.is_set():
                            return
                        self._ready.set()
                    if not announced_ready:
                        announced_ready = True
                        if self._on_ready:
                            self._on_ready(self)
                    if pending is not None:
                        request, pending = pending, None
                    else:
                        try:
                            request = self._requests.get_nowait()
                        except queue.Empty:
                            continue
                    if request is None or self._stop.is_set():
                        return
                    if getattr(request, "cancelled", False):
                        continue
                    if getattr(request, "needs_portal", False) and lease is None:
                        return request
                    if isinstance(request, ClipboardPermissionRequest):
                        request.finish()
                        continue
                    if lease is not None and getattr(request, "needs_portal", False):
                        request.use_portal(
                            lease.claim, lease.stop_watching, lease.watch
                        )
                    self._send_paste(device)
                    if callable(request):
                        request()
                    continue
                if isinstance(paste, ClipboardPermissionRequest):
                    return
                if (
                    paste
                    and not self._stop.is_set()
                    and not getattr(paste, "cancelled", False)
                ):
                    self._send_paste(device)
                    self._finish_input(sender, ei)
                    if callable(paste):
                        paste()
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
