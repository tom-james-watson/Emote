import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from emote import config


def load_css():
    """
    Load associated CSS for the window.
    """
    css_provider = Gtk.CssProvider()

    if config.is_snap:
        css_provider.load_from_path(f"{config.snap_root}/static/style.css")
    else:
        css_provider.load_from_path("static/style.css")

    screen = Gdk.Screen.get_default()
    styleContext = Gtk.StyleContext()
    styleContext.add_provider_for_screen(
        screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
    )
