import sys
import os
import subprocess
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Keybinder', '3.0')
from gi.repository import Gtk, Keybinder
from emote import picker


def create_picker_process():
    '''
    Create picker process.

    $SNAP is only set when the app is bundled and running as a snap.
    '''
    if os.environ.get("SNAP"):
        subprocess.Popen(['emote', 'picker'])
    else:
        subprocess.Popen(['pipenv', 'run', 'start', 'picker'])


def main():
    '''
    If the app is launched with the 'picker' arg, we spawn a new process that
    launches the emoji picker window.

    Otherwise, we create a long lived daemon that simply listens for the picker
    shortcut. When the shortcut is pressed, spawn a new instance of emote with
    the picker arg present.

    The reason we do this instead of having a single process that spanws a new
    window when the shortcut is pressed, is because the second time an
    application launches a window, the window manager (at least Gnome) does not
    refocus the application. This means the picker is spawned behind other
    windows. Creating a new instance avoids this issue.
    '''

    if len(sys.argv) > 1 and sys.argv[1] == 'picker':
        print('Creating picker window')
        picker.create()
    else:
        print('Launching emote daemon')
        Gtk.Application(application_id='org.tom-james-watson.EmojiGTK')

        # Register global shortcut for invoking the emoji picker
        Keybinder.init()
        Keybinder.bind("<Ctrl><Alt>E", lambda x: create_picker_process())

    # Run the main gtk event loop - this prevents the app from quitting
    Gtk.main()
