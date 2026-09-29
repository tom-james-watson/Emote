from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from tempfile import TemporaryDirectory

from emote.keyboard_shortcuts import KeyboardShortcuts, format_accelerator_label


class KeyboardShortcutLabelTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch("emote.user_data.SHELVE_PATH", directory.name + "/user_data")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_formats_portal_accelerator_syntax(self):
        self.assertEqual(format_accelerator_label("<Control><Alt>t"), "Ctrl+Alt+T")

    def test_removes_portal_press_prefix(self):
        self.assertEqual(format_accelerator_label("Press Ctrl+Alt+E"), "Ctrl+Alt+E")

    @patch(
        "emote.keyboard_shortcuts.user_data.load_wayland_global_shortcut_choice",
        return_value=False,
    )
    def test_setup_opens_native_shortcut_configuration(self, _choice):
        application = Mock()
        application.set_wayland_global_shortcut.return_value = True
        dialog = SimpleNamespace(
            picker=SimpleNamespace(get_application=Mock(return_value=application)),
            global_shortcut_button=Mock(),
        )

        KeyboardShortcuts.setup_wayland_global_shortcut(dialog, None)

        application.set_wayland_global_shortcut.assert_called_once_with()
        dialog.global_shortcut_button.set_label.assert_called_once_with("Opening…")
        dialog.global_shortcut_button.set_sensitive.assert_called_once_with(False)

    @patch(
        "emote.keyboard_shortcuts.user_data.load_wayland_global_shortcut_label",
        return_value="Press <Control><Alt>t",
    )
    @patch(
        "emote.keyboard_shortcuts.user_data.load_wayland_global_shortcut_choice",
        return_value=True,
    )
    def test_existing_shortcut_is_displayed_as_read_only_text(self, _choice, _label):
        button = Mock()
        value = Mock()
        dialog = SimpleNamespace(
            global_shortcut_button=button,
            global_shortcut_value=value,
        )

        KeyboardShortcuts.refresh_wayland_global_shortcut(dialog)

        value.set_label.assert_called_once_with("Ctrl+Alt+T")
        value.set_visible.assert_called_once_with(True)
        button.set_visible.assert_called_once_with(False)

    @patch(
        "emote.keyboard_shortcuts.user_data.load_wayland_global_shortcut_choice",
        return_value=False,
    )
    def test_missing_shortcut_is_displayed_as_setup_button(self, _choice):
        button = Mock()
        value = Mock()
        dialog = SimpleNamespace(
            global_shortcut_button=button,
            global_shortcut_value=value,
            picker=Mock(),
        )
        dialog.picker.get_application.return_value.is_wayland_shortcut_registered.return_value = (
            False
        )

        KeyboardShortcuts.refresh_wayland_global_shortcut(dialog)

        button.set_label.assert_called_once_with("Set up…")
        button.set_sensitive.assert_called_once_with(True)
        button.set_visible.assert_called_once_with(True)
        value.set_visible.assert_called_once_with(False)
