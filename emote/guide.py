import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from emote import config


class Guide(Adw.Dialog):
    def __init__(self, picker):
        super().__init__(title="Emote Guide")
        self.set_content_width(430)
        self.set_content_height(280)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(box)
        toolbar.set_content(scroller)
        self.set_child(toolbar)

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
