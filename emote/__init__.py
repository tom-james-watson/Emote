import sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Keybinder', '3.0')
from gi.repository import Gtk, Keybinder
from emote import picker, css, emojis


class EmoteApplication(Gtk.Application):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id='com.tomjwatson.Emote',
                         **kwargs)

        self.activated = False

    def start_daemon(self):
        # Register global shortcut for invoking the emoji picker
        Keybinder.init()
        Keybinder.bind("<Ctrl><Alt>E", lambda x: self.create_picker_window())

        css.load_css()
        emojis.init()

        self.activated = True

        # Run the main gtk event loop - this prevents the app from quitting
        Gtk.main()

    def create_picker_window(self):
        picker.EmojiPicker(Keybinder.get_current_event_time())

    def do_activate(self):
        if not self.activated:
            print('Launching emote daemon')
            self.start_daemon()
        else:
            print('Second instance launched')
            self.create_picker_window()


def main():
    app = EmoteApplication()
    app.run(sys.argv)
