import sys

import gi
from setproctitle import setproctitle

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from emote import config, css, emojis, picker, user_data
from emote.x11_hotkey import X11Hotkey


class EmoteApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=config.app_id)
        self.started = False
        self.picker_window = None
        self.hotkey = None

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
            self.picker_window.present()
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
        self.picker_window.present()

    def close_picker_window(self):
        if self.picker_window and self.picker_window.get_visible():
            window = self.picker_window
            width, height = window.get_width(), window.get_height()
            if width > 0 and height > 0:
                user_data.update_picker_size(width, height)
            window.prepare_for_close()
            window.hide()

    def do_shutdown(self):
        if self.hotkey:
            self.hotkey.close()
        if self.picker_window:
            self.picker_window.destroy()
            self.picker_window = None
        Gtk.Application.do_shutdown(self)


def main():
    return EmoteApplication().run(sys.argv)
