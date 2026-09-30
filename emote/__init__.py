import sys

import gi
from setproctitle import setproctitle

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from emote import config, css, emojis, picker, user_data
from emote.x11_hotkey import X11Hotkey
from emote.wayland_paste import WaylandPaste, clear_restore_token
from emote.wayland_shortcut import WaylandShortcut


class EmoteApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=config.app_id)
        self.started = False
        self.picker_window = None
        self.hotkey = None
        self.wayland_paste = None
        self.wayland_shortcut = None
        self.wayland_shortcut_checked = False
        self.wayland_shortcut_needs_setup = False
        self.pending_wayland_shortcut_setup = False
        self.wayland_shortcut_onboarding = False
        self.pending_activation_token = None
        self.wayland_paste_error_pending = False

    def do_activate(self):
        if not self.started:
            self.start_daemon()
            if not user_data.load_shown_welcome():
                user_data.update_shown_welcome()
                self.create_picker_window()
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
        else:
            self.wayland_shortcut = WaylandShortcut(
                on_activated=self.on_hotkey,
                on_bound=self.on_wayland_shortcut_bound,
                on_missing=self.on_wayland_shortcut_missing,
                on_unavailable=self.on_wayland_shortcut_unavailable,
            )
            # GNOME may return no shortcuts for a new session until BindShortcuts
            # is called, even when the app already has a saved binding.
            if user_data.load_wayland_global_shortcut_choice() is True:
                self.wayland_shortcut.bind()
            else:
                self.wayland_shortcut.enable()
            # Restore an approved keyboard-control session before the picker is
            # needed, so the first emoji cannot outrun portal negotiation.
            self.maybe_start_wayland_paste()

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

    def on_hotkey(self, activation_token=None):
        if self.picker_window and self.picker_window.get_visible():
            self.close_picker_window()
        else:
            self.pending_activation_token = activation_token
            self.activate()

    def update_accelerator(self, accel, label):
        user_data.update_accelerator(accel, label)
        self.set_accelerator()

    def create_picker_window(self):
        self.picker_window = picker.EmojiPicker(
            application=self,
            update_accelerator=self.update_accelerator,
        )
        self.prepare_wayland_picker_focus()
        self.picker_window.present()
        self.on_picker_presented()

    def prepare_wayland_picker_focus(self):
        if not config.is_wayland:
            return
        if self.pending_activation_token:
            self.picker_window.set_startup_id(self.pending_activation_token)
            self.pending_activation_token = None
        choice = user_data.load_wayland_auto_paste_choice()
        if choice is None or (
            choice is True
            and (self.wayland_paste is None or not self.wayland_paste.is_ready)
        ):
            self.picker_window.begin_wayland_request()

    def on_picker_presented(self):
        if not config.is_wayland:
            return
        if (
            self.wayland_paste_error_pending
            and self.picker_window.get_visible_dialog() is None
        ):
            self.wayland_paste_error_pending = False
            GLib.idle_add(self.picker_window.show_wayland_paste_unavailable)
            return
        if not self.wayland_shortcut_checked:
            return
        if self.pending_wayland_shortcut_setup:
            return
        if (
            self.wayland_shortcut_needs_setup
            or user_data.load_wayland_global_shortcut_choice() is None
        ):
            GLib.idle_add(self.begin_wayland_shortcut_setup)
        elif user_data.load_wayland_auto_paste_choice() is None:
            GLib.idle_add(self.picker_window.show_wayland_paste_choice)
        else:
            self.maybe_start_wayland_paste()

    def begin_wayland_shortcut_setup(self):
        if (
            not self.picker_window
            or not self.picker_window.get_visible()
            or self.pending_wayland_shortcut_setup
        ):
            return GLib.SOURCE_REMOVE
        self.wayland_shortcut_needs_setup = False
        self.set_wayland_global_shortcut(onboarding=True)
        return GLib.SOURCE_REMOVE

    def continue_wayland_setup(self):
        if not self.picker_window or not self.picker_window.get_visible():
            return GLib.SOURCE_REMOVE
        if user_data.load_wayland_auto_paste_choice() is None:
            GLib.idle_add(self.picker_window.show_wayland_paste_choice)
        else:
            self.maybe_start_wayland_paste()
        return GLib.SOURCE_REMOVE

    def set_wayland_global_shortcut(self, onboarding=False):
        if not config.is_wayland or not self.wayland_shortcut:
            return False

        if self.wayland_shortcut.is_registered:
            # v1 BindShortcuts restores saved entries, including disabled ones;
            # it is not an editor. Do not promise to reopen setup for them.
            self.picker_window.show_wayland_shortcut_unassigned(onboarding)
            return False

        self.pending_wayland_shortcut_setup = True
        self.wayland_shortcut_onboarding = onboarding
        if self.picker_window and self.picker_window.get_visible():
            self.picker_window.begin_wayland_request()
            self.picker_window.get_portal_parent(self.bind_wayland_shortcut)
        else:
            self.bind_wayland_shortcut("")
        return True

    def bind_wayland_shortcut(self, parent_window):
        self.wayland_shortcut.bind(parent_window)

    def is_wayland_shortcut_registered(self):
        return bool(self.wayland_shortcut and self.wayland_shortcut.is_registered)

    def on_wayland_shortcut_bound(self, label):
        GLib.idle_add(self.handle_wayland_shortcut_bound, label)

    def handle_wayland_shortcut_bound(self, label):
        self.wayland_shortcut_checked = True
        self.wayland_shortcut_needs_setup = False
        user_data.update_wayland_global_shortcut_choice(True)
        user_data.update_wayland_global_shortcut_label(label)

        if self.pending_wayland_shortcut_setup:
            onboarding = self.wayland_shortcut_onboarding
            self.pending_wayland_shortcut_setup = False
            self.wayland_shortcut_onboarding = False
            if self.picker_window:
                self.picker_window.end_wayland_request(present=True)
            self.refresh_wayland_shortcut_preferences()
            if onboarding:
                self.continue_wayland_setup()
        else:
            self.refresh_wayland_shortcut_preferences()
            if self.picker_window and self.picker_window.get_visible():
                self.on_picker_presented()
        return GLib.SOURCE_REMOVE

    def on_wayland_shortcut_missing(self, registered=False):
        GLib.idle_add(self.handle_wayland_shortcut_missing, registered)

    def handle_wayland_shortcut_missing(self, registered=False):
        self.wayland_shortcut_checked = True
        pending = self.pending_wayland_shortcut_setup
        onboarding = self.wayland_shortcut_onboarding
        previous_choice = user_data.load_wayland_global_shortcut_choice()
        self.pending_wayland_shortcut_setup = False
        self.wayland_shortcut_onboarding = False
        self.wayland_shortcut_needs_setup = (
            not pending and not registered and previous_choice is None
        )
        user_data.update_wayland_global_shortcut_choice(False)
        if self.picker_window:
            self.picker_window.end_wayland_request(present=True)
        self.refresh_wayland_shortcut_preferences()
        if pending and onboarding:
            self.continue_wayland_setup()
        elif not pending and self.picker_window and self.picker_window.get_visible():
            self.on_picker_presented()
        return GLib.SOURCE_REMOVE

    def on_wayland_shortcut_unavailable(self, error):
        GLib.idle_add(self.handle_wayland_shortcut_unavailable, error)

    def handle_wayland_shortcut_unavailable(self, _error):
        self.wayland_shortcut_checked = True
        pending = self.pending_wayland_shortcut_setup
        onboarding = self.wayland_shortcut_onboarding
        self.pending_wayland_shortcut_setup = False
        self.wayland_shortcut_onboarding = False
        self.wayland_shortcut_needs_setup = False
        if pending:
            user_data.update_wayland_global_shortcut_choice(False)

        if self.picker_window:
            self.picker_window.end_wayland_request(present=True)
            self.refresh_wayland_shortcut_preferences()
            if self.picker_window.get_visible() and pending and onboarding:
                self.continue_wayland_setup()
            elif self.picker_window.get_visible():
                self.on_picker_presented()
        return GLib.SOURCE_REMOVE

    def refresh_wayland_shortcut_preferences(self):
        if not self.picker_window:
            return
        # Adw.Dialog can temporarily disappear from get_visible_dialog() while
        # a desktop-owned portal window has focus. Keep using the dialog Emote
        # presented so its disabled “Opening…” button is always restored.
        dialog = self.picker_window.get_visible_dialog() or getattr(
            self.picker_window, "active_dialog", None
        )
        if dialog and hasattr(dialog, "refresh_wayland_global_shortcut"):
            dialog.refresh_wayland_global_shortcut()

    def maybe_start_wayland_paste(self):
        if (
            not config.is_wayland
            or user_data.load_wayland_auto_paste_choice() is not True
        ):
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
            self.picker_window.begin_wayland_request()
        self.wayland_paste.ensure_started()

    def set_wayland_auto_paste(self, enabled):
        if not config.is_wayland:
            return
        user_data.update_wayland_auto_paste_choice(enabled)
        if enabled:
            self.maybe_start_wayland_paste()
        else:
            if self.picker_window:
                self.picker_window.end_wayland_request(present=False)
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
            self.picker_window.end_wayland_request(present=True)
        return GLib.SOURCE_REMOVE

    def on_wayland_paste_unavailable(self, backend, _error):
        GLib.idle_add(self.handle_wayland_paste_unavailable, backend)

    def handle_wayland_paste_unavailable(self, backend):
        if self.wayland_paste is backend:
            self.wayland_paste_error_pending = True
            self.set_wayland_auto_paste(False)
            if self.picker_window and self.picker_window.get_visible():
                self.wayland_paste_error_pending = False
                if self.picker_window.get_visible_dialog() is None:
                    self.picker_window.present()
                self.picker_window.show_wayland_paste_unavailable()
        return GLib.SOURCE_REMOVE

    def paste_wayland(self):
        if user_data.load_wayland_auto_paste_choice() is not True:
            return GLib.SOURCE_REMOVE
        if self.wayland_paste and self.wayland_paste.paste():
            return GLib.SOURCE_REMOVE
        user_data.update_wayland_auto_paste_choice(False)
        if self.wayland_paste:
            self.wayland_paste.close()
            self.wayland_paste = None
        self.wayland_paste_error_pending = True
        self.activate()
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
        if self.wayland_shortcut:
            self.wayland_shortcut.close()
        if self.hotkey:
            self.hotkey.close()
        if self.picker_window:
            self.picker_window.release_portal_parent()
            self.picker_window.destroy()
            self.picker_window = None
        Gtk.Application.do_shutdown(self)


def main():
    return EmoteApplication().run(sys.argv)
