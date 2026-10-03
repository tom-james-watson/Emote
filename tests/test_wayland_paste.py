import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from emote.wayland_paste import (
    PermissionNotSavedError,
    SessionEndedError,
    WaylandPaste,
    load_restore_token,
    save_restore_token,
)


class WaylandPasteTests(unittest.TestCase):
    def test_paste_is_rejected_until_permission_setup_finishes(self):
        backend = WaylandPaste()

        self.assertFalse(backend.paste())

    def test_ready_paste_is_queued(self):
        backend = WaylandPaste()
        backend._ready.set()

        self.assertTrue(backend.paste())
        self.assertTrue(backend._requests.get_nowait())

    def test_close_immediately_removes_readiness(self):
        backend = WaylandPaste()
        backend._ready.set()

        backend.close()

        self.assertFalse(backend.is_ready)
        self.assertFalse(backend.paste())

    @patch("libei.ei.Sender.create_for_fd")
    @patch("libei.portal.RemoteDesktopSession.negotiate")
    def test_permission_and_each_paste_close_their_session(self, negotiate, sender):
        with TemporaryDirectory() as directory, patch(
            "emote.wayland_paste.TOKEN_PATH", Path(directory) / "token"
        ):
            sessions = [Mock(restore_token=token) for token in ("one", "two", "three")]
            for session in sessions:
                session.__enter__ = Mock(return_value=session)
                session.__exit__ = Mock(return_value=False)
            negotiate.side_effect = sessions
            backend = WaylandPaste()

            def ready(_backend):
                sessions[0].__exit__.assert_called_once()
                self.assertTrue(backend.paste())
                self.assertTrue(backend.paste())

            backend._on_ready = ready

            def serve(_sender, _ei, paste):
                if backend._serve.call_count == 3:
                    backend.close()

            backend._serve = Mock(side_effect=serve)
            backend._run()

            self.assertEqual(
                [call.kwargs["restore_token"] for call in negotiate.call_args_list],
                [None, "one", "two"],
            )
            self.assertEqual(
                [call.args[2] for call in backend._serve.call_args_list],
                [False, True, True],
            )
            for session in sessions:
                session.__exit__.assert_called_once()
            self.assertEqual(sender.return_value.release.call_count, 3)
            self.assertEqual(load_restore_token(), "three")

    @patch("libei.portal.RemoteDesktopSession.negotiate")
    def test_saved_permission_does_not_open_an_idle_session(self, negotiate):
        with TemporaryDirectory() as directory, patch(
            "emote.wayland_paste.TOKEN_PATH", Path(directory) / "token"
        ):
            save_restore_token("saved")
            backend = WaylandPaste(on_ready=lambda backend: backend.close())

            backend._run()

            negotiate.assert_not_called()
            self.assertEqual(load_restore_token(), "saved")

    @patch("emote.wayland_paste.select.select")
    @patch("libei.ei.Sender.create_for_fd")
    @patch("libei.portal.RemoteDesktopSession.negotiate")
    def test_persistent_session_is_reused_and_closes_when_disabled(
        self, negotiate, sender_factory, select
    ):
        from libei import ei

        with TemporaryDirectory() as directory, patch(
            "emote.wayland_paste.TOKEN_PATH", Path(directory) / "token"
        ):
            save_restore_token("saved")
            session = Mock(restore_token="renewed")
            session.__enter__ = Mock(return_value=session)
            session.__exit__ = Mock(return_value=False)
            negotiate.return_value = session
            device = Mock(capabilities=(ei.DeviceCapability.KEYBOARD,))
            sender = sender_factory.return_value
            sender.events = [
                Mock(event_type=ei.EventType.DEVICE_RESUMED, device=device)
            ]
            select.return_value = ([sender.fd], [], [])
            backend = WaylandPaste(keep_session_open=True)

            def ready(_backend):
                session.__exit__.assert_not_called()
                backend.paste()
                backend.paste()

            def pasted(_device):
                if backend._send_paste.call_count == 2:
                    backend.close(discard_token=True)

            backend._on_ready = Mock(side_effect=ready)
            backend._send_paste = Mock(side_effect=pasted)
            backend._run()

            negotiate.assert_called_once()
            backend._on_ready.assert_called_once_with(backend)
            self.assertEqual(backend._send_paste.call_count, 2)
            session.__exit__.assert_called_once()
            sender.release.assert_called_once()
            self.assertFalse(backend.is_ready)
            self.assertIsNone(load_restore_token())

    @patch("emote.wayland_paste.select.select")
    @patch("libei.ei.Sender.create_for_fd")
    @patch("libei.portal.RemoteDesktopSession.negotiate")
    def test_persistent_session_detects_desktop_stop_while_idle(
        self, negotiate, sender_factory, select
    ):
        from libei import ei

        with TemporaryDirectory() as directory, patch(
            "emote.wayland_paste.TOKEN_PATH", Path(directory) / "token"
        ):
            session = Mock(restore_token="saved")
            session.__enter__ = Mock(return_value=session)
            session.__exit__ = Mock(return_value=False)
            negotiate.return_value = session
            device = Mock(capabilities=(ei.DeviceCapability.KEYBOARD,))
            sender = sender_factory.return_value
            sender.events = []
            events = iter(
                [
                    [Mock(event_type=ei.EventType.DEVICE_RESUMED, device=device)],
                    [Mock(event_type=ei.EventType.DISCONNECT)],
                ]
            )
            sender.dispatch.side_effect = lambda: setattr(
                sender, "events", next(events)
            )
            select.return_value = ([sender.fd], [], [])
            ready, unavailable = Mock(), Mock()
            backend = WaylandPaste(
                on_ready=ready, on_unavailable=unavailable, keep_session_open=True
            )
            backend._send_paste = Mock()
            backend._run()

            ready.assert_called_once_with(backend)
            self.assertIsInstance(unavailable.call_args.args[1], SessionEndedError)
            backend._send_paste.assert_not_called()
            negotiate.assert_called_once()
            session.__exit__.assert_called_once()
            sender.release.assert_called_once()
            self.assertFalse(backend.paste())

    @patch("emote.wayland_paste.time.monotonic", side_effect=[0, 20])
    @patch("emote.wayland_paste.select.select")
    def test_persistent_keyboard_can_pause_and_resume(self, select, _time):
        from libei import ei

        device = Mock(capabilities=(ei.DeviceCapability.KEYBOARD,))
        sender = Mock()
        events = iter(
            [
                [Mock(event_type=ei.EventType.DEVICE_RESUMED, device=device)],
                [Mock(event_type=ei.EventType.DEVICE_PAUSED, device=device)],
                [Mock(event_type=ei.EventType.DEVICE_RESUMED, device=device)],
            ]
        )
        sender.dispatch.side_effect = lambda: setattr(sender, "events", next(events))
        backend = WaylandPaste(keep_session_open=True)

        def poll(*_args):
            if select.call_count == 3:
                self.assertFalse(backend.is_ready)
                self.assertFalse(backend.paste())
            return ([sender.fd], [], [])

        def ready(_backend):
            if backend._on_ready.call_count == 2:
                self.assertTrue(backend.paste())

        select.side_effect = poll
        backend._on_ready = Mock(side_effect=ready)
        backend._send_paste = Mock(side_effect=lambda _device: backend.close())
        backend._serve(sender, ei, paste=False)

        self.assertEqual(backend._on_ready.call_count, 2)
        backend._send_paste.assert_called_once_with(device)

    @patch("libei.ei.Sender.create_for_fd")
    @patch("libei.portal.RemoteDesktopSession.negotiate")
    def test_session_ending_does_not_replay_queued_pastes(self, negotiate, sender):
        with TemporaryDirectory() as directory, patch(
            "emote.wayland_paste.TOKEN_PATH", Path(directory) / "token"
        ):
            save_restore_token("saved")
            session = Mock(restore_token="renewed")
            session.__enter__ = Mock(return_value=session)
            session.__exit__ = Mock(return_value=False)
            negotiate.return_value = session
            unavailable = Mock()
            backend = WaylandPaste(on_unavailable=unavailable)
            backend._on_ready = lambda backend: (backend.paste(), backend.paste())
            error = SessionEndedError("stopped")
            backend._serve = Mock(side_effect=error)

            backend._run()

            negotiate.assert_called_once()
            session.__exit__.assert_called_once()
            sender.return_value.release.assert_called_once()
            unavailable.assert_called_once_with(backend, error)
            self.assertFalse(backend.is_ready)
            self.assertFalse(backend.paste())

    @patch("libei.portal.RemoteDesktopSession.negotiate")
    def test_cancel_during_negotiation_closes_session_and_discards_permission(
        self, negotiate
    ):
        with TemporaryDirectory() as directory, patch(
            "emote.wayland_paste.TOKEN_PATH", Path(directory) / "token"
        ):
            session = Mock(restore_token="late")
            session.__enter__ = Mock(return_value=session)
            session.__exit__ = Mock(return_value=False)
            unavailable = Mock()
            backend = WaylandPaste(on_unavailable=unavailable)
            backend._serve = Mock()

            def finish_negotiation(**_kwargs):
                backend.close(discard_token=True)
                return session

            negotiate.side_effect = finish_negotiation
            backend._run()

            session.__exit__.assert_called_once()
            backend._serve.assert_not_called()
            unavailable.assert_not_called()
            self.assertIsNone(load_restore_token())

    @patch("libei.portal.RemoteDesktopSession.negotiate")
    def test_old_cancelled_request_cannot_erase_a_new_permission(self, negotiate):
        with TemporaryDirectory() as directory, patch(
            "emote.wayland_paste.TOKEN_PATH", Path(directory) / "token"
        ):
            session = Mock(restore_token="old")
            session.__enter__ = Mock(return_value=session)
            session.__exit__ = Mock(return_value=False)
            backend = WaylandPaste()

            def finish_negotiation(**_kwargs):
                backend.close(discard_token=True)
                save_restore_token("new")
                return session

            negotiate.side_effect = finish_negotiation
            backend._run()

            self.assertEqual(load_restore_token(), "new")
            session.__exit__.assert_called_once()

    @patch("libei.portal.RemoteDesktopSession.negotiate")
    def test_permission_without_persistence_does_not_enable_repeated_prompts(
        self, negotiate
    ):
        with TemporaryDirectory() as directory, patch(
            "emote.wayland_paste.TOKEN_PATH", Path(directory) / "token"
        ):
            session = Mock(restore_token=None)
            session.__enter__ = Mock(return_value=session)
            session.__exit__ = Mock(return_value=False)
            negotiate.return_value = session
            ready = Mock()
            unavailable = Mock()
            backend = WaylandPaste(on_ready=ready, on_unavailable=unavailable)

            backend._run()

            ready.assert_not_called()
            self.assertIsInstance(
                unavailable.call_args.args[1], PermissionNotSavedError
            )
            session.__exit__.assert_called_once()
            self.assertFalse(backend.is_ready)

    @patch("emote.wayland_paste.select.select", return_value=([], [], []))
    def test_input_is_acknowledged_before_cleanup(self, _select):
        from libei import ei

        sender = Mock()
        ping = sender.new_ping.return_value
        sender.events = [Mock(event_type=ei.EventType.PONG, pong=Mock(id=ping.id))]

        WaylandPaste()._finish_input(sender, ei)

        ping.send.assert_called_once()
        sender.dispatch.assert_called_once()
        ping.release.assert_called_once()

    @patch("emote.wayland_paste.select.select", return_value=([], [], []))
    def test_disconnect_before_acknowledgement_releases_ping_and_reports_stop(
        self, _select
    ):
        from libei import ei

        sender = Mock()
        sender.events = [Mock(event_type=ei.EventType.DISCONNECT)]

        with self.assertRaises(SessionEndedError):
            WaylandPaste()._finish_input(sender, ei)

        sender.new_ping.return_value.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
