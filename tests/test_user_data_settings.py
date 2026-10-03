import json
import shelve
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from emote import user_data
from tests import isolate_user_data


class SettingsFileTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(isolate_user_data(directory.name).close)
        self.shelve_path = user_data.SHELVE_PATH
        self.settings_path = Path(user_data.SETTINGS_PATH)

    def write_settings(self, text):
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(text, encoding="utf-8")

    def read_settings(self):
        return json.loads(self.settings_path.read_text(encoding="utf-8"))

    def test_first_read_writes_defaults(self):
        self.assertEqual(user_data.load_accelerator(), "<Primary><Alt>e")
        self.assertEqual(self.read_settings(), user_data.DEFAULT_SETTINGS)

    def test_round_trip(self):
        user_data.update_accelerator("<Super>period")
        user_data.update_skintone_index(3)
        user_data.update_emoji_size(36)
        user_data.update_picker_size(640, 480)
        user_data.update_x11_auto_paste_enabled(False)
        user_data.update_wayland_auto_paste_choice(True)
        user_data.update_shown_welcome()

        self.assertEqual(user_data.load_accelerator(), "<Super>period")
        self.assertEqual(user_data.load_skintone_index(), 3)
        self.assertEqual(user_data.load_emoji_size(), 36)
        self.assertEqual(user_data.load_picker_size(), (640, 480))
        self.assertFalse(user_data.load_x11_auto_paste_enabled())
        self.assertTrue(user_data.load_wayland_auto_paste_choice())
        self.assertTrue(user_data.load_shown_welcome())
        self.assertTrue(self.settings_path.read_text().endswith("\n"))

    def test_hand_edits_are_read_without_restart(self):
        user_data.update_emoji_size(20)
        self.write_settings(json.dumps({"emoji_size": 32}))

        self.assertEqual(user_data.load_emoji_size(), 32)

    def test_unknown_keys_survive_updates(self):
        self.write_settings(json.dumps({"future": "value"}))

        user_data.update_skintone_index(2)

        self.assertEqual(self.read_settings(), {"future": "value", "skintone_index": 2})

    def test_wrong_types_fall_back_to_defaults(self):
        self.write_settings(
            json.dumps(
                {
                    "accelerator": 1,
                    "skintone_index": True,
                    "emoji_size": "36",
                    "picker_size": "640x480",
                    "x11_auto_paste": "no",
                    "wayland_auto_paste": 1,
                    "shown_welcome": None,
                }
            )
        )

        self.assertEqual(user_data.load_accelerator(), "<Primary><Alt>e")
        self.assertEqual(user_data.load_skintone_index(), 0)
        self.assertEqual(user_data.load_emoji_size(), 28)
        self.assertEqual(user_data.load_picker_size(), (515, 500))
        self.assertTrue(user_data.load_x11_auto_paste_enabled())
        self.assertIsNone(user_data.load_wayland_auto_paste_choice())
        self.assertFalse(user_data.load_shown_welcome())

    def test_out_of_range_values_are_normalized(self):
        self.write_settings(
            json.dumps({"skintone_index": 9, "emoji_size": 30, "picker_size": [1, 1]})
        )

        self.assertEqual(user_data.load_skintone_index(), 0)
        self.assertEqual(user_data.load_emoji_size(), 28)
        self.assertEqual(user_data.load_picker_size(), (460, 300))

    def test_unreadable_file_is_kept_as_backup_on_save(self):
        self.write_settings("{not json\n")

        self.assertEqual(user_data.load_skintone_index(), 0)
        self.assertEqual(self.settings_path.read_text(), "{not json\n")

        user_data.update_skintone_index(4)

        backup = Path(f"{self.settings_path}.bak")
        self.assertEqual(backup.read_text(), "{not json\n")
        self.assertEqual(self.read_settings()["skintone_index"], 4)

    def test_migrates_shelve_settings_and_keeps_recent_emojis(self):
        with shelve.open(self.shelve_path) as db:
            db["accelerator_string"] = "<Primary><Alt>x"
            db["accelerator_label"] = "Ctrl+Alt+X"
            db["skintone_index"] = 4
            db["emoji_size"] = 32
            db["picker_size"] = (700, 600)
            db["x11_auto_paste"] = False
            db["shown_welcome"] = True
            db["recent_emojis"] = ["🧪"]

        self.assertEqual(user_data.load_accelerator(), "<Primary><Alt>x")
        self.assertEqual(
            self.read_settings(),
            {
                **user_data.DEFAULT_SETTINGS,
                "accelerator": "<Primary><Alt>x",
                "skintone_index": 4,
                "emoji_size": 32,
                "picker_size": [700, 600],
                "x11_auto_paste": False,
                "shown_welcome": True,
            },
        )
        self.assertEqual(user_data.load_recent_emojis(), ["🧪"])

    def test_partial_shortcuts_merge_with_defaults(self):
        self.write_settings(
            json.dumps({"shortcuts": {"close": "q", "focus_search": 1, "other": "x"}})
        )

        self.assertEqual(
            user_data.load_shortcuts(),
            {**user_data.DEFAULT_SHORTCUTS, "close": "q"},
        )
