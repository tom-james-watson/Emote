"""Window-manager hints and placement for the X11 picker."""

from contextlib import closing

import gi

try:
    gi.require_version("GdkX11", "4.0")
    from gi.repository import GdkX11
except (ImportError, ValueError):
    GdkX11 = None


def is_x11_surface(surface):
    return GdkX11 is not None and isinstance(surface, GdkX11.X11Surface)


def configure_picker(surface):
    if is_x11_surface(surface):
        surface.set_skip_taskbar_hint(True)


def center_picker(surface):
    if not is_x11_surface(surface):
        return

    from Xlib import display, error

    try:
        # Flush GTK's map/resize requests before using a second X connection.
        surface.get_display().sync()
        with closing(display.Display()) as connection:
            pointer = connection.screen().root.query_pointer()
            monitors = surface.get_display().get_monitors()
            scale = surface.get_scale_factor()
            for index in range(monitors.get_n_items()):
                geometry = monitors.get_item(index).get_geometry()
                x, y = geometry.x * scale, geometry.y * scale
                width, height = geometry.width * scale, geometry.height * scale
                if not (
                    x <= pointer.root_x < x + width and y <= pointer.root_y < y + height
                ):
                    continue
                window = connection.create_resource_object("window", surface.get_xid())
                size = window.get_geometry()
                window.configure(
                    x=x + max(0, (width - size.width) // 2),
                    y=y + max(0, (height - size.height) // 2),
                )
                connection.sync()
                break
    except (error.XError, error.DisplayError, OSError) as exc:
        print("Could not position X11 picker:", exc)
