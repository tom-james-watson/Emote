"""Restore a background clipboard through the RemoteDesktop session's permission.

Mutter rejects ordinary Wayland selection changes after the picker loses focus.
A Clipboard portal session must live as long as it serves the restored data.
Input devices are released after the paste; the session ends on a new copy or
when automatic paste is disabled.
"""

import threading
import time
import uuid

from gi.repository import Gdk, Gio, GLib

BUS = "org.freedesktop.portal.Desktop"
PATH = "/org/freedesktop/portal/desktop"
CLIPBOARD = "org.freedesktop.portal.Clipboard"
REMOTE_DESKTOP = "org.freedesktop.portal.RemoteDesktop"


class ClipboardPermissionError(RuntimeError):
    pass


def negotiate(portal, restore_token):
    # python-libei 0.5.2 has no pre-Start clipboard hook. Reuse its bounded
    # request/Response handling rather than running a second consent session.
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    code, results = portal._request(
        bus,
        Gio,
        GLib,
        BUS,
        REMOTE_DESKTOP,
        "CreateSession",
        "(a{sv})",
        (),
        {"session_handle_token": GLib.Variant("s", uuid.uuid4().hex)},
        60,
    )
    if code != 0:
        raise portal.PortalDeniedError("CreateSession")
    handle = results["session_handle"]
    session = None
    lease = None
    try:
        options = {
            "types": GLib.Variant("u", int(portal.DeviceType.KEYBOARD)),
            "persist_mode": GLib.Variant("u", int(portal.PersistMode.UNTIL_REVOKED)),
        }
        if restore_token:
            options["restore_token"] = GLib.Variant("s", restore_token)
        code, _ = portal._request(
            bus,
            Gio,
            GLib,
            BUS,
            REMOTE_DESKTOP,
            "SelectDevices",
            "(oa{sv})",
            (handle,),
            options,
            60,
        )
        if code != 0:
            raise portal.PortalDeniedError("SelectDevices")
        bus.call_sync(
            BUS,
            PATH,
            CLIPBOARD,
            "RequestClipboard",
            GLib.Variant("(oa{sv})", (handle, {})),
            None,
            Gio.DBusCallFlags.NONE,
            10000,
            None,
        )
        lease = ClipboardLease(bus, handle)
        code, results = portal._request(
            bus,
            Gio,
            GLib,
            BUS,
            REMOTE_DESKTOP,
            "Start",
            "(osa{sv})",
            (handle, ""),
            {},
            60,
        )
        if code != 0:
            raise portal.PortalDeniedError("Start")
        if not results.get("clipboard_enabled"):
            raise ClipboardPermissionError(
                "the desktop did not grant clipboard restoration access"
            )
        fd = portal._call_for_fd(
            bus, Gio, GLib, BUS, REMOTE_DESKTOP, "ConnectToEIS", handle, 60
        )
        session = portal.RemoteDesktopSession(
            bus, fd, results.get("restore_token"), handle
        )
        return session, lease
    except BaseException as error:
        if lease is not None:
            lease.close()
        if session is not None:
            session.close()
        else:
            portal._close_session(bus, Gio, GLib, BUS, handle)
        if isinstance(error, ClipboardPermissionError) and restore_token:
            # GNOME restores the old clipboard grant verbatim. A keyboard-only
            # token needs one new consent request before it can include clipboard.
            return negotiate(portal, None)
        raise


