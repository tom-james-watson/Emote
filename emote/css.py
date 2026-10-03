from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from emote import config

GRID_METRICS_CSS = """
listview.emoji-list > row {
  padding: 0;
}

.emoji-cell {
  min-width: 0;
  padding: 4px 0 0;
  margin: 0;
}
"""


def load_css():
    provider = Gtk.CssProvider()
    provider.load_from_path(f"{config.static_dir}/style.css")
    icon_root = Path(config.static_dir).resolve() / "icons"
    icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
    icon_theme.add_search_path(str(icon_root))
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    grid_provider = Gtk.CssProvider()
    grid_provider.load_from_string(GRID_METRICS_CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        grid_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_USER + 1,
    )
