import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from emote import config, user_data


class KeyboardShortcuts(Adw.Dialog):
    def __init__(self, picker, update_accelerator):
        super().__init__(title="Keyboard Shortcuts")
        self.update_accelerator = update_accelerator
        self.recording = False
        self.set_content_width(400)
        self.set_content_height(260)
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

        if not config.is_wayland:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.append(Gtk.Label(label="Open Emoji Picker", xalign=0, hexpand=True))
            self.record_button = Gtk.Button(label=user_data.load_accelerator()[1])
            self.record_button.connect("clicked", self.start_recording)
            row.append(self.record_button)
            box.append(row)

        for label, binding in (
            ("Select Emoji", "Enter"),
            ("Add to Selection", "Shift+Enter"),
            ("Focus Search", "Ctrl+F"),
            ("Next Category", "Ctrl+Tab"),
            ("Previous Category", "Ctrl+Shift+Tab"),
        ):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.append(Gtk.Label(label=label, xalign=0, hexpand=True))
            shortcut = Gtk.Label(label=binding)
            shortcut.add_css_class("dim-label")
            row.append(shortcut)
            box.append(row)

        keys = Gtk.EventControllerKey.new()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.on_key_pressed)
        self.add_controller(keys)

    def start_recording(self, _button):
        self.recording = True
        self.record_button.set_label("Press a shortcut…")

    def on_key_pressed(self, _controller, keyval, _keycode, state):
        if not self.recording:
            return False
        if keyval == Gdk.KEY_Escape:
            self.record_button.set_label(user_data.load_accelerator()[1])
            self.recording = False
            return True
        if keyval == Gdk.KEY_BackSpace:
            self.update_accelerator("", "Unassigned")
            self.record_button.set_label("Unassigned")
            self.recording = False
            return True

        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        if not modifiers:
            self.record_button.set_label("Include Ctrl, Alt, or Super")
            return True
        accelerator = Gtk.accelerator_name(keyval, modifiers)
        label = Gtk.accelerator_get_label(keyval, modifiers)
        self.update_accelerator(accelerator, label)
        self.record_button.set_label(label)
        self.recording = False
        return True
