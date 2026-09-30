import os
import unittest
from unittest.mock import Mock, patch

from gi.repository import Gio

from emote.wayland_shortcut import SHORTCUT_ID, WaylandShortcut


class FakeBus:
    def get_unique_name(self):
        return ":1.42"


class WaylandShortcutTests(unittest.TestCase):
    def make_shortcut(self):
        self.activated = Mock()
        self.bound = Mock()
        self.missing = Mock()
        shortcut = WaylandShortcut(
            on_activated=self.activated,
            on_bound=self.bound,
            on_missing=self.missing,
            on_unavailable=Mock(),
        )
        shortcut._bus = FakeBus()
        shortcut._generation = 7
        return shortcut

    @patch("emote.wayland_shortcut.Gio.DBusConnection.new_for_address")
    @patch(
        "emote.wayland_shortcut.Gio.dbus_address_get_for_bus_sync",
        return_value="unix:path=/session-bus",
    )
    def test_enable_uses_a_private_bus_connection(self, _get_address, new_connection):
        shortcut = self.make_shortcut()
        shortcut._bus = None

        shortcut.enable()

        self.assertEqual(new_connection.call_args.args[0], "unix:path=/session-bus")
        flags = new_connection.call_args.args[1]
        self.assertTrue(flags & Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT)
        self.assertTrue(flags & Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION)

    def test_portal_paths_encode_bus_name_without_leading_colon(self):
        shortcut = self.make_shortcut()

        self.assertEqual(
            shortcut._request_path("token"),
            "/org/freedesktop/portal/desktop/request/1_42/token",
        )
        self.assertEqual(
            shortcut._session_path("token"),
            "/org/freedesktop/portal/desktop/session/1_42/token",
        )

    @patch.dict(os.environ, {"FLATPAK_ID": "", "SNAP": ""})
    def test_host_registration_is_the_first_portal_call(self):
        shortcut = self.make_shortcut()
        shortcut._enabled = True
        shortcut._bus = Mock()
        shortcut._register_host_app = Mock()
        shortcut._create_session = Mock()

        shortcut._continue_bus_ready(shortcut._generation)

        shortcut._register_host_app.assert_called_once_with(shortcut._generation)
        shortcut._create_session.assert_not_called()

    def test_successful_host_registration_creates_session(self):
        shortcut = self.make_shortcut()
        shortcut._enabled = True
        shortcut._create_session = Mock()
        connection = Mock()

        shortcut._on_host_app_registered(connection, Mock(), shortcut._generation)

        self.assertTrue(shortcut._host_registered)
        shortcut._create_session.assert_called_once_with(shortcut._generation)

    @patch("emote.wayland_shortcut.config.app_id", "com.tomjwatson.Emote.Devel")
    def test_host_registration_uses_current_application_id(self):
        shortcut = self.make_shortcut()
        shortcut._bus = Mock()

        shortcut._register_host_app(shortcut._generation)

        registration = shortcut._bus.call.call_args.args[4]
        self.assertEqual(registration.unpack()[0], "com.tomjwatson.Emote.Devel")

    def test_existing_binding_is_reported_without_rebinding(self):
        shortcut = self.make_shortcut()
        shortcut._bind_shortcut = Mock()

        shortcut._on_shortcuts_listed(
            {"shortcuts": [(SHORTCUT_ID, {"trigger_description": "Super+period"})]}
        )

        self.bound.assert_called_once_with("Super+period")
        self.missing.assert_not_called()
        shortcut._bind_shortcut.assert_not_called()

    def test_duplicate_bound_signal_is_reported_once(self):
        shortcut = self.make_shortcut()
        properties = {"trigger_description": "Press Ctrl+Alt+E"}

        shortcut._notify_bound(properties)
        shortcut._notify_bound(properties)

        self.bound.assert_called_once_with("Press Ctrl+Alt+E")

    def test_missing_binding_is_reported_during_discovery(self):
        shortcut = self.make_shortcut()

        shortcut._on_shortcuts_listed({"shortcuts": []})

        self.missing.assert_called_once_with(False)
        self.bound.assert_not_called()

    def test_legacy_disabled_entry_is_preserved_instead_of_replaced(self):
        shortcut = self.make_shortcut()

        shortcut._on_shortcuts_listed(
            {"shortcuts": [("open-picker", {"trigger_description": ""})]}
        )

        self.assertTrue(shortcut.is_registered)
        self.assertEqual(shortcut._shortcut_id, "open-picker")
        self.missing.assert_called_once_with(True)

    def test_setup_binds_default_when_discovery_finds_nothing(self):
        shortcut = self.make_shortcut()
        shortcut._bind_shortcut = Mock()
        shortcut._bind_requested = True

        shortcut._on_shortcuts_listed({"shortcuts": []})

        shortcut._bind_shortcut.assert_called_once_with(7)
        self.missing.assert_not_called()

    def test_clean_install_bind_includes_preferred_trigger(self):
        shortcut = self.make_shortcut()
        shortcut._session_handle = "/session"
        shortcut._call_request = Mock()

        shortcut._bind_shortcut(shortcut._generation)

        parameters = shortcut._call_request.call_args.args[1].unpack()
        properties = parameters[1][0][1]
        self.assertEqual(properties["preferred_trigger"], "CTRL+ALT+e")

    def test_missing_trigger_description_is_unassigned(self):
        shortcut = self.make_shortcut()

        shortcut._on_shortcut_bound(
            {"shortcuts": [(SHORTCUT_ID, {"description": "Open Emote"})]}
        )

        self.bound.assert_not_called()
        self.missing.assert_called_once_with(True)

    def test_empty_trigger_description_is_unassigned(self):
        shortcut = self.make_shortcut()

        shortcut._on_shortcut_bound(
            {
                "shortcuts": [
                    (SHORTCUT_ID, {"trigger_description": "", "description": "Open"})
                ]
            }
        )

        self.bound.assert_not_called()
        self.missing.assert_called_once_with(True)

    def test_second_bind_starts_a_fresh_session(self):
        shortcut = self.make_shortcut()
        shortcut._enabled = True
        shortcut._session_handle = "/session"
        shortcut._bind_attempted = True
        shortcut.disable = Mock()
        shortcut.enable = Mock()

        shortcut.bind("wayland:parent")

        shortcut.disable.assert_called_once_with()
        shortcut.enable.assert_called_once_with()
        self.assertTrue(shortcut._force_bind)
        self.assertEqual(shortcut._parent_window, "wayland:parent")

    def test_activation_token_is_forwarded(self):
        shortcut = self.make_shortcut()
        shortcut._enabled = True
        shortcut._session_handle = "/session"

        shortcut._on_portal_activated(
            None,
            None,
            None,
            None,
            None,
            Mock(
                unpack=Mock(
                    return_value=(
                        "/session",
                        SHORTCUT_ID,
                        42,
                        {"activation_token": "token"},
                    )
                )
            ),
        )

        self.activated.assert_called_once_with("token")

    @patch("emote.wayland_shortcut.GLib.timeout_add", return_value=99)
    def test_lost_session_clears_state_and_schedules_recovery(self, timeout_add):
        shortcut = self.make_shortcut()
        shortcut._enabled = True
        shortcut._session_handle = "/session"
        shortcut._last_bound_trigger = "Ctrl+Alt+E"

        shortcut._connection_lost(RuntimeError("portal restarted"))

        self.assertFalse(shortcut._enabled)
        self.assertIsNone(shortcut._session_handle)
        self.assertIsNone(shortcut._last_bound_trigger)
        timeout_add.assert_called_once()
        self.assertEqual(shortcut._recover_source, 99)

    def test_removing_and_readding_same_trigger_reports_new_binding(self):
        shortcut = self.make_shortcut()
        shortcut._enabled = True
        shortcut._session_handle = "/session"

        def changed(entries):
            shortcut._on_shortcuts_changed(
                None,
                None,
                None,
                None,
                None,
                Mock(unpack=Mock(return_value=("/session", entries))),
            )

        binding = [(SHORTCUT_ID, {"trigger_description": "Ctrl+Alt+E"})]
        changed(binding)
        changed([])
        changed(binding)

        self.assertEqual(self.bound.call_count, 2)
        self.missing.assert_called_once_with(False)

    def test_existing_unassigned_shortcut_is_remembered(self):
        shortcut = self.make_shortcut()

        shortcut._on_shortcuts_listed(
            {"shortcuts": [(SHORTCUT_ID, {"trigger_description": ""})]}
        )

        self.assertTrue(shortcut.is_registered)
        self.missing.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
