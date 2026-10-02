from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from emote.picker import EmojiPicker
from gi.repository import Gdk, GLib, GObject, Gtk


class PickerFocusTests(TestCase):
    @patch("emote.picker.Adw.AlertDialog.new")
    def test_paste_failure_dialog_blocks_blur_during_opening_transition(
        self, new_dialog
    ):
        picker = self.make_picker()
        picker.pointer_in_picker = False
        picker.show_dialog = EmojiPicker.show_dialog.__get__(picker)
        picker.on_dialog_closed = EmojiPicker.on_dialog_closed.__get__(picker)
        picker.get_visible = Mock(return_value=True)
        picker.maybe_schedule_inactive_close = (
            EmojiPicker.maybe_schedule_inactive_close.__get__(picker)
        )
        dialog = new_dialog.return_value

        EmojiPicker.show_wayland_paste_unavailable(picker)

        # Adwaita has not exposed the modal through get_visible_dialog yet.
        self.assertIsNone(picker.get_visible_dialog())
        self.assertIs(picker.active_dialog, dialog)
        EmojiPicker.on_active_changed(picker, None, None)
        EmojiPicker.close_if_inactive(picker)
        picker.schedule_inactive_close.assert_not_called()
        picker.get_application.return_value.close_picker_window.assert_not_called()
        dialog.present.assert_called_once_with(picker)

        # Dismissal releases the modal guard and ordinary blur still works.
        picker.is_active.return_value = True
        picker.on_dialog_closed(dialog)
        self.assertIsNone(picker.active_dialog)
        picker.is_active.return_value = False
        EmojiPicker.close_if_inactive(picker)
        picker.get_application.return_value.close_picker_window.assert_called_once_with()

    @patch("emote.picker.Adw.AlertDialog.new")
    def test_paste_failure_preserves_tracked_parent_dialog(self, new_dialog):
        picker = self.make_picker()
        parent = Mock()
        picker.active_dialog = parent
        picker.show_dialog = Mock()

        EmojiPicker.show_wayland_paste_unavailable(picker)

        self.assertIs(picker.active_dialog, parent)
        new_dialog.return_value.present.assert_called_once_with(parent)
        picker.show_dialog.assert_not_called()

    def test_blur_then_gtk_leave_closes_picker(self):
        picker = self.make_picker()
        for name in (
            "maybe_schedule_inactive_close",
            "schedule_inactive_close",
            "close_if_inactive",
        ):
            setattr(picker, name, getattr(EmojiPicker, name).__get__(picker))
        controller = Gtk.EventControllerMotion.new()
        controller.connect(
            "leave", lambda source: EmojiPicker.on_pointer_leave(picker, source)
        )

        # GTK can send focus loss before its synthetic pointer leave. That
        # leave has no Gdk event, just like pointer-focus changes during setup.
        EmojiPicker.on_active_changed(picker, None, None)
        self.assertIsNone(picker.pending_inactive_close)
        controller.emit("leave")
        self.assertFalse(picker.pointer_in_picker)
        self.assertIsNotNone(picker.pending_inactive_close)

        loop = GLib.MainLoop()
        GLib.timeout_add(120, lambda: (loop.quit(), GLib.SOURCE_REMOVE)[1])
        loop.run()
        picker.get_application.return_value.close_picker_window.assert_called_once_with()

    def make_picker(self):
        surface = Mock()
        surface.get_state.return_value = Gdk.ToplevelState(0)
        return SimpleNamespace(
            was_active=True,
            pointer_in_picker=True,
            active_dialog=None,
            waiting_for_wayland_setup=False,
            pending_inactive_close=None,
            is_active=Mock(return_value=False),
            menu_button=SimpleNamespace(get_active=Mock(return_value=False)),
            get_visible_dialog=Mock(return_value=None),
            get_application=Mock(),
            get_surface=Mock(return_value=surface),
            schedule_inactive_close=Mock(),
        )

    def test_compositor_drag_keeps_picker_open_without_pointer_or_keyboard_focus(self):
        picker = self.make_picker()
        picker.maybe_schedule_inactive_close = (
            EmojiPicker.maybe_schedule_inactive_close.__get__(picker)
        )

        class Toplevel(GObject.Object):
            state = GObject.Property(type=int, default=int(Gdk.ToplevelState.FOCUSED))

            def get_state(self):
                return Gdk.ToplevelState(self.state)

        surface = Toplevel()
        picker.get_surface.return_value = surface
        picker.on_active_changed = EmojiPicker.on_active_changed.__get__(picker)
        EmojiPicker.on_realize(picker, None)
        controller = Gtk.EventControllerMotion.new()
        controller.connect(
            "leave", lambda source: EmojiPicker.on_pointer_leave(picker, source)
        )

        # Super+drag is handled by GNOME before GTK sees the mouse press.
        # GTK loses both pointer and keyboard focus; the window stays active.
        controller.emit("leave")
        EmojiPicker.on_active_changed(picker, None, None)
        EmojiPicker.close_if_inactive(picker)

        self.assertFalse(picker.pointer_in_picker)
        picker.get_application.return_value.close_picker_window.assert_not_called()

        # A later activation change must still dismiss the picker, even if
        # GTK's keyboard focus was already lost during the drag.
        picker.schedule_inactive_close.reset_mock()
        surface.state = 0
        picker.schedule_inactive_close.assert_called_once_with()
        EmojiPicker.close_if_inactive(picker)

        picker.get_application.return_value.close_picker_window.assert_called_once_with()

    def test_pending_close_does_not_fire_while_pointer_is_in_picker(self):
        picker = self.make_picker()

        EmojiPicker.close_if_inactive(picker)

        picker.get_application.return_value.close_picker_window.assert_not_called()

    def test_finishing_portal_setup_preserves_already_returned_focus(self):
        picker = SimpleNamespace(
            waiting_for_wayland_setup=True,
            root=SimpleNamespace(set_sensitive=Mock()),
            was_active=False,
            pointer_in_picker=True,
            pending_inactive_close=None,
            is_active=Mock(return_value=True),
            get_visible=Mock(return_value=True),
            get_visible_dialog=Mock(return_value=None),
            present=Mock(),
        )

        EmojiPicker.end_wayland_request(picker, present=True)

        self.assertTrue(picker.was_active)
        self.assertFalse(picker.pointer_in_picker)
        picker.present.assert_called_once_with()

    def test_finishing_skip_does_not_disarm_blur_before_focus_returns(self):
        picker = SimpleNamespace(
            waiting_for_wayland_setup=False,
            root=SimpleNamespace(set_sensitive=Mock()),
            was_active=True,
            pointer_in_picker=True,
            pending_inactive_close=None,
            is_active=Mock(return_value=False),
            get_visible=Mock(return_value=True),
            get_visible_dialog=Mock(return_value=None),
            present=Mock(),
        )

        EmojiPicker.end_wayland_request(picker, present=False)

        self.assertTrue(picker.was_active)
        self.assertFalse(picker.pointer_in_picker)
        picker.present.assert_not_called()

    def test_dialog_close_arms_blur_before_focus_return_signal(self):
        dialog = object()
        picker = SimpleNamespace(
            active_dialog=dialog,
            was_active=False,
            pointer_in_picker=True,
            get_visible=Mock(return_value=True),
            is_active=Mock(return_value=False),
            maybe_schedule_inactive_close=Mock(),
        )

        EmojiPicker.on_dialog_closed(picker, dialog)

        self.assertTrue(picker.was_active)
        self.assertFalse(picker.pointer_in_picker)
        picker.maybe_schedule_inactive_close.assert_called_once_with()

    @patch("emote.picker.user_data.load_wayland_auto_paste_choice", return_value=None)
    def test_auto_paste_prompt_is_not_duplicated_while_dialog_is_pending(self, _choice):
        picker = SimpleNamespace(
            get_visible=Mock(return_value=True),
            active_dialog=object(),
            get_visible_dialog=Mock(return_value=None),
        )

        EmojiPicker.show_wayland_paste_choice(picker)

        picker.get_visible_dialog.assert_not_called()
