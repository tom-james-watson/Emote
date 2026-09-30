from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from gi.repository import GLib

from emote.picker import EmojiPicker


class PickerSelectionTests(TestCase):
    def test_focus_callback_runs_once_even_when_grab_succeeds(self):
        picker = SimpleNamespace(
            search_entry=SimpleNamespace(grab_focus=Mock(return_value=True))
        )

        self.assertEqual(EmojiPicker.focus_search_entry(picker), GLib.SOURCE_REMOVE)
        picker.search_entry.grab_focus.assert_called_once_with()

    @patch("emote.picker.GLib.timeout_add")
    def test_jumping_to_category_selects_its_first_emoji(self, _timeout_add):
        rows = [
            SimpleNamespace(title="Recent"),
            SimpleNamespace(title=None, entries=["🙂"], start_index=0),
            SimpleNamespace(title="Animals"),
            SimpleNamespace(title=None, entries=["🐯"], start_index=1),
        ]
        picker = SimpleNamespace(
            searching=False,
            search_entry=SimpleNamespace(get_text=Mock(return_value="")),
            category_rows={"recent": 0, "animals-nature": 2},
            rows=SimpleNamespace(
                get_n_items=Mock(return_value=len(rows)),
                get_item=Mock(side_effect=rows.__getitem__),
            ),
            selected_index=0,
            scroller=SimpleNamespace(get_vadjustment=Mock()),
            list_view=Mock(),
            cancel_search_scroll_restore=Mock(),
            set_active_category=Mock(),
            update_visible_selection=Mock(),
            update_preview=Mock(),
            category_scroll_position=Mock(return_value=None),
            finish_category_jump=Mock(),
        )

        EmojiPicker.on_category_clicked(picker, None, "animals-nature")

        self.assertEqual(picker.selected_index, 1)
        picker.update_preview.assert_called_once_with()
        picker.list_view.scroll_to.assert_called_once()

    @patch("emote.picker.config.is_wayland", True)
    @patch("emote.picker.GLib.timeout_add")
    @patch("emote.picker.user_data.update_recent_emojis")
    @patch("emote.picker.user_data.load_wayland_auto_paste_choice")
    def test_wayland_selection_only_schedules_paste_when_enabled(
        self, load_choice, _update_recent, timeout_add
    ):
        application = SimpleNamespace(close_picker_window=Mock(), paste_wayland=Mock())
        picker = SimpleNamespace(
            waiting_for_wayland_setup=False,
            display_emojis=[{"char": "🙂"}],
            appended=[],
            get_skintone_char=Mock(return_value="🙂"),
            copy_to_clipboard=Mock(),
            get_application=Mock(return_value=application),
            recent_dirty=False,
        )

        load_choice.return_value = False
        EmojiPicker.select_emoji(picker, 0)
        picker.copy_to_clipboard.assert_called_with("🙂")
        timeout_add.assert_not_called()

        load_choice.return_value = True
        EmojiPicker.select_emoji(picker, 0)
        timeout_add.assert_called_once_with(150, application.paste_wayland)
