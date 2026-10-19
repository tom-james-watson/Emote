from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from emote import x11_window


class X11WindowTests(TestCase):
    @patch("Xlib.display.Display")
    def test_other_backends_do_not_open_an_x_connection(self, connect):
        surface = Mock()
        x11_window.configure_picker(surface)
        x11_window.center_picker(surface)
        connect.assert_not_called()
        surface.set_skip_taskbar_hint.assert_not_called()

    @patch("emote.x11_window.is_x11_surface", return_value=True)
    @patch("Xlib.display.Display")
    def test_centers_in_pointer_monitor_instead_of_combined_desktop(
        self, connect, _is_x11
    ):
        monitors = [
            SimpleNamespace(x=0, y=0, width=1280, height=800),
            SimpleNamespace(x=1280, y=0, width=1920, height=1080),
        ]
        self.check_position(connect, monitors, (2000, 400), (500, 400), (1990, 340))

    @patch("emote.x11_window.is_x11_surface", return_value=True)
    @patch("Xlib.display.Display")
    def test_negative_monitor_origin_and_scaled_coordinates(self, connect, _is_x11):
        monitors = [
            SimpleNamespace(x=-1280, y=-100, width=1280, height=800),
            SimpleNamespace(x=0, y=0, width=1280, height=800),
        ]
        self.check_position(
            connect, monitors, (-2000, 200), (1000, 800), (-1780, 200), scale=2
        )

    @patch("emote.x11_window.is_x11_surface", return_value=True)
    @patch("Xlib.display.Display")
    def test_oversized_picker_keeps_its_top_left_on_the_monitor(self, connect, _is_x11):
        monitors = [SimpleNamespace(x=1280, y=0, width=800, height=600)]
        self.check_position(connect, monitors, (1500, 100), (1000, 900), (1280, 0))

    def check_position(self, connect, geometries, pointer, size, expected, scale=1):
        connection = connect.return_value
        connection.screen.return_value.root.query_pointer.return_value = (
            SimpleNamespace(root_x=pointer[0], root_y=pointer[1])
        )
        window = connection.create_resource_object.return_value
        window.get_geometry.return_value = SimpleNamespace(
            width=size[0], height=size[1]
        )
        surface = Mock()
        surface.get_scale_factor.return_value = scale
        monitors = surface.get_display.return_value.get_monitors.return_value
        monitors.get_n_items.return_value = len(geometries)
        monitors.get_item.side_effect = lambda index: SimpleNamespace(
            get_geometry=lambda: geometries[index]
        )

        x11_window.center_picker(surface)

        window.configure.assert_called_once_with(x=expected[0], y=expected[1])
        connection.close.assert_called_once_with()
