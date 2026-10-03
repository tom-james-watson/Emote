from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from emote import EmoteApplication, user_data
from emote.picker import EmojiPicker
from tests import isolate_user_data


class PasteCancellationTests(TestCase):
    @patch("emote.config.is_wayland", True)
    def test_copy_only_mode_does_not_reopen_picker_or_report_failure(self):
        with TemporaryDirectory() as directory, isolate_user_data(directory):
            user_data.update_wayland_auto_paste_choice(False)
            application = SimpleNamespace(
                wayland_paste=None,
                wayland_paste_error_pending=False,
                activate=Mock(),
            )

            EmoteApplication.paste_wayland(application)

            application.activate.assert_not_called()
            self.assertFalse(application.wayland_paste_error_pending)
            self.assertFalse(user_data.load_wayland_auto_paste_choice())

    @patch("emote.config.is_wayland", True)
    @patch("emote.picker.Adw.AlertDialog.new")
    def test_cancel_releases_input_and_keeps_failure_dialog_tracked(self, new_dialog):
        with TemporaryDirectory() as directory, isolate_user_data(directory):
            for shortcut_enabled in (False, True):
                with self.subTest(shortcut_enabled=shortcut_enabled):
                    user_data.update_wayland_global_shortcut_choice(shortcut_enabled)
                    user_data.update_wayland_auto_paste_choice(True)
                    backend = Mock()
                    picker = SimpleNamespace(
                        waiting_for_wayland_setup=True,
                        root=Mock(),
                        was_active=True,
                        pointer_in_picker=False,
                        pending_inactive_close=None,
                        active_dialog=None,
                        is_active=Mock(return_value=False),
                        get_visible=Mock(return_value=True),
                        get_visible_dialog=Mock(return_value=None),
                        present=Mock(),
                        on_dialog_closed=Mock(),
                    )
                    for name in (
                        "end_wayland_request",
                        "show_dialog",
                        "show_wayland_paste_unavailable",
                    ):
                        setattr(
                            picker, name, getattr(EmojiPicker, name).__get__(picker)
                        )
                    application = SimpleNamespace(
                        wayland_paste=backend,
                        picker_window=picker,
                        wayland_paste_error_pending=False,
                    )
                    application.set_wayland_auto_paste = (
                        EmoteApplication.set_wayland_auto_paste.__get__(application)
                    )

                    EmoteApplication.handle_wayland_paste_unavailable(
                        application, backend
                    )

                    self.assertFalse(picker.waiting_for_wayland_setup)
                    picker.root.set_sensitive.assert_called_once_with(True)
                    self.assertIs(picker.active_dialog, new_dialog.return_value)
                    picker.present.assert_called_once_with()
                    backend.close.assert_called_once_with(discard_token=True)
                    self.assertIsNone(application.wayland_paste)
                    self.assertFalse(user_data.load_wayland_auto_paste_choice())
                    self.assertFalse(application.wayland_paste_error_pending)
                    # Reopening must not re-enter a dead permission request.
                    EmoteApplication.prepare_picker_focus(
                        SimpleNamespace(
                            picker_window=picker, pending_activation_token=None
                        )
                    )
                    self.assertFalse(picker.waiting_for_wayland_setup)
