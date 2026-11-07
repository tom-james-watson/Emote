from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from gi.repository import Gdk, GLib, Gtk

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

    @patch("emote.picker.GLib.source_remove")
    @patch("emote.picker.GLib.timeout_add", return_value=1)
    def test_scroll_reset_survives_the_next_allocation(
        self, _timeout_add, _source_remove
    ):
        adjustment = Gtk.Adjustment(
            value=0, lower=0, upper=9504, page_size=322, step_increment=1
        )
        picker = SimpleNamespace(
            scroller=SimpleNamespace(get_vadjustment=Mock(return_value=adjustment)),
            pending_search_scroll_restore=None,
            search_scroll_restore_handler=None,
            search_scroll_restore_target=None,
        )
        for name in (
            "finish_scroll_reset",
            "stop_scroll_reset",
            "cancel_search_scroll_restore",
        ):
            setattr(picker, name, getattr(EmojiPicker, name).__get__(picker))

        EmojiPicker.schedule_scroll_reset(picker)
        adjustment.configure(6024, 0, 6346, 1, 0, 322)
        self.assertEqual(adjustment.get_value(), 0)
        self.assertIsNone(picker.search_scroll_restore_handler)

        adjustment.configure(100, 0, 9504, 1, 0, 322)
        self.assertEqual(adjustment.get_value(), 100)

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
            selection_pending=False,
            root=Mock(),
            clipboard_restore=Mock(),
            display_emojis=[{"char": "🙂"}],
            appended=[],
            get_skintone_char=Mock(return_value="🙂"),
            copy_to_clipboard=Mock(),
            get_application=Mock(return_value=application),
            recent_dirty=False,
        )
        paste_sent = Mock()
        picker.clipboard_restore.copy.side_effect = lambda text, callback: callback(
            paste_sent, None
        )

        load_choice.return_value = False
        EmojiPicker.select_emoji(picker, 0)
        self.assertEqual(picker.clipboard_restore.copy.call_args.args[0], "🙂")
        timeout_add.assert_not_called()

        load_choice.return_value = True
        EmojiPicker.select_emoji(picker, 0)
        timeout_add.assert_called_once_with(150, application.paste_wayland, paste_sent)

    def test_shift_click_appends_and_plain_click_selects(self):
        for state, appended in (
            (Gdk.ModifierType.SHIFT_MASK, True),
            (Gdk.ModifierType(0), False),
        ):
            with self.subTest(state=state):
                picker = SimpleNamespace(append_emoji=Mock(), select_emoji=Mock())
                gesture = SimpleNamespace(
                    get_current_event_state=Mock(return_value=state)
                )
                box = SimpleNamespace()
                button = SimpleNamespace(
                    emoji_index=3, get_parent=Mock(return_value=box)
                )

                EmojiPicker.on_row_left_pressed(picker, gesture, 1, 0, 0, box)
                EmojiPicker.on_bound_button_clicked(picker, button)

                if appended:
                    picker.append_emoji.assert_called_once_with(3)
                    picker.select_emoji.assert_not_called()
                else:
                    picker.select_emoji.assert_called_once_with(3)
                    picker.append_emoji.assert_not_called()
