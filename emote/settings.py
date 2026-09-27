import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from emote import user_data


class Settings(Adw.PreferencesDialog):
    def __init__(self, picker):
        super().__init__(title="Preferences", search_enabled=False)
        self.picker = picker
        self.set_content_width(390)
        self.set_content_height(260)
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        page.add(group)
        self.add(page)

        tone = Adw.ComboRow(title="Skin tone", model=Gtk.StringList.new(user_data.SKINTONES))
        tone.set_selected(user_data.load_skintone_index())
        tone.connect("notify::selected", self.on_tone_changed)
        group.add(tone)

        size = Adw.ComboRow(title="Emoji size", model=Gtk.StringList.new(user_data.EMOJI_SIZE_LABELS))
        size.set_selected(user_data.EMOJI_SIZES.index(picker.emoji_size))
        size.connect("notify::selected", self.on_size_changed)
        group.add(size)

    def on_size_changed(self, row, _property):
        self.picker.set_emoji_size(user_data.EMOJI_SIZES[row.get_selected()])

    def on_tone_changed(self, row, _property):
        self.picker.set_skin_tone(row.get_selected())
