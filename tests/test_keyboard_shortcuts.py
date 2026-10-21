from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from tempfile import TemporaryDirectory

from emote.keyboard_shortcuts import (
    KeyboardShortcuts,
    ShortcutLabel,
    parse_shortcut_accelerator,
)
from gi.repository import Gdk


class KeyboardShortcutLabelTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch("emote.user_data.SHELVE_PATH", directory.name + "/user_data")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_parses_portal_descriptions_for_keycaps(self):
        for description in ("<Control><Alt>e", "Ctrl+Alt+E", "Press Ctrl+Alt+E"):
            with self.subTest(description=description):
                self.assertEqual(
                    parse_shortcut_accelerator(description), "<Control><Alt>e"
                )

    def test_preserves_unknown_portal_descriptions_as_text(self):
        for description in (
            "",
            "Disabled",
            "Unassigned",
            "Press a shortcut…",
            "Include Ctrl, Alt, or Super",
            "Custom+E",
            "Desktop shortcut: Ctrl+E",
        ):
            with self.subTest(description=description):
                self.assertIsNone(parse_shortcut_accelerator(description))

    def test_recording_prompt_is_preserved_verbatim(self):
        label = SimpleNamespace(keycaps=Mock(), text=Mock())

        ShortcutLabel.set_label(label, "Press a shortcut…")

        label.text.set_label.assert_called_once_with("Press a shortcut…")
        label.text.set_visible.assert_called_once_with(True)
        label.keycaps.set_visible.assert_called_once_with(False)

    def test_recording_waits_for_non_modifier_key(self):
        dialog = SimpleNamespace(
            recording=True,
            record_button=Mock(),
            update_accelerator=Mock(),
        )

        KeyboardShortcuts.on_key_pressed(
            dialog, None, Gdk.KEY_Alt_L, 0, Gdk.ModifierType.CONTROL_MASK
        )
        self.assertTrue(dialog.recording)
        dialog.update_accelerator.assert_not_called()

        KeyboardShortcuts.on_key_pressed(
            dialog,
            None,
            Gdk.KEY_e,
            0,
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK,
        )
        self.assertFalse(dialog.recording)
        dialog.update_accelerator.assert_called_once_with(
            "<Control><Alt>e", "Ctrl+Alt+E"
        )
        dialog.record_button.get_child().set_label.assert_called_once_with(
            "Ctrl+Alt+E", "<Control><Alt>e"
        )

    def test_shift_alone_is_not_a_global_shortcut(self):
        dialog = SimpleNamespace(
            recording=True,
            record_button=Mock(),
            update_accelerator=Mock(),
        )

        KeyboardShortcuts.on_key_pressed(
            dialog, None, Gdk.KEY_e, 0, Gdk.ModifierType.SHIFT_MASK
        )

        self.assertTrue(dialog.recording)
        dialog.update_accelerator.assert_not_called()

    def test_removes_portal_press_prefix(self):
        self.assertEqual(
            parse_shortcut_accelerator("Press <Control><Alt>t"), "<Control><Alt>t"
        )

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

        value.set_label.assert_called_once_with("Press <Control><Alt>t")
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
