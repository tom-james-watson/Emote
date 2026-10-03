from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from emote.picker import EmojiPicker, normalize_key, parse_shortcuts
from gi.repository import Gdk

CONTROL = Gdk.ModifierType.CONTROL_MASK
SHIFT = Gdk.ModifierType.SHIFT_MASK


class PickerShortcutTests(TestCase):
    def make_picker(self, shortcuts):
        application = SimpleNamespace(close_picker_window=Mock())
        return SimpleNamespace(
            shortcuts=parse_shortcuts(shortcuts),
            search_entry=Mock(),
            cycle_category=Mock(),
            get_application=Mock(return_value=application),
            get_visible_dialog=Mock(return_value=None),
            waiting_for_wayland_setup=False,
            display_emojis=[],
            get_focus=Mock(return_value=None),
        )

    def press(self, picker, keyval, state=0):
        return EmojiPicker.on_key_pressed(picker, None, keyval, 0, state)

    def test_shift_tab_matches_previous_category(self):
        picker = self.make_picker({"previous_category": "<Primary><Shift>Tab"})

        self.assertTrue(self.press(picker, Gdk.KEY_ISO_Left_Tab, CONTROL | SHIFT))
        picker.cycle_category.assert_called_once_with(-1)

    def test_configured_shortcuts_replace_defaults(self):
        picker = self.make_picker({"next_category": "Page_Down", "close": "<Primary>q"})

        self.assertTrue(self.press(picker, Gdk.KEY_Page_Down))
        picker.cycle_category.assert_called_once_with(1)
        self.assertFalse(self.press(picker, Gdk.KEY_Escape))
        caps_lock = Gdk.ModifierType.LOCK_MASK
        self.assertTrue(self.press(picker, Gdk.KEY_Q, CONTROL | caps_lock))
        picker.get_application().close_picker_window.assert_called_once_with()

    def test_extra_modifiers_do_not_match(self):
        picker = self.make_picker({"focus_search": "<Primary>f"})

        self.assertFalse(self.press(picker, Gdk.KEY_F, CONTROL | SHIFT))
        picker.search_entry.grab_focus.assert_not_called()

    def test_unparseable_shortcut_uses_default(self):
        self.assertEqual(
            parse_shortcuts({"close": "not a key"}),
            {"close": normalize_key(Gdk.KEY_Escape, 0)},
        )
