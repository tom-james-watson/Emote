"""Picker dialogs and Wayland permission prompts."""

import os
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from emote import config, keyboard_shortcuts, settings, user_data


class PickerDialogs:
    def open_preferences(self):
        self.show_dialog(settings.Settings(self))

    def show_wayland_paste_choice(self):
        if (
            not self.get_visible()
            or user_data.load_wayland_auto_paste_choice() is not None
            or self.active_dialog is not None
            or self.get_visible_dialog() is not None
        ):
            return GLib.SOURCE_REMOVE

        dialog = Adw.AlertDialog.new("Enable automatic paste", None)
        body = Gtk.Label(
            label="To automatically paste the selected emoji into your current app, "
            "you must grant the “Remote Interaction” permission.",
            xalign=0,
            wrap=True,
            max_width_chars=42,
        )
        body.add_css_class("dim-label")
        dialog.set_extra_child(body)
        dialog.add_response("skip", "Skip")
        dialog.add_response("enable", "Enable")
        dialog.set_default_response("skip")
        dialog.set_close_response("skip")
        dialog.set_response_appearance("enable", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self.on_wayland_paste_choice)
        self.show_dialog(dialog)
        return GLib.SOURCE_REMOVE

    def on_wayland_paste_choice(self, _dialog, response):
        GLib.idle_add(self.apply_wayland_paste_choice, response == "enable")

    def apply_wayland_paste_choice(self, enabled):
        self.get_application().set_wayland_auto_paste(enabled)
        if not enabled and self.get_visible():
            self.present()
            self.get_application().on_picker_presented()
        return GLib.SOURCE_REMOVE

    def begin_wayland_request(self):
        # A desktop-managed Wayland setup dialog can take focus; keep the picker
        # open until the user has answered it.
        self.waiting_for_wayland_setup = True
        self.root.set_sensitive(False)
        if self.pending_inactive_close is not None:
            GLib.source_remove(self.pending_inactive_close)
            self.pending_inactive_close = None

    def end_wayland_request(self, present):
        was_waiting = self.waiting_for_wayland_setup
        self.waiting_for_wayland_setup = False
        self.root.set_sensitive(True)
        # Portal windows can take the pointer without producing a normal leave
        # event for this window. Do not let that stale hover state permanently
        # suppress close-on-blur after setup.
        self.pointer_in_picker = False
        # The compositor may already have returned focus before the portal
        # response reaches us. Preserve that state: resetting it to False here
        # means no subsequent notify::is-active signal is emitted, so the next
        # real blur cannot close the picker.
        # Never disarm an already presented picker merely because focus has
        # not returned from a closing dialog yet. This exact transient occurs
        # when the user skips automatic paste: the dialog-close callback arms
        # blur tracking, then set_wayland_auto_paste(False) arrives here while
        # GTK still reports the window inactive.
        self.was_active = self.was_active or self.is_active()
        if self.pending_inactive_close is not None:
            GLib.source_remove(self.pending_inactive_close)
            self.pending_inactive_close = None
        if (
            was_waiting
            and present
            and self.get_visible()
            and self.get_visible_dialog() is None
        ):
            self.present()

    def show_wayland_paste_unavailable(self):
        current_dialog = self.get_visible_dialog() or self.active_dialog
        if isinstance(current_dialog, settings.Settings):
            current_dialog.refresh_wayland_auto_paste()
        dialog = Adw.AlertDialog.new(
            "Automatic paste is off",
            "Emote could not get keyboard control from your desktop. Your emojis "
            "will still be copied to the clipboard. You can try again in Preferences.",
        )
        dialog.add_response("ok", "OK")
        dialog.set_close_response("ok")
        if current_dialog is not None:
            # The parent dialog already keeps the picker open, including
            # while Adwaita transitions between the two dialogs.
            dialog.present(current_dialog)
        else:
            # Track this before presenting it. get_visible_dialog() can still
            # be None during the opening animation after the portal closes;
            # an untracked modal could otherwise be hidden by close-on-blur.
            self.show_dialog(dialog)

    def show_wayland_shortcut_unassigned(self, onboarding):
        dialog = Adw.AlertDialog.new(
            "Shortcut is disabled",
            "You can enable Emote’s shortcut in your desktop’s keyboard settings.",
        )
        dialog.add_response("ok", "OK")
        dialog.set_close_response("ok")
        dialog.connect(
            "response", self.on_wayland_shortcut_unassigned_response, onboarding
        )
        dialog.present(self.get_visible_dialog() or self)

    def on_wayland_shortcut_unassigned_response(self, _dialog, response, onboarding):
        if onboarding:
            GLib.idle_add(self.get_application().continue_wayland_setup)

    def open_shortcuts(self):
        self.show_dialog(
            keyboard_shortcuts.KeyboardShortcuts(self, self.update_accelerator)
        )

    def show_dialog(self, dialog):
        if self.pending_inactive_close is not None:
            GLib.source_remove(self.pending_inactive_close)
            self.pending_inactive_close = None
        self.active_dialog = dialog
        dialog.connect("closed", self.on_dialog_closed)
        dialog.present(self)

    def on_dialog_closed(self, dialog):
        if self.active_dialog is dialog:
            self.active_dialog = None
            # Closing an Adw dialog can likewise omit the normal pointer-leave
            # transition seen by the underlying application window.
            self.pointer_in_picker = False
            if self.get_visible():
                # Dialog closure and compositor focus restoration are ordered
                # independently on Wayland. The picker was active enough to
                # present this dialog, so keep blur tracking armed even when
                # is_active has not caught up yet. The delayed close check will
                # see the restored focus before doing anything.
                self.was_active = True
            if not self.is_active():
                self.maybe_schedule_inactive_close()

    def open_about(self):
        dialog = Adw.AboutDialog(
            application_name="Emote",
            application_icon=config.app_id,
            version=os.environ.get(
                "FLATPAK_APP_VERSION", os.environ.get("SNAP_VERSION", "dev build")
            ),
            developers=["Tom Watson", "Vincent Emonet"],
            artists=["Tom Watson, Matthew Wong"],
            documenters=["Irene Auñón"],
            copyright=f"© Tom Watson {datetime.now().year}",
            website="https://github.com/tom-james-watson/emote",
            comments="Popup emoji picker for Linux",
            license_type=Gtk.License.GPL_3_0,
        )
        self.show_dialog(dialog)
