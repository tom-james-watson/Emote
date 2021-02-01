import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from emote import user_data


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
            "or with right click"
        )
        multiple.set_line_wrap(True)
        multiple.set_alignment(0, 0.5)
        vbox.pack_start(multiple, True, True, GRID_SIZE)

        shortcuts = Gtk.Label()
        shortcuts.set_markup(
            '<span size="large" font_weight="bold" underline="single">Keyboard Shortcuts</span>'
        )
        shortcuts.set_alignment(0, 0.5)
        vbox.pack_start(shortcuts, True, True, GRID_SIZE)

        _, accel_label = user_data.load_accelerator()
        launch_shortcut = Gtk.Label()
        launch_shortcut.set_markup(
            f'<span font_weight="bold">Open Emoji Picker:</span> {accel_label}'
        )
        launch_shortcut.set_alignment(0, 0.5)
        vbox.pack_start(launch_shortcut, True, True, GRID_SIZE)

        _, accel_label = user_data.load_accelerator()
        select_shortcut = Gtk.Label()
        select_shortcut.set_markup(
            f'<span font_weight="bold">Select Emoji:</span> Enter'
        )
        select_shortcut.set_alignment(0, 0.5)
        vbox.pack_start(select_shortcut, True, True, GRID_SIZE)

        _, accel_label = user_data.load_accelerator()
        select_multi_shortcut = Gtk.Label()
        select_multi_shortcut.set_markup(
            f'<span font_weight="bold">Add Emoji to Selection:</span> Shift+Enter'
        )
        select_multi_shortcut.set_alignment(0, 0.5)
        vbox.pack_start(select_multi_shortcut, True, True, GRID_SIZE)

        search_shortcut = Gtk.Label()
        search_shortcut.set_markup(
            f'<span font_weight="bold">Focus Search:</span> Ctrl+F'
        )
        search_shortcut.set_alignment(0, 0.5)
        vbox.pack_start(search_shortcut, True, True, GRID_SIZE)

        next_cat_shortcut = Gtk.Label()
        next_cat_shortcut.set_markup(
            f'<span font_weight="bold">Next Emoji Category:</span> Ctrl+Tab'
        )
        next_cat_shortcut.set_alignment(0, 0.5)
        vbox.pack_start(next_cat_shortcut, True, True, GRID_SIZE)

        prev_cat_shortcut = Gtk.Label()
        prev_cat_shortcut.set_markup(
            f'<span font_weight="bold">Previous Emoji Category:</span> Ctrl+Shift+Tab'
        )
        prev_cat_shortcut.set_alignment(0, 0.5)
        vbox.pack_start(prev_cat_shortcut, True, True, GRID_SIZE)

        hbox.pack_start(vbox, True, True, GRID_SIZE)
        box.pack_start(hbox, True, True, GRID_SIZE)

        self.show_all()
        self.present()
