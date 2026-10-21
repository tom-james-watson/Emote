from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from gi.repository import Gdk, GLib

from emote import EmoteApplication, user_data
from emote.clipboard import (
    ClipboardRestore,
    ClipboardSnapshot,
    restoration_available,
    restoration_enabled,
)
from emote.settings import Settings


class ClipboardRestoreTests(TestCase):
    def setUp(self):
        self.clipboard = Mock()
        self.owner = None
        self.clipboard.get_content.side_effect = lambda: self.owner

        def set_content(provider):
            self.owner = provider
            self.restore._changed(self.clipboard)
            return True

        self.clipboard.set_content.side_effect = set_content
        self.restore = ClipboardRestore(self.clipboard)
        self.previous = Gdk.ContentProvider.new_for_bytes(
            "text/html", GLib.Bytes.new(b"<b>original</b>")
        )
        self.enabled = patch("emote.clipboard.restoration_enabled", return_value=True)
        self.enabled.start()
        self.addCleanup(self.enabled.stop)
        self.snapshot = patch("emote.clipboard.ClipboardSnapshot")
        self.snapshot_class = self.snapshot.start()
        self.addCleanup(self.snapshot.stop)
        self.snapshot_class.return_value.start.side_effect = lambda: (
            self.snapshot_class.call_args.args[1](self.previous)
        )

    def copy(self):
        ready = Mock()
        self.restore.copy("👩🏽‍💻", ready)
        ready.assert_called_once()
        self.assertIsNone(ready.call_args.args[1])
        return ready.call_args.args[0]

    @patch("emote.clipboard.GLib.timeout_add", return_value=42)
    @patch("emote.clipboard.GLib.idle_add")
    def test_wait_starts_only_after_input_is_sent(self, idle, timeout):
        sent = self.copy()
        timeout.assert_not_called()
        sent()
        idle.assert_called_once()
        callback, generation = idle.call_args.args
        callback(generation)
        self.assertEqual(timeout.call_args.args[0], 500)
        self.assertIsNot(self.owner, self.previous)
        self.restore._restore(generation)
        self.assertIs(self.owner, self.previous)

    def test_external_copy_even_with_same_text_prevents_restoration(self):
        sent = self.copy()
        self.assertFalse(sent.cancelled)
        generation = self.restore._generation
        self.clipboard.set_content(Gdk.ContentProvider.new_for_value("👩🏽‍💻"))
        external = self.owner
        self.restore._restore(generation)
        self.assertIs(self.owner, external)
        self.assertTrue(sent.cancelled)

    def test_disabled_setting_is_ignored_and_cancels_restoration(self):
        self.copy()
        self.enabled.stop()
        with patch("emote.clipboard.restoration_enabled", return_value=False):
            self.restore._restore(self.restore._generation)
        self.assertIsNot(self.owner, self.previous)

    def test_snapshot_failure_never_replaces_clipboard(self):
        self.snapshot_class.return_value.start.side_effect = lambda: (
            self.snapshot_class.call_args.args[1](None, "unsupported format")
        )
        ready = Mock()
        self.restore.copy("🙂", ready)
        ready.assert_called_once_with(None, "unsupported format")
        self.clipboard.set_content.assert_not_called()

    def test_new_selection_keeps_original_snapshot_and_rejects_old_callback(self):
        self.copy()
        generation = self.restore._generation
        self.copy()
        self.snapshot_class.assert_called_once()
        self.restore._restore(generation)
        self.assertIsNot(self.owner, self.previous)
        self.restore._restore(self.restore._generation)
        self.assertIs(self.owner, self.previous)

    def test_empty_clipboard_is_restored_as_empty(self):
        self.previous = None
        self.copy()
        self.restore._restore(self.restore._generation)
        self.assertIsNone(self.owner)

    @patch("emote.clipboard.GLib.idle_add", side_effect=lambda fn: fn())
    def test_new_copy_releases_unused_portal_without_waiting_for_timeout(self, _idle):
        sent = self.copy()
        release = Mock()
        sent.use_portal(Mock(), release)
        self.copy()
        release.assert_called_once_with()

    @patch("emote.clipboard.GLib.idle_add", side_effect=lambda fn: fn())
    def test_restoration_keeps_portal_alive_to_serve_original_data(self, _idle):
        sent = self.copy()
        setter, release = Mock(), Mock()
        sent.use_portal(setter, release)
        self.restore._restore(self.restore._generation)
        setter.assert_called_once_with(self.previous)
        release.assert_not_called()

    @patch("emote.clipboard.GLib.idle_add", side_effect=lambda fn: fn())
    def test_xwayland_uses_portal_to_monitor_but_restores_through_x11(self, _idle):
        self.restore.portal_restoration = False
        sent = self.copy()
        setter, release, watch = Mock(), Mock(), Mock()
        sent.use_portal(setter, release, watch)
        watch.assert_called_once_with(self.restore.cancel)
        self.restore._restore(self.restore._generation)
        self.assertIs(self.owner, self.previous)
        setter.assert_not_called()
        release.assert_called_once_with()

    @patch("emote.config.is_wayland", True)
    @patch("emote.config.is_gnome", True)
    @patch("emote.user_data.load_wayland_auto_paste_choice", return_value=True)
    @patch("emote.user_data.load_restore_clipboard_enabled", return_value=True)
    def test_gnome_saved_choice_cannot_snapshot_or_request_clipboard_access(self, *_):
        self.enabled.stop()
        sent = self.copy()
        self.snapshot_class.assert_not_called()
        self.assertFalse(sent.needs_portal)
        self.assertIsNone(self.restore._snapshot)


