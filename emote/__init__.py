import sys

import gi
from setproctitle import setproctitle

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from emote import config, css, emojis, picker, user_data
from emote.x11_hotkey import X11Hotkey


class EmoteApplication(Gtk.Application):
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
            self.picker_window.present()
        else:
            self.create_picker_window()

    def start_daemon(self):
        setproctitle("emote")
        css.load_css()
        emojis.init()
        self.apply_saved_theme()
        self.hold()  # Keep the shortcut service alive when the picker is closed.
        self.started = True

        if not config.is_wayland:
            self.hotkey = X11Hotkey(self.on_hotkey)
            self.set_accelerator()

        if config.is_flatpak:
            self.flatpak_autostart()

    def apply_saved_theme(self):
        theme = user_data.load_theme()
        gtk_settings = Gtk.Settings.get_default()
        if theme == user_data.DEFAULT_THEME:
            gtk_settings.reset_property("gtk-theme-name")
        else:
            gtk_settings.set_property("gtk-theme-name", theme)

    def flatpak_autostart(self):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
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
            )
        except Exception as exc:
            print("Failed to enable autostart:", exc)

    def set_accelerator(self):
        if self.hotkey:
            accel, _ = user_data.load_accelerator()
            self.hotkey.bind(accel)

    def on_hotkey(self):
        if self.picker_window:
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
        self.picker_window.connect("notify::visible", self.on_picker_visibility)
        self.picker_window.present()

    def on_picker_visibility(self, window, _property):
        if not window.get_visible() and self.picker_window is window:
            self.picker_window = None

    def close_picker_window(self):
        if self.picker_window:
            window = self.picker_window
            user_data.update_picker_size(*window.get_default_size())
            self.picker_window = None
            window.destroy()

    def do_shutdown(self):
        if self.hotkey:
            self.hotkey.close()
        Gtk.Application.do_shutdown(self)


def main():
    return EmoteApplication().run(sys.argv)
