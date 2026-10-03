import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from emote import config, user_data


class Settings(Adw.PreferencesDialog):
    def __init__(self, picker):
        super().__init__(title="Preferences", search_enabled=False)
        self.picker = picker
        self._refreshing_auto_paste = False
        self.set_content_width(390)
        self.set_content_height(450 if config.is_wayland else 400)
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

    def refresh_wayland_auto_paste(self):
        enabled = user_data.load_wayland_auto_paste_choice() is True
        self._refreshing_auto_paste = True
        try:
            self.auto_paste.set_active(enabled)
        finally:
            self._refreshing_auto_paste = False
