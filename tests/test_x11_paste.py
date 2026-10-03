from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from emote import user_data
from emote.picker import EmojiPicker
from emote.settings import Settings
from tests import isolate_user_data


class X11PasteTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(isolate_user_data(directory.name).close)

    @patch("emote.settings.config.is_wayland", False)
    def test_preference_defaults_on_and_can_be_toggled(self):
        self.assertTrue(user_data.load_x11_auto_paste_enabled())
        settings = SimpleNamespace(_refreshing_auto_paste=False)
        row = SimpleNamespace(get_active=Mock(return_value=False))

        Settings.on_auto_paste_changed(settings, row, None)
        self.assertFalse(user_data.load_x11_auto_paste_enabled())

        row.get_active.return_value = True
        Settings.on_auto_paste_changed(settings, row, None)
        self.assertTrue(user_data.load_x11_auto_paste_enabled())

    @patch("emote.picker.config.is_wayland", False)
    @patch("emote.picker.GLib.timeout_add")
    def test_selection_always_copies_and_only_pastes_when_enabled(self, timeout_add):
        application = SimpleNamespace(close_picker_window=Mock())
        picker = SimpleNamespace(
            waiting_for_wayland_setup=False,
            display_emojis=[{"name": "smile"}],
            appended=[],
            get_skintone_char=Mock(return_value="🙂"),
            copy_to_clipboard=Mock(),
            get_application=Mock(return_value=application),
            paste_x11=Mock(),
            recent_dirty=False,
        )

        with patch("emote.picker.user_data.update_recent_emojis"):
            user_data.update_x11_auto_paste_enabled(False)
            EmojiPicker.select_emoji(picker, 0)
            picker.copy_to_clipboard.assert_called_once_with("🙂")
            application.close_picker_window.assert_called_once_with()
            timeout_add.assert_not_called()

            user_data.update_x11_auto_paste_enabled(True)
            EmojiPicker.select_emoji(picker, 0)
            timeout_add.assert_called_once_with(150, picker.paste_x11)