class ClipboardSnapshotTests(TestCase):
    def test_unsupported_local_only_format_aborts_without_clearing_clipboard(self):
        clipboard = Mock()
        clipboard.get_formats.return_value.get_mime_types.return_value = []
        clipboard.get_formats.return_value.is_empty.return_value = False
        ready = Mock()
        ClipboardSnapshot(clipboard, ready).start()
        self.assertIsNotNone(ready.call_args.args[1])
        clipboard.set_content.assert_not_called()

    def test_timeout_completes_once_and_cancels_reads(self):
        ready = Mock()
        snapshot = ClipboardSnapshot(Mock(), ready)
        snapshot._timeout()
        snapshot.fail("late error")
        ready.assert_called_once()
        self.assertTrue(snapshot.cancellable.is_cancelled())

    def test_size_limit_rejects_entire_snapshot(self):
        ready = Mock()
        snapshot = ClipboardSnapshot(Mock(), ready)
        snapshot.stream = Mock()
        stream = Mock()
        stream.read_bytes_finish.return_value = GLib.Bytes.new(b"too large")
        with patch("emote.clipboard.MAX_SNAPSHOT_BYTES", 2):
            snapshot._received(stream, Mock())
        self.assertIn("too large", ready.call_args.args[1])
        self.assertEqual(snapshot.providers, [])


