import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Keybinder', '3.0')
from gi.repository import Gtk, Keybinder
from emote import picker, css


def create_picker():
    picker.EmojiPicker(Keybinder.get_current_event_time())


def main():
    print('Launching emote daemon')

    Gtk.Application(application_id='org.tom-james-watson.EmojiGTK')

    css.load_css()

    # Register global shortcut for invoking the emoji picker
    Keybinder.init()
    Keybinder.bind("<Ctrl><Alt>E", lambda x: create_picker())

    # Run the main gtk event loop - this prevents the app from quitting
    Gtk.main()
