import sys

import gi
from setproctitle import setproctitle

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from emote import config, css, emojis, picker, user_data
from emote.x11_hotkey import X11Hotkey
from emote.wayland_paste import WaylandPaste, clear_restore_token


class EmoteApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=config.app_id)
        self.started = False
        self.picker_window = None
        self.hotkey = None
        self.wayland_paste = None

    def do_activate(self):
        if not self.started:
            self.start_daemon()
            if not user_data.load_shown_welcome():
                self.create_picker_window(show_welcome=True)
                user_data.update_shown_welcome()
            return

        if self.picker_window:
            if not self.picker_window.get_visible():
                self.picker_window.prepare_for_open()
            self.prepare_wayland_picker_focus()
            self.picker_window.present()
            self.on_picker_presented()
        else:
            self.create_picker_window()

    def start_daemon(self):
        setproctitle("emote")
        css.load_css()
        emojis.init()
        self.hold()  # Keep the shortcut service alive when the picker is closed.
        self.started = True

        if not config.is_wayland:
            self.hotkey = X11Hotkey(self.on_hotkey)
            self.set_accelerator()

        if config.is_flatpak:
            self.flatpak_autostart()

    def flatpak_autostart(self):
        Gio.bus_get(Gio.BusType.SESSION, None, self.on_autostart_bus_ready)

    def on_autostart_bus_ready(self, _source, result):
        try:
            bus = Gio.bus_get_finish(result)
            bus.call(
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Background",
                "RequestBackground",
                GLib.Variant(
                    "(sa{sv})",
                    (
                        "",
                        {
                            "reason": GLib.Variant("s", "Emote autostart"),
                            "autostart": GLib.Variant("b", True),
                            "background": GLib.Variant("b", True),
                            "commandline": GLib.Variant("as", ["emote"]),
                        },
                    ),
                ),
                GLib.VariantType.new("(o)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                self.on_autostart_request_finished,
            )
        except Exception as exc:
            print("Failed to enable autostart:", exc)

    def on_autostart_request_finished(self, bus, result):
        try:
            bus.call_finish(result)
        except Exception as exc:
            print("Failed to enable autostart:", exc)

    def set_accelerator(self):
        if self.hotkey:
            accel, _ = user_data.load_accelerator()
            self.hotkey.bind(accel)

    def on_hotkey(self):
        if self.picker_window and self.picker_window.get_visible():
            self.close_picker_window()
        else:
            self.activate()

    def update_accelerator(self, accel, label):
        user_data.update_accelerator(accel, label)
        self.set_accelerator()

    def create_picker_window(self, show_welcome=False):
        self.picker_window = picker.EmojiPicker(
            application=self,
            update_accelerator=self.update_accelerator,
            show_welcome=show_welcome,
        )
        self.prepare_wayland_picker_focus()
        self.picker_window.present()
        self.on_picker_presented()

    def prepare_wayland_picker_focus(self):
        if not config.is_wayland:
            return
        choice = user_data.load_wayland_auto_paste_choice()
        if choice is None or (
            choice is True
            and (self.wayland_paste is None or not self.wayland_paste.is_ready)
        ):
            self.picker_window.begin_wayland_permission()

    def on_picker_presented(self):
        if not config.is_wayland:
            return
        if user_data.load_wayland_auto_paste_choice() is None:
            GLib.idle_add(self.picker_window.show_wayland_paste_choice)
        else:
            self.maybe_start_wayland_paste()

    def maybe_start_wayland_paste(self):
        if not config.is_wayland or user_data.load_wayland_auto_paste_choice() is not True:
            return
        if self.wayland_paste is None:
            self.wayland_paste = WaylandPaste(
                on_ready=self.on_wayland_paste_ready,
                on_unavailable=self.on_wayland_paste_unavailable,
            )
        if (
            self.picker_window
            and self.picker_window.get_visible()
            and not self.wayland_paste.is_ready
        ):
            self.picker_window.begin_wayland_permission()
        self.wayland_paste.ensure_started()

    def set_wayland_auto_paste(self, enabled):
        if not config.is_wayland:
            return
        user_data.update_wayland_auto_paste_choice(enabled)
        if enabled:
            if self.picker_window and self.picker_window.get_visible():
                self.maybe_start_wayland_paste()
        else:
            if self.picker_window:
                self.picker_window.end_wayland_permission(present=False)
            if self.wayland_paste:
                self.wayland_paste.close(discard_token=True)
                self.wayland_paste = None
            else:
                try:
                    clear_restore_token()
                except OSError as exc:
                    print("Failed to remove Wayland auto-paste permission:", exc)

    def on_wayland_paste_ready(self, backend):
        GLib.idle_add(self.handle_wayland_paste_ready, backend)

    def handle_wayland_paste_ready(self, backend):
        if self.wayland_paste is backend and self.picker_window:
            self.picker_window.end_wayland_permission(present=True)
        return GLib.SOURCE_REMOVE

    def on_wayland_paste_unavailable(self, backend, _error):
        GLib.idle_add(self.handle_wayland_paste_unavailable, backend)

    def handle_wayland_paste_unavailable(self, backend):
        if self.wayland_paste is backend:
            self.set_wayland_auto_paste(False)
            if self.picker_window and self.picker_window.get_visible():
                if self.picker_window.get_visible_dialog() is None:
                    self.picker_window.present()
                self.picker_window.show_wayland_paste_unavailable()
        return GLib.SOURCE_REMOVE

    def paste_wayland(self):
        if self.wayland_paste and user_data.load_wayland_auto_paste_choice() is True:
            self.wayland_paste.paste()
        return GLib.SOURCE_REMOVE

    def close_picker_window(self):
        if self.picker_window and self.picker_window.get_visible():
            window = self.picker_window
            width, height = window.get_width(), window.get_height()
            if width > 0 and height > 0:
                user_data.update_picker_size(width, height)
            window.prepare_for_close()
            window.hide()

    def do_shutdown(self):
        if self.wayland_paste:
            self.wayland_paste.close()
        if self.hotkey:
            self.hotkey.close()
        if self.picker_window:
            self.picker_window.destroy()
            self.picker_window = None
        Gtk.Application.do_shutdown(self)


def main():
    return EmoteApplication().run(sys.argv)
