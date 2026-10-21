import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from emote import config, user_data
from emote.clipboard import restoration_available


class Settings(Adw.PreferencesDialog):
    def __init__(self, picker):
        super().__init__(title="Preferences", search_enabled=False)
        self.picker = picker
        self._refreshing_auto_paste = False
        self._restore_request = None
        self._refreshing_restore = False
        self.set_content_width(390)
        self.set_content_height(500)
        self.set_font_map(picker.root.get_font_map())
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        page.add(group)
        self.add(page)

        tone = Adw.ComboRow(
            title="Skin tone", model=Gtk.StringList.new(user_data.SKINTONES)
        )
        tone.set_selected(user_data.load_skintone_index())
        tone.connect("notify::selected", self.on_tone_changed)
        group.add(tone)

        size = Adw.ComboRow(
            title="Emoji size", model=Gtk.StringList.new(user_data.EMOJI_SIZE_LABELS)
        )
        size.set_selected(user_data.EMOJI_SIZES.index(picker.emoji_size))
        size.connect("notify::selected", self.on_size_changed)
        group.add(size)

        font = Adw.ComboRow(
            title="Emoji font", model=Gtk.StringList.new(user_data.EMOJI_FONT_LABELS)
        )
        font.set_selected(user_data.EMOJI_FONTS.index(user_data.load_emoji_font()))
        font.connect("notify::selected", self.on_font_changed)
        group.add(font)

        paste_group = Adw.PreferencesGroup()
        page.add(paste_group)
        self.auto_paste = Adw.SwitchRow(
            title="Automatic paste",
            subtitle="Paste emojis into the app you were using",
        )
        enabled = (
            user_data.load_wayland_auto_paste_choice() is True
            if config.is_wayland
            else user_data.load_x11_auto_paste_enabled()
        )
        self.auto_paste.set_active(enabled)
        self.auto_paste.connect("notify::active", self.on_auto_paste_changed)
        paste_group.add(self.auto_paste)
        self.restore_clipboard = Adw.SwitchRow(
            title="Restore clipboard",
            subtitle="Keep what you copied before inserting an emoji",
            active=user_data.load_restore_clipboard_enabled(),
            visible=enabled and restoration_available(),
        )
        self.restore_clipboard.connect(
            "notify::active", self.on_restore_clipboard_changed
        )
        paste_group.add(self.restore_clipboard)

    def on_size_changed(self, row, _property):
        self.picker.set_emoji_size(user_data.EMOJI_SIZES[row.get_selected()])

    def on_tone_changed(self, row, _property):
        self.picker.set_skin_tone(row.get_selected())

    def on_font_changed(self, row, _property):
        self.picker.set_emoji_font(user_data.EMOJI_FONTS[row.get_selected()])
        self.set_font_map(self.picker.root.get_font_map())

    def on_auto_paste_changed(self, row, _property):
        if not self._refreshing_auto_paste:
            if config.is_wayland:
                self.picker.get_application().set_wayland_auto_paste(row.get_active())
            else:
                user_data.update_x11_auto_paste_enabled(row.get_active())
            self.restore_clipboard.set_visible(
                row.get_active() and restoration_available()
            )
            if not row.get_active():
                self._restore_request = None
                self.refresh_clipboard_restoration()

    def on_restore_clipboard_changed(self, row, _property):
        if (
            not restoration_available()
            or not self.auto_paste.get_active()
            or self._restore_request is not None
            or self._refreshing_restore
        ):
            return
        enabled = row.get_active()
        if (
            not enabled
            or not config.is_wayland
            or not self.picker.clipboard_restore.needs_portal
        ):
            user_data.update_restore_clipboard_enabled(enabled)
            return
        request = object()
        self._restore_request = request
        row.set_sensitive(False)

        def finished(error):
            if self._restore_request is not request:
                return
            enabled = error is None and self.auto_paste.get_active()
            user_data.update_restore_clipboard_enabled(enabled)
            row.set_active(enabled)
            row.set_sensitive(True)
            self._restore_request = None
            if error is not None and self.auto_paste.get_active():
                dialog = Adw.AlertDialog.new(
                    "Clipboard restoration is off",
                    "Clipboard access wasn’t granted. You can try enabling this setting "
                    "again. Automatic paste remains enabled.",
                )
                dialog.add_response("close", "Close")
                self.picker.show_dialog(dialog)

        self.picker.get_application().ensure_clipboard_access(finished)

    def refresh_clipboard_restoration(self):
        self._refreshing_restore = True
        try:
            self.restore_clipboard.set_active(
                user_data.load_restore_clipboard_enabled()
            )
            self.restore_clipboard.set_sensitive(True)
        finally:
            self._refreshing_restore = False

    def refresh_wayland_auto_paste(self):
        enabled = user_data.load_wayland_auto_paste_choice() is True
        self._refreshing_auto_paste = True
        try:
            self.auto_paste.set_active(enabled)
            self.restore_clipboard.set_visible(enabled and restoration_available())
        finally:
            self._refreshing_auto_paste = False
