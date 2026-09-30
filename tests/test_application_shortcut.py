from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from tempfile import TemporaryDirectory

from emote import EmoteApplication, user_data


class ApplicationShortcutTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch("emote.user_data.SHELVE_PATH", directory.name + "/user_data")
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_application(self):
        shortcut = SimpleNamespace(
            bind=Mock(),
            is_registered=False,
        )
        picker = SimpleNamespace(
            get_visible=Mock(return_value=True),
            begin_wayland_request=Mock(),
            get_portal_parent=Mock(),
        )
        application = SimpleNamespace(
            wayland_shortcut=shortcut,
            picker_window=picker,
            pending_wayland_shortcut_setup=False,
            wayland_shortcut_onboarding=None,
        )
        return application, shortcut, picker

    @patch("emote.config.is_wayland", True)
    @patch("emote.config.is_flatpak", False)
    @patch("emote.emojis.init")
    @patch("emote.css.load_css")
    @patch("emote.setproctitle")
    @patch("emote.WaylandShortcut")
    def test_start_restores_saved_shortcut_with_bind(
        self, shortcut_class, _title, _css, _emojis
    ):
        user_data.update_wayland_global_shortcut_choice(True)
        application = SimpleNamespace(
            hold=Mock(),
            maybe_start_wayland_paste=Mock(),
            on_hotkey=Mock(),
            on_wayland_shortcut_bound=Mock(),
            on_wayland_shortcut_missing=Mock(),
            on_wayland_shortcut_unavailable=Mock(),
        )

        EmoteApplication.start_daemon(application)

        shortcut_class.return_value.bind.assert_called_once_with()
        shortcut_class.return_value.enable.assert_not_called()

    @patch("emote.config.is_wayland", True)
    def test_setup_always_uses_bind_shortcuts(self):
        application, shortcut, picker = self.make_application()
        application.bind_wayland_shortcut = Mock()

        started = EmoteApplication.set_wayland_global_shortcut(application)

        self.assertTrue(started)
        picker.begin_wayland_request.assert_called_once_with()
        picker.get_portal_parent.assert_called_once_with(
            application.bind_wayland_shortcut
        )

    def test_legacy_launch_still_presents_emote(self):
        application = SimpleNamespace(
            started=True,
            picker_window=Mock(),
            prepare_wayland_picker_focus=Mock(),
            on_picker_presented=Mock(),
        )
        # An existing desktop command starts a secondary GApplication process.
        EmoteApplication.do_activate(application)
        application.picker_window.present.assert_called_once_with()
        application.on_picker_presented.assert_called_once_with()

    def test_setup_response_continues_onboarding_directly(self):
        application = SimpleNamespace(
            pending_wayland_shortcut_setup=True,
            wayland_shortcut_onboarding=True,
            picker_window=Mock(),
            refresh_wayland_shortcut_preferences=Mock(),
            continue_wayland_setup=Mock(),
        )

        EmoteApplication.handle_wayland_shortcut_bound(application, "Super+period")

        application.continue_wayland_setup.assert_called_once_with()
        application.picker_window.end_wayland_request.assert_called_once_with(
            present=True
        )
        self.assertTrue(user_data.load_wayland_global_shortcut_choice())
        self.assertEqual(user_data.load_wayland_global_shortcut_label(), "Super+period")
        self.assertFalse(application.pending_wayland_shortcut_setup)

    def test_setup_from_shortcuts_dialog_does_not_restart_onboarding(self):
        application = SimpleNamespace(
            pending_wayland_shortcut_setup=True,
            wayland_shortcut_onboarding=False,
            picker_window=Mock(),
            refresh_wayland_shortcut_preferences=Mock(),
            continue_wayland_setup=Mock(),
        )

        EmoteApplication.handle_wayland_shortcut_bound(application, "Ctrl+Alt+E")

        application.continue_wayland_setup.assert_not_called()
        application.picker_window.end_wayland_request.assert_called_once_with(
            present=True
        )

    def test_cancelled_setup_continues_and_remembers_skip(self):
        application = self.make_missing_application()
        application.pending_wayland_shortcut_setup = True
        application.wayland_shortcut_onboarding = True
        application.picker_window.get_visible.return_value = True

        EmoteApplication.handle_wayland_shortcut_unavailable(
            application, RuntimeError()
        )

        self.assertFalse(user_data.load_wayland_global_shortcut_choice())
        self.assertFalse(application.pending_wayland_shortcut_setup)
        self.assertFalse(application.wayland_shortcut_needs_setup)
        application.continue_wayland_setup.assert_called_once_with()
        application.picker_window.end_wayland_request.assert_called_once_with(
            present=True
        )

    def test_portal_failure_preserves_existing_shortcut_choice(self):
        user_data.update_wayland_global_shortcut_choice(True)
        application = self.make_missing_application()

        EmoteApplication.handle_wayland_shortcut_unavailable(
            application, RuntimeError("portal unavailable")
        )

        self.assertTrue(user_data.load_wayland_global_shortcut_choice())

    @patch("emote.config.is_wayland", True)
    def test_saved_disabled_shortcut_does_not_rebind(self):
        application, shortcut, picker = self.make_application()
        shortcut.is_registered = True
        picker.show_wayland_shortcut_unassigned = Mock()

        self.assertFalse(EmoteApplication.set_wayland_global_shortcut(application))

        shortcut.bind.assert_not_called()
        picker.show_wayland_shortcut_unassigned.assert_called_once_with(False)

    def test_refreshes_tracked_dialog_when_adwaita_reports_none_visible(self):
        dialog = SimpleNamespace(refresh_wayland_global_shortcut=Mock())
        application = SimpleNamespace(
            picker_window=SimpleNamespace(
                get_visible_dialog=Mock(return_value=None),
                active_dialog=dialog,
            )
        )

        EmoteApplication.refresh_wayland_shortcut_preferences(application)

        dialog.refresh_wayland_global_shortcut.assert_called_once_with()

    @staticmethod
    def make_missing_application():
        picker = SimpleNamespace(
            end_wayland_request=Mock(),
            get_visible=Mock(return_value=False),
            show_wayland_shortcut_unassigned=Mock(),
        )
        return SimpleNamespace(
            wayland_shortcut_checked=False,
            pending_wayland_shortcut_setup=False,
            wayland_shortcut_onboarding=False,
            wayland_shortcut_needs_setup=False,
            picker_window=picker,
            refresh_wayland_shortcut_preferences=Mock(),
            continue_wayland_setup=Mock(),
            on_picker_presented=Mock(),
        )

    def test_first_run_asks_once_and_remembers_skip(self):
        application = self.make_missing_application()
        self.assertIsNone(user_data.load_wayland_global_shortcut_choice())

        EmoteApplication.handle_wayland_shortcut_missing(application)
        self.assertTrue(application.wayland_shortcut_needs_setup)
        self.assertFalse(user_data.load_wayland_global_shortcut_choice())

        application.wayland_shortcut_needs_setup = False
        EmoteApplication.handle_wayland_shortcut_missing(application)
        self.assertFalse(application.wayland_shortcut_needs_setup)

    def test_unassigned_portal_offer_continues_without_extra_dialog(self):
        application = self.make_missing_application()
        application.pending_wayland_shortcut_setup = True
        application.wayland_shortcut_onboarding = True

        EmoteApplication.handle_wayland_shortcut_missing(application, True)

        application.picker_window.show_wayland_shortcut_unassigned.assert_not_called()
        application.continue_wayland_setup.assert_called_once_with()
