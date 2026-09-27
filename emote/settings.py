import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from emote import user_data


class Settings(Gtk.Window):
    def __init__(self, picker):
        super().__init__(title="Preferences", transient_for=picker, modal=True)
        self.picker = picker
        self.set_default_size(390, 200)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        self.set_child(box)

        theme_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        theme_row.append(Gtk.Label(label="Theme", xalign=0, hexpand=True))
        theme = Gtk.DropDown.new_from_strings(user_data.THEMES)
        saved_theme = user_data.load_theme()
        theme.set_selected(user_data.THEMES.index(saved_theme) if saved_theme in user_data.THEMES else 0)
        theme.connect("notify::selected", self.on_theme_changed)
        theme_row.append(theme)
        box.append(theme_row)

        tone_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        tone_row.append(Gtk.Label(label="Skin tone", xalign=0, hexpand=True))
        tone = Gtk.DropDown.new_from_strings(user_data.SKINTONES)
        tone.set_selected(user_data.load_skintone_index())
        tone.connect("notify::selected", self.on_tone_changed)
        tone_row.append(tone)
        box.append(tone_row)

        size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        size_row.append(Gtk.Label(label="Emoji size", xalign=0, hexpand=True))
        size = Gtk.DropDown.new_from_strings(user_data.EMOJI_SIZE_LABELS)
        size.set_selected(user_data.EMOJI_SIZES.index(picker.emoji_size))
        size.connect("notify::selected", self.on_size_changed)
        size_row.append(size)
        box.append(size_row)

    def on_size_changed(self, dropdown, _property):
        self.picker.set_emoji_size(user_data.EMOJI_SIZES[dropdown.get_selected()])

    def on_theme_changed(self, dropdown, _property):
        theme = user_data.THEMES[dropdown.get_selected()]
        user_data.update_theme(theme)
        gtk_settings = Gtk.Settings.get_default()
        if theme == user_data.DEFAULT_THEME:
            gtk_settings.reset_property("gtk-theme-name")
        else:
            gtk_settings.set_property("gtk-theme-name", theme)

    def on_tone_changed(self, dropdown, _property):
        self.picker.set_skin_tone(dropdown.get_selected())
