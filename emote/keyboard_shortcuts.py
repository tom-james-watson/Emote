import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from emote import config, user_data

MODIFIER_KEYS = {
    Gdk.KEY_Shift_L,
    Gdk.KEY_Shift_R,
    Gdk.KEY_Shift_Lock,
    Gdk.KEY_Control_L,
    Gdk.KEY_Control_R,
    Gdk.KEY_Alt_L,
    Gdk.KEY_Alt_R,
    Gdk.KEY_Meta_L,
    Gdk.KEY_Meta_R,
    Gdk.KEY_Super_L,
    Gdk.KEY_Super_R,
    Gdk.KEY_Hyper_L,
    Gdk.KEY_Hyper_R,
    Gdk.KEY_ISO_Level3_Shift,
    Gdk.KEY_ISO_Level3_Latch,
    Gdk.KEY_ISO_Level3_Lock,
}


def format_accelerator_label(label):
    label = label.removeprefix("Press ")
    valid, keyval, modifiers = Gtk.accelerator_parse(label)
    if valid:
        return Gtk.accelerator_get_label(keyval, modifiers)
    return label


def current_accelerator_label():
    return format_accelerator_label(user_data.load_accelerator()) or "Unassigned"


class KeyboardShortcuts(Adw.Dialog):
    def __init__(self, picker, update_accelerator):
        super().__init__(title="Keyboard Shortcuts")
        self.picker = picker
        self.update_accelerator = update_accelerator
        self.recording = False
        self.set_content_width(400)
        self.set_content_height(420)
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

        if config.is_wayland:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.append(Gtk.Label(label="Open Emote", xalign=0, hexpand=True))
            self.global_shortcut_button = Gtk.Button(valign=Gtk.Align.CENTER)
            self.global_shortcut_button.connect(
                "clicked", self.setup_wayland_global_shortcut
            )
            self.global_shortcut_value = Gtk.Label(valign=Gtk.Align.CENTER)
            self.global_shortcut_value.add_css_class("dim-label")
            row.append(self.global_shortcut_button)
            row.append(self.global_shortcut_value)
            box.append(row)
            self.refresh_wayland_global_shortcut()
        else:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.append(Gtk.Label(label="Open Emote", xalign=0, hexpand=True))
            self.record_button = Gtk.Button(label=current_accelerator_label())
            self.record_button.connect("clicked", self.start_recording)
            row.append(self.record_button)
            box.append(row)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        shortcuts = user_data.load_shortcuts()
        for label, binding in (
            ("Select Emoji", "Enter"),
            ("Add to Selection", "Shift+Enter"),
            ("Focus Search", format_accelerator_label(shortcuts["focus_search"])),
            ("Next Category", format_accelerator_label(shortcuts["next_category"])),
            (
                "Previous Category",
                format_accelerator_label(shortcuts["previous_category"]),
            ),
            ("Close Picker", format_accelerator_label(shortcuts["close"])),
        ):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.append(Gtk.Label(label=label, xalign=0, hexpand=True))
            shortcut = Gtk.Label(label=binding)
            shortcut.add_css_class("dim-label")
            row.append(shortcut)
            box.append(row)

        settings_hint = Gtk.Label(
            label=f"Change picker shortcuts in {user_data.SETTINGS_PATH}",
            xalign=0,
            wrap=True,
            selectable=True,
        )
        settings_hint.add_css_class("dim-label")
        settings_hint.add_css_class("caption")
        box.append(settings_hint)

        keys = Gtk.EventControllerKey.new()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.on_key_pressed)
        self.add_controller(keys)

    def setup_wayland_global_shortcut(self, _button):
        application = self.picker.get_application()
        if user_data.load_wayland_global_shortcut_choice() is True:
            return
        started = application.set_wayland_global_shortcut()
        if started:
            self.global_shortcut_button.set_label("Opening…")
            self.global_shortcut_button.set_sensitive(False)
        else:
            self.refresh_wayland_global_shortcut()

    def refresh_wayland_global_shortcut(self):
        is_set = user_data.load_wayland_global_shortcut_choice() is True
        if is_set:
            shortcut_label = format_accelerator_label(
                user_data.load_wayland_global_shortcut_label()
            )
            self.global_shortcut_value.set_label(shortcut_label)
            self.global_shortcut_value.set_visible(True)
            self.global_shortcut_button.set_visible(False)
        else:
            registered = self.picker.get_application().is_wayland_shortcut_registered()
            self.global_shortcut_button.set_label(
                "Details…" if registered else "Set up…"
            )
            self.global_shortcut_button.set_tooltip_text(
                "About the disabled shortcut" if registered else "Set up shortcut"
            )
            self.global_shortcut_button.set_sensitive(True)
            self.global_shortcut_button.set_visible(True)
            self.global_shortcut_value.set_label("Disabled" if registered else "")
            self.global_shortcut_value.set_visible(registered)

    def start_recording(self, _button):
        self.recording = True
        self.record_button.set_label("Press a shortcut…")

    def on_key_pressed(self, _controller, keyval, _keycode, state):
        if not self.recording:
            return False
        if keyval == Gdk.KEY_Escape:
            self.record_button.set_label(current_accelerator_label())
            self.recording = False
            return True
        if keyval == Gdk.KEY_BackSpace:
            self.update_accelerator("")
            self.record_button.set_label("Unassigned")
            self.recording = False
            return True

        if keyval in MODIFIER_KEYS:
            return True
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        if not modifiers & (
            Gdk.ModifierType.CONTROL_MASK
            | Gdk.ModifierType.ALT_MASK
            | Gdk.ModifierType.SUPER_MASK
        ):
            self.record_button.set_label("Include Ctrl, Alt, or Super")
            return True
        accelerator = Gtk.accelerator_name(keyval, modifiers)
        label = Gtk.accelerator_get_label(keyval, modifiers)
        self.update_accelerator(accelerator)
        self.record_button.set_label(label)
        self.recording = False
        return True
