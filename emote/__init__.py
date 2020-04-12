import sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Keybinder', '3.0')
from gi.repository import Gtk, Keybinder
from emote import picker, css, emojis, user_data


class EmoteApplication(Gtk.Application):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id='com.tomjwatson.Emote',
                         **kwargs)

        self.activated = False
        self.picker_window = None

    def start_daemon(self):
        Keybinder.init()
        self.set_accelerator()

        css.load_css()
        emojis.init()

        self.activated = True

        # Run the main gtk event loop - this prevents the app from quitting
        Gtk.main()

    def set_accelerator(self):
        '''Register global shortcut for invoking the emoji picker'''
        accel_string, _ = user_data.load_accelerator()

        if accel_string:
            Keybinder.bind(accel_string, lambda x: self.create_picker_window())

    def unset_accelerator(self):
        old_accel_string, _ = user_data.load_accelerator()

        if old_accel_string:
            Keybinder.unbind(old_accel_string)

    def update_accelerator(self, accel_string, accel_label):
        print(f'Updating global shortcut to {accel_label}')
        self.unset_accelerator()
        user_data.update_accelerator(accel_string, accel_label)
        self.set_accelerator()

    def create_picker_window(self):
        if self.picker_window:
            self.picker_window.destroy()
        self.picker_window = picker.EmojiPicker(
            Keybinder.get_current_event_time(),
            self.update_accelerator
        )

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