class ClipboardLease:
    def __init__(self, bus, handle):
        self.bus = bus
        self.handle = handle
        self.provider = None
        self.claimed = False
        self.revoked = False
        self.finished = threading.Event()
        self.on_external_copy = None
        self.subscription = bus.signal_subscribe(
            BUS,
            CLIPBOARD,
            None,
            PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self._signal,
        )
        self.closed_subscription = bus.signal_subscribe(
            BUS,
            "org.freedesktop.portal.Session",
            "Closed",
            handle,
            None,
            Gio.DBusSignalFlags.NONE,
            self._closed,
        )

    def _closed(self, *_args):
        if not self.finished.is_set():
            self.revoked = True
            self.finished.set()

    def _call(self, method, parameters, callback=None):
        self.bus.call(
            BUS,
            PATH,
            CLIPBOARD,
            method,
            parameters,
            None,
            Gio.DBusCallFlags.NONE,
            10000,
            None,
            callback,
        )

    def claim(self, provider):
        if self.finished.is_set():
            return
        if provider is None:
            # An empty format list clears portal ownership. GNOME's clipboard
            # manager can then resurrect the emoji; serve empty text instead.
            provider = Gdk.ContentProvider.new_for_bytes(
                "text/plain;charset=utf-8", GLib.Bytes.new(b"")
            )
        self.provider = provider
        formats = list(provider.ref_formats().get_mime_types())

        def done(bus, result):
            try:
                bus.call_finish(result)
            except GLib.Error as error:
                print("Could not restore clipboard:", error)
                self.finished.set()

        self._call(
            "SetSelection",
            GLib.Variant(
                "(oa{sv})", (self.handle, {"mime_types": GLib.Variant("as", formats)})
            ),
            done,
        )

    def watch(self, callback):
        # XWayland may withhold native Wayland ownership notifications from an
        # unfocused X11 client. The portal observes those copies independently.
        self.on_external_copy = callback

    def stop_watching(self):
        self.on_external_copy = None

    def _signal(self, _bus, _sender, _path, _interface, name, parameters):
        if self.finished.is_set():
            return
        values = parameters.unpack()
        if values[0] != self.handle:
            return
        if name == "SelectionOwnerChanged":
            is_owner = values[1].get("session_is_owner", False)
            if is_owner:
                self.claimed = True
            elif self.claimed:
                self.finished.set()
            elif self.on_external_copy is not None:
                self.on_external_copy()
        elif name == "SelectionTransfer":
            _, mime_type, serial = values
            self._transfer(mime_type, serial)

    def _transfer(self, mime_type, serial):
        provider = self.provider
        if provider is None:
            self._write_done(serial, False)
            return

        def opened(bus, result):
            try:
                reply, descriptors = bus.call_with_unix_fd_list_finish(result)
                fd = descriptors.get(reply.unpack()[0])
                stream = Gio.UnixOutputStream.new(fd, True)
            except GLib.Error as error:
                print("Could not serve restored clipboard:", error)
                self._write_done(serial, False)
                return

            def written(provider, result):
                success = False
                try:
                    success = provider.write_mime_type_finish(result)
                except GLib.Error as error:
                    print("Could not serve restored clipboard format:", error)

                def closed(stream, result):
                    try:
                        stream.close_finish(result)
                    except GLib.Error:
                        self._write_done(serial, False)
                    else:
                        self._write_done(serial, success)

                stream.close_async(GLib.PRIORITY_DEFAULT, None, closed)

            provider.write_mime_type_async(
                mime_type,
                stream,
                GLib.PRIORITY_DEFAULT,
                None,
                written,
            )

        self.bus.call_with_unix_fd_list(
            BUS,
            PATH,
            CLIPBOARD,
            "SelectionWrite",
            GLib.Variant("(ou)", (self.handle, serial)),
            GLib.VariantType.new("(h)"),
            Gio.DBusCallFlags.NONE,
            10000,
            None,
            None,
            opened,
        )

    def _write_done(self, serial, success):
        if not self.finished.is_set():
            self._call(
                "SelectionWriteDone",
                GLib.Variant("(oub)", (self.handle, serial, success)),
            )

    def wait(self, stop):
        deadline = time.monotonic() + 10
        while not stop.is_set() and not self.finished.wait(0.1):
            if not self.claimed and time.monotonic() > deadline:
                return

    def close(self):
        self.finished.set()
        self.bus.signal_unsubscribe(self.subscription)
        self.bus.signal_unsubscribe(self.closed_subscription)
        self.provider = None
