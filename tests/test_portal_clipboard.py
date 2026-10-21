from unittest import TestCase
from unittest.mock import Mock, patch

from gi.repository import GLib

from emote import portal_clipboard


class ClipboardLeaseTests(TestCase):
    def setUp(self):
        self.bus = Mock()
        self.lease = portal_clipboard.ClipboardLease(self.bus, "/session/ours")

    def owner_changed(self, path, owned):
        self.lease._signal(
            None,
            None,
            None,
            None,
            "SelectionOwnerChanged",
            GLib.Variant(
                "(oa{sv})", (path, {"session_is_owner": GLib.Variant("b", owned)})
            ),
        )

    def test_object_path_is_filtered_in_handler_instead_of_string_match_rule(self):
        self.assertIsNone(self.bus.signal_subscribe.call_args_list[0].args[4])
        self.owner_changed("/session/other", True)
        self.assertFalse(self.lease.claimed)
        self.owner_changed("/session/ours", False)
        self.assertFalse(self.lease.finished.is_set())
        self.owner_changed("/session/ours", True)
        self.assertTrue(self.lease.claimed)
        self.owner_changed("/session/other", False)
        self.assertFalse(self.lease.finished.is_set())
        self.owner_changed("/session/ours", False)
        self.assertTrue(self.lease.finished.is_set())

    def test_remote_permission_revocation_wakes_worker(self):
        self.lease._closed()
        self.assertTrue(self.lease.revoked)
        self.assertTrue(self.lease.finished.is_set())
        self.lease.close()
        self.assertEqual(self.bus.signal_unsubscribe.call_count, 2)

    def test_normal_owner_loss_is_not_reported_as_revocation(self):
        self.owner_changed("/session/ours", True)
        self.owner_changed("/session/ours", False)
        self.lease._closed()
        self.assertFalse(self.lease.revoked)

    def test_empty_restoration_stays_alive_until_the_next_copy(self):
        self.lease.claim(None)
        call = self.bus.call.call_args
        self.assertEqual(call.args[3], "SetSelection")
        self.assertEqual(
            call.args[4].unpack(),
            ("/session/ours", {"mime_types": ["text/plain;charset=utf-8"]}),
        )
        call.args[-1](self.bus, Mock())
        self.owner_changed("/session/ours", True)
        self.assertFalse(self.lease.finished.is_set())
        self.owner_changed("/session/ours", False)
        self.assertTrue(self.lease.finished.is_set())

    def test_missing_provider_rejects_transfer(self):
        with patch.object(self.lease, "_write_done") as done:
            self.lease._transfer("text/html", 17)
        done.assert_called_once_with(17, False)

    def test_copy_before_restoration_cancels_even_without_x11_notification(self):
        cancel = Mock()
        self.owner_changed("/session/ours", False)
        self.lease.watch(cancel)
        self.owner_changed("/session/other", False)
        cancel.assert_not_called()
        self.owner_changed("/session/ours", False)
        cancel.assert_called_once_with()


class ClipboardNegotiationTests(TestCase):
    def test_upgrade_of_keyboard_only_token_asks_for_clipboard_once(self):
        from libei import portal

        bus = Mock()
        responses = [
            (0, {"session_handle": "/old"}),
            (0, {}),
            (0, {"clipboard_enabled": False}),
            (0, {"session_handle": "/new"}),
            (0, {}),
            (0, {"clipboard_enabled": True, "restore_token": "clipboard-grant"}),
        ]
        with patch.object(
            portal_clipboard.Gio, "bus_get_sync", return_value=bus
        ), patch.object(
            portal, "_request", side_effect=responses
        ) as request, patch.object(
            portal, "_close_session"
        ) as close, patch.object(
            portal, "_call_for_fd", return_value=12
        ), patch.object(
            portal, "RemoteDesktopSession"
        ) as session, patch.object(
            portal_clipboard, "ClipboardLease"
        ) as lease:
            result, active = portal_clipboard.negotiate(portal, "keyboard-grant")
        self.assertIs(result, session.return_value)
        self.assertIs(active, lease.return_value)
        close.assert_called_once_with(
            bus, portal_clipboard.Gio, GLib, portal_clipboard.BUS, "/old"
        )
        self.assertIn("restore_token", request.call_args_list[1].args[-2])
        self.assertNotIn("restore_token", request.call_args_list[4].args[-2])
        session.assert_called_once_with(bus, 12, "clipboard-grant", "/new")
        self.assertEqual(
            [call.args[3] for call in bus.call_sync.call_args_list],
            ["RequestClipboard", "RequestClipboard"],
        )

    def test_declined_clipboard_permission_does_not_repeat_consent_forever(self):
        from libei import portal

        responses = [
            (0, {"session_handle": "/new"}),
            (0, {}),
            (0, {"clipboard_enabled": False}),
        ]
        with patch.object(
            portal_clipboard.Gio, "bus_get_sync", return_value=Mock()
        ), patch.object(portal, "_request", side_effect=responses), patch.object(
            portal, "_close_session"
        ) as close, patch.object(
            portal_clipboard, "ClipboardLease"
        ), self.assertRaises(
            portal_clipboard.ClipboardPermissionError
        ):
            portal_clipboard.negotiate(portal, None)
        close.assert_called_once()
