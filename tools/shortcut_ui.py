"""Run real GTK setup UI with isolated data and a simulated portal transport.

GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 pipenv run python tools/shortcut_ui.py
Never connects to desktop portals or changes desktop shortcuts. Harness controls
inject the same events as the backend, but cannot prove compositor key delivery.
"""

import argparse
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emote import EmoteApplication, config, user_data, css, emojis
from emote.wayland_shortcut import WaylandShortcut, SHORTCUT_ID
from gi.repository import Adw, Gio, GLib, Gtk

parser = argparse.ArgumentParser()
parser.add_argument(
    "--scenario", choices=("bound", "disabled", "cancel"), default="bound"
)
args = parser.parse_args()
test_data = tempfile.TemporaryDirectory(prefix="emote-shortcut-ui-")
user_data.SHELVE_PATH = str(Path(test_data.name) / "user_data")
config.is_wayland = True
config.is_flatpak = False
config.app_id = "com.tomjwatson.Emote.ShortcutUITest"


class TestPortal(WaylandShortcut):
    def enable(self):
        self._enabled = True
        self._session_handle = "/test/session"
        GLib.idle_add(self._on_shortcuts_listed, {"shortcuts": []})

    def bind(self, parent_window=""):
        if args.scenario == "cancel":
            GLib.idle_add(self._on_unavailable, RuntimeError("Simulated cancellation"))
        else:
            GLib.idle_add(
                self._on_shortcut_bound,
                {
                    "shortcuts": [
                        (
                            SHORTCUT_ID,
                            {
                                "trigger_description": (
                                    "Ctrl+Alt+E" if args.scenario == "bound" else ""
                                )
                            },
                        )
                    ]
                },
            )

    def activate_shortcut(self):
        self._on_portal_activated(
            None,
            None,
            None,
            None,
            None,
            GLib.Variant("(osta{sv})", (self._session_handle, SHORTCUT_ID, 1, {})),
        )

    def close(self):
        pass


class TestApplication(EmoteApplication):
    def start_daemon(self):
        css.load_css()
        emojis.init()
        self.started = True
        self.wayland_shortcut = TestPortal(
            self.on_hotkey,
            self.on_wayland_shortcut_bound,
            self.on_wayland_shortcut_missing,
            self.on_wayland_shortcut_unavailable,
        )
        self.wayland_shortcut.enable()
        controls = Adw.ApplicationWindow(
            application=self, title="Emote UI test controls"
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for margin in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{margin}")(18)
        box.append(Gtk.Label(label="Real GTK UI • simulated desktop events"))
        for label, callback in (
            ("Native shortcut signal", self.wayland_shortcut.activate_shortcut),
            ("Legacy launch / open Emote", self.activate),
            ("Keyboard Shortcuts", lambda: self.picker_window.open_shortcuts()),
            ("Quit test", self.quit),
        ):
            button = Gtk.Button(label=label)
            button.connect("clicked", lambda _button, action=callback: action())
            box.append(button)
        controls.set_content(box)
        controls.present()

    def set_wayland_auto_paste(self, enabled):
        # This harness exercises Skip only; never ask for real keyboard access.
        user_data.update_wayland_auto_paste_choice(False)
        self.picker_window.end_wayland_request(present=False)


Adw.init()
app = TestApplication()
try:
    app.run([])
finally:
    test_data.cleanup()
