from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from Xlib import X

from emote.x11_hotkey import X11Hotkey


class X11HotkeyTests(TestCase):
    @patch("emote.x11_hotkey.GLib.idle_add")
    def test_shortcut_preserves_keypress_time_for_focus(self, idle_add):
        callback = Mock()
        hotkey = X11Hotkey(callback)
        connection = Mock()
        connection.pending_events.side_effect = [1, 0]
        connection.next_event.return_value = SimpleNamespace(
            type=X.KeyPress, time=12345
        )
        stop = Mock()
        stop.wait.side_effect = [False, True]

        hotkey._listen(connection, Mock(), 26, X.ControlMask, (0,), stop)

        idle_add.assert_called_once_with(callback, "_TIME12345")