class RestorePreferenceTests(TestCase):
    def setUp(self):
        desktop = patch("emote.config.is_gnome", False)
        desktop.start()
        self.addCleanup(desktop.stop)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch("emote.user_data.SHELVE_PATH", directory.name + "/settings")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_default_off_and_effective_only_with_auto_paste(self):
        self.assertFalse(user_data.load_restore_clipboard_enabled())
        user_data.update_restore_clipboard_enabled(True)
        for wayland in (False, True):
            with self.subTest(wayland=wayland), patch(
                "emote.clipboard.config.is_wayland", wayland
            ):
                for enabled in (False, True):
                    user_data.update_x11_auto_paste_enabled(enabled)
                    user_data.update_wayland_auto_paste_choice(enabled)
                    self.assertEqual(restoration_enabled(), enabled)

    def test_restoration_is_unavailable_only_on_gnome_wayland(self):
        user_data.update_restore_clipboard_enabled(True)
        user_data.update_wayland_auto_paste_choice(True)
        user_data.update_x11_auto_paste_enabled(True)
        for wayland in (False, True):
            for gnome in (False, True):
                with self.subTest(wayland=wayland, gnome=gnome), patch(
                    "emote.config.is_wayland", wayland
                ), patch("emote.config.is_gnome", gnome):
                    expected = not (wayland and gnome)
                    self.assertEqual(restoration_available(), expected)
                    self.assertEqual(restoration_enabled(), expected)

    @patch("emote.config.is_wayland", True)
    @patch("emote.config.is_gnome", True)
    def test_gnome_auto_paste_changes_cannot_show_or_enable_restoration(self):
        user_data.update_wayland_auto_paste_choice(True)
        settings = SimpleNamespace(
            auto_paste=Mock(get_active=lambda: True),
            restore_clipboard=Mock(),
            picker=Mock(),
            _refreshing_auto_paste=False,
            _refreshing_restore=False,
            _restore_request=None,
        )
        Settings.on_auto_paste_changed(settings, settings.auto_paste, None)
        settings.restore_clipboard.set_visible.assert_called_with(False)
        Settings.refresh_wayland_auto_paste(settings)
        settings.restore_clipboard.set_visible.assert_called_with(False)
        Settings.on_restore_clipboard_changed(
            settings, Mock(get_active=lambda: True), None
        )
        self.assertFalse(user_data.load_restore_clipboard_enabled())
        settings.picker.get_application.return_value.ensure_clipboard_access.assert_not_called()

    def test_hidden_preference_changes_are_ignored(self):
        settings = SimpleNamespace(
            auto_paste=Mock(), _restore_request=None, _refreshing_restore=False
        )
        settings.picker = SimpleNamespace(
            clipboard_restore=SimpleNamespace(needs_portal=False)
        )
        settings.auto_paste.get_active.return_value = False
        Settings.on_restore_clipboard_changed(
            settings, Mock(get_active=lambda: True), None
        )
        self.assertFalse(user_data.load_restore_clipboard_enabled())
        settings.auto_paste.get_active.return_value = True
        Settings.on_restore_clipboard_changed(
            settings, Mock(get_active=lambda: True), None
        )
        self.assertTrue(user_data.load_restore_clipboard_enabled())

    @patch("emote.settings.config.is_wayland", True)
    @patch("emote.settings.Adw.AlertDialog.new")
    def test_permission_is_requested_before_saving_enabled_setting(self, alert):
        for error in (None, RuntimeError("declined")):
            with self.subTest(error=error):
                user_data.update_restore_clipboard_enabled(False)
                application = Mock()
                settings = SimpleNamespace(
                    auto_paste=Mock(get_active=lambda: True),
                    _restore_request=None,
                    _refreshing_restore=False,
                    picker=Mock(),
                )
                settings.picker.clipboard_restore.needs_portal = True
                settings.picker.get_application.return_value = application
                row = Mock(get_active=lambda: True)
                Settings.on_restore_clipboard_changed(settings, row, None)
                application.ensure_clipboard_access.assert_called_once()
                self.assertFalse(user_data.load_restore_clipboard_enabled())
                row.set_sensitive.assert_called_once_with(False)
                application.ensure_clipboard_access.call_args.args[0](error)
                self.assertEqual(
                    user_data.load_restore_clipboard_enabled(), error is None
                )
                row.set_active.assert_called_with(error is None)
                row.set_sensitive.assert_called_with(True)

    @patch("emote.settings.config.is_wayland", True)
    def test_stale_permission_response_cannot_enable_restoration(self):
        application = Mock()
        settings = SimpleNamespace(
            auto_paste=Mock(get_active=lambda: True),
            _restore_request=None,
            _refreshing_restore=False,
            picker=Mock(),
        )
        settings.picker.clipboard_restore.needs_portal = True
        settings.picker.get_application.return_value = application
        Settings.on_restore_clipboard_changed(
            settings, Mock(get_active=lambda: True), None
        )
        settings._restore_request = None
        application.ensure_clipboard_access.call_args.args[0](None)
        self.assertFalse(user_data.load_restore_clipboard_enabled())

    @patch("emote.config.is_wayland", True)
    @patch("emote.WaylandPaste")
    def test_saved_restore_setting_preflights_when_automatic_paste_starts(
        self, factory
    ):
        user_data.update_restore_clipboard_enabled(True)
        user_data.update_wayland_auto_paste_choice(True)
        backend = factory.return_value
        backend.is_ready = False
        application = SimpleNamespace(
            wayland_paste=None,
            picker_window=Mock(),
            on_wayland_paste_ready=Mock(),
            on_wayland_paste_unavailable=Mock(),
            finish_saved_clipboard_access=Mock(),
            request_clipboard_access=Mock(),
        )
        application.picker_window.clipboard_restore.needs_portal = True
        EmoteApplication.maybe_start_wayland_paste(application)
        application.request_clipboard_access.assert_called_once_with(
            backend, application.finish_saved_clipboard_access
        )
        backend.ensure_started.assert_called_once()
        application.picker_window.begin_wayland_request.assert_called_once()

        # A setting saved on KDE must not request clipboard access on GNOME.
        application.wayland_paste = None
        application.request_clipboard_access.reset_mock()
        with patch("emote.config.is_gnome", True):
            EmoteApplication.maybe_start_wayland_paste(application)
        application.request_clipboard_access.assert_not_called()

    def test_keyboard_readiness_does_not_unlock_picker_during_clipboard_prompt(self):
        backend = SimpleNamespace(clipboard_pending=True)
        application = SimpleNamespace(wayland_paste=backend, picker_window=Mock())
        EmoteApplication.handle_wayland_paste_ready(application, backend)
        application.picker_window.end_wayland_request.assert_not_called()
        backend.clipboard_pending = False
        EmoteApplication.handle_wayland_paste_ready(application, backend)
        application.picker_window.end_wayland_request.assert_called_once_with(
            present=True
        )

    @patch("emote.GLib.idle_add")
    def test_clipboard_permission_completion_runs_on_gtk_thread(self, idle):
        for ready in (False, True):
            with self.subTest(ready=ready):
                backend = Mock(is_ready=ready)
                application = SimpleNamespace(
                    wayland_paste=backend, picker_window=Mock()
                )
                callback = Mock()
                EmoteApplication.request_clipboard_access(
                    application, backend, callback
                )
                application.picker_window.begin_wayland_request.assert_called_once()
                error = RuntimeError("declined")
                backend.request_clipboard.call_args.args[0](error)
                callback.assert_not_called()
                idle.call_args.args[0]()
                callback.assert_called_once_with(error)
                if ready:
                    application.picker_window.end_wayland_request.assert_called_once_with(
                        present=True
                    )
                else:
                    application.picker_window.end_wayland_request.assert_not_called()

    @patch("emote.GLib.idle_add")
    def test_stale_backend_cannot_complete_permission_or_reset_saved_choice(self, idle):
        user_data.update_restore_clipboard_enabled(True)
        backend = Mock(is_ready=True)
        application = SimpleNamespace(wayland_paste=backend, picker_window=Mock())
        callback = lambda error: EmoteApplication.finish_saved_clipboard_access(
            application, error
        )
        EmoteApplication.request_clipboard_access(application, backend, callback)
        backend.request_clipboard.call_args.args[0](RuntimeError("disabled"))
        application.wayland_paste = Mock()
        idle.call_args.args[0]()
        self.assertTrue(user_data.load_restore_clipboard_enabled())
        application.picker_window.end_wayland_request.assert_not_called()

    def test_saved_permission_failure_refreshes_preferences_and_disables_restoration(
        self,
    ):
        user_data.update_restore_clipboard_enabled(True)
        picker = Mock()
        # Portal focus can hide the dialog temporarily.
        picker.get_visible_dialog.return_value = None
        application = SimpleNamespace(picker_window=picker)
        EmoteApplication.finish_saved_clipboard_access(
            application, RuntimeError("denied")
        )
        self.assertFalse(user_data.load_restore_clipboard_enabled())
        picker.active_dialog.refresh_clipboard_restoration.assert_called_once()
