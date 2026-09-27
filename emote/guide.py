import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from emote import config


class Guide(Gtk.Window):
    def __init__(self, picker):
        super().__init__(title="Emote Guide", transient_for=picker, modal=True)
        self.set_default_size(430, 280)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        self.set_child(box)

        self.add_section(box, "Find an emoji", "Search, or scroll through all categories. Select a category above the list to jump to it.")
        self.add_section(box, "Select", "Click an emoji or press Enter to copy it. Right-click or press Shift+Enter to collect multiple emojis.")
        if config.is_wayland:
            self.add_section(box, "Shortcut on Wayland", "Create a custom desktop shortcut that runs Emote. The selected emoji is copied to your clipboard.")
        else:
            self.add_section(box, "Shortcut", "Press Ctrl+Alt+E to open Emote. On X11, the selected emoji is also pasted into the previous application.")

    def add_section(self, box, title, description):
        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class("heading")
        box.append(heading)
        body = Gtk.Label(label=description, xalign=0, wrap=True)
        box.append(body)
