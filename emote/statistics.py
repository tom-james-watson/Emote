import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango

from emote import emojis, user_data

MOST_USED_LIMIT = 10
MOST_USED_EMOJI_SIZE = 20


class Statistics(Adw.PreferencesDialog):
    def __init__(self, picker):
        super().__init__(title="Statistics", search_enabled=False)
        self.set_content_width(440)
        self.set_content_height(580)
        self.set_font_map(picker.root.get_font_map())
        if picker.bundled_emoji_font:
            self.add_css_class("bundled-emojis")
        page = Adw.PreferencesPage()
        self.add(page)

        counts = user_data.load_emoji_usage_counts()
        summary = Adw.PreferencesGroup()
        summary.add(self.summary_row(sum(counts.values()), "Emojis used"))
        summary.add(self.summary_row(len(counts), "Unique emojis"))
        page.add(summary)

        group = Adw.PreferencesGroup(title=f"Top {MOST_USED_LIMIT}")
        page.add(group)
        if not counts:
            group.set_description("No emojis used yet")
            return

        attributes = (
            picker.emoji_attributes.copy()
            if picker.emoji_attributes is not None
            else Pango.AttrList()
        )
        attributes.insert(
            Pango.attr_size_new_absolute(MOST_USED_EMOJI_SIZE * Pango.SCALE)
        )

        most_used = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        for char, count in most_used[:MOST_USED_LIMIT]:
            try:
                emoji = emojis.get_emoji_by_char(char)
            except Exception:
                emoji = {"char": char, "name": "Unavailable emoji", "skintone": None}
            row = Adw.ActionRow(title=emoji["name"], title_lines=1, use_markup=False)
            row.set_tooltip_text(emoji["name"])
            glyph = Gtk.Label(label=picker.get_skintone_char(emoji), width_request=28)
            glyph.add_css_class("emoji-glyph")
            glyph.set_attributes(attributes)
            row.add_prefix(glyph)
            total = Gtk.Label(label=f"{count:,}")
            total.add_css_class("dim-label")
            row.add_suffix(total)
            group.add(row)

    @staticmethod
    def summary_row(count, title):
        row = Adw.ActionRow(title=title)
        value = Gtk.Label(label=f"{count:,}")
        value.add_css_class("dim-label")
        row.add_suffix(value)
        return row
