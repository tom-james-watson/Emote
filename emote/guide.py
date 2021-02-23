import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from emote import user_data, config


GRID_SIZE = 10


class Guide(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(
            self,
            title="Emote Guide",
            window_position=Gtk.WindowPosition.CENTER,
            resizable=False,
        )

        header = Gtk.HeaderBar(title="Guide", show_close_button=True)
        self.set_titlebar(header)

        box = self.get_content_area()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        launching = Gtk.Label()
        launching.set_markup(
            '<span size="large" font_weight="bold" underline="single">Launching</span>'
        )
        launching.set_alignment(0, 0.5)
        vbox.pack_start(launching, True, True, GRID_SIZE)

        background = Gtk.Label()
        background.set_markup(
            "Emote runs in the background and automatically starts when you log in."
        )
        background.set_line_wrap(True)
        background.set_alignment(0, 0.5)
        vbox.pack_start(background, True, True, GRID_SIZE)

        if config.is_wayland:
            opening = Gtk.Label()
            opening.set_markup(
                "The emoji picker can be opened by clicking the app icon again, or by\n"
                'setting a custom app shortcut. See <a href="https://github.com/tom-james-watson/Emote/wiki/Hotkey-In-Wayland" title="See Wayland shortcut instructions">the wiki</a> for details.'
            )
            opening.set_line_wrap(True)
            opening.set_alignment(0, 0.5)
            vbox.pack_start(opening, True, True, GRID_SIZE)
        else:
            opening = Gtk.Label()
            opening.set_markup(
                "The emoji picker can be opened with either the keyboard shortcut or by\n"
                "clicking the app icon again."
            )
            opening.set_line_wrap(True)
            opening.set_alignment(0, 0.5)
            vbox.pack_start(opening, True, True, GRID_SIZE)

        usage = Gtk.Label()
        usage.set_markup(
            '<span size="large" font_weight="bold" underline="single">Usage</span>'
        )
        usage.set_alignment(0, 0.5)
        vbox.pack_start(usage, True, True, GRID_SIZE)

        if config.is_wayland:
            copying = Gtk.Label()
            copying.set_markup(
                "Select an emoji to have it copied to your clipboard. You can then paste the\n"
                "emoji wherever you need."
            )
            copying.set_line_wrap(True)
            copying.set_alignment(0, 0.5)
            vbox.pack_start(copying, True, True, GRID_SIZE)
        else:
            copying = Gtk.Label()
            copying.set_markup(
                "Select an emoji to have it pasted to your currently focussed app. The\n"
                "emoji is also copied to the clipboard so you can then paste the emoji\n"
                "wherever you need."
            )
            copying.set_line_wrap(True)
            copying.set_alignment(0, 0.5)
            vbox.pack_start(copying, True, True, GRID_SIZE)

        multiple = Gtk.Label()
        multiple.set_markup(
            "You can select multiple emojis by selecting them with shift left click\n"
            "or with right click."
        )
        multiple.set_line_wrap(True)
        multiple.set_alignment(0, 0.5)
        vbox.pack_start(multiple, True, True, GRID_SIZE)

        hbox.pack_start(vbox, True, True, GRID_SIZE)
        box.pack_start(hbox, True, True, GRID_SIZE)

        self.show_all()
        self.present()
