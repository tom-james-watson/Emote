import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from emote import user_data
from emote.keybinding import ButtonKeybinding


GRID_SIZE = 10


class Settings(Gtk.Dialog):
    def __init__(self, update_accelerator):
        Gtk.Dialog.__init__(
            self,
            title="Emote Settings",
            window_position=Gtk.WindowPosition.CENTER,
            resizable=False,
        )

        self.update_accelerator = update_accelerator

        header = Gtk.HeaderBar(title="Settings", show_close_button=True)
        self.set_titlebar(header)

        box = self.get_content_area()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=GRID_SIZE)

        shortcut_label = Gtk.Label()
        shortcut_label.set_text("Keyboard Shortcut")
        shortcut_label.set_justify(Gtk.Justification.LEFT)
        hbox.pack_start(shortcut_label, False, False, GRID_SIZE)

        shortcut_keybinding = ButtonKeybinding()
        shortcut_keybinding.set_size_request(150, -1)
        shortcut_keybinding.connect("accel-edited", self.on_kb_changed)
        shortcut_keybinding.connect("accel-cleared", self.on_kb_changed)
        accel_string, _ = user_data.load_accelerator()
        shortcut_keybinding.set_accel_string(accel_string)

        hbox.pack_start(shortcut_keybinding, False, False, GRID_SIZE)
        box.pack_start(hbox, False, False, GRID_SIZE)

        self.show_all()
        self.present()

    def on_kb_changed(self, button_keybinding, accel_string=None, accel_label=None):
        self.update_accelerator(accel_string, accel_label)
