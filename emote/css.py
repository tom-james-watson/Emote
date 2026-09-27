import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from emote import config


def load_css():
    provider = Gtk.CssProvider()
    provider.load_from_path(f"{config.static_dir}/style.css")
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
