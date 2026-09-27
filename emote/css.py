from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from emote import config

category_icons_ready = False


def load_css():
    provider = Gtk.CssProvider()
    provider.load_from_path(f"{config.static_dir}/style.css")
    icon_root = Path(config.static_dir).resolve() / "icons"
    global category_icons_ready
    try:
        sample = icon_root / "hicolor/scalable/actions/emote-category-recent-symbolic.svg"
        GdkPixbuf.Pixbuf.new_from_file(str(sample))
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(str(icon_root))
        category_icons_ready = True
    except GLib.Error:
        category_icons_ready = False
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
