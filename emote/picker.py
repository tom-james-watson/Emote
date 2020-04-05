import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from emote import emojis


GRID_SIZE = 10
EMOJI_COLUMNS = 9


class EmojiPicker(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(
            self,
            title='Emote',
            window_position=Gtk.WindowPosition.CENTER,
        )
        self.set_default_size(450, 400)
        self.set_resizable(False)
        self.set_deletable(False)

        header = Gtk.HeaderBar(title='Emote')
        header.set_subtitle('Select an emoji to copy it')
        self.set_titlebar(header)

        self.app_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        search_box = Gtk.Box()
        search = Gtk.SearchEntry()
        search_box.pack_start(search, True, True, GRID_SIZE)
        self.app_container.pack_start(search_box, False, False, GRID_SIZE)

        self.spinner = Gtk.Spinner()
        self.spinner.start()
        self.app_container.pack_start(self.spinner, False, False, GRID_SIZE)

        self.add(self.app_container)

        self.show_all()

        # Delay registering events by 100ms. For some reason FOCUS of Window is
        # momentarily False during window creation.
        GLib.timeout_add(100, self.register_window_state_event_handler)

        # Release the main loop before creating the emoji list
        GLib.idle_add(self.create_emoji_list)

    def register_window_state_event_handler(self):
        self.connect('window-state-event', self.handle_window_state_event)

    def handle_window_state_event(self, widget, event):
        '''If the window has just unfocussed, exit'''
        if not (event.new_window_state & Gdk.WindowState.FOCUSED):
            Gtk.main_quit()

    def create_emoji_list(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(False)

        emoji_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=GRID_SIZE
        )

        emoji_categories = emojis.get_emojis_by_category()

        for category in emojis.get_category_order():
            category_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=GRID_SIZE
            )
            emoji_box.pack_start(category_box, True, True, 0)

            label_box = Gtk.Box()
            label = Gtk.Label()
            label.set_text(category)
            label.set_justify(Gtk.Justification.LEFT)
            label_box.pack_start(label, False, False, GRID_SIZE)
            category_box.add(label_box)

            count = 0
            category_emoji_box = None

            for emoji in emoji_categories[category]:
                if count % EMOJI_COLUMNS == 0:
                    category_emoji_box = Gtk.Box(spacing=GRID_SIZE)
                    category_emoji_box.props.halign = Gtk.Align.CENTER
                    category_box.pack_start(category_emoji_box, True, True, 0)
                # print(
                #     emoji.char,
                #     len(emoji.char),
                #     emoji.is_doublebyte,
                #     emoji.short_name,
                #     emoji.chars,
                #     emoji.added_in
                # )
                btn = Gtk.Button(label=emoji.char)
                btn.set_name('emoji_button')
                btn.connect('clicked', self.on_emoji_selected)
                category_emoji_box.add(btn)
                count += 1

        scrolled.add(emoji_box)
        self.app_container.remove(self.spinner)
        self.app_container.pack_end(scrolled, True, True, 0)

        self.show_all()

    def on_emoji_selected(self, widget):
        '''Copy the selected emoji to the clipboard'''
        emoji = widget.get_label()

        self.hide()

        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(emoji, -1)

        self.destroy()


def load_css():
    '''
    Load associated CSS for the window.

    $SNAP is only set when the app is bundled and running as a snap.
    '''
    css_provider = Gtk.CssProvider()

    snap = os.environ.get("SNAP")

    if snap:
        css_provider.load_from_path(f'{snap}/static/style.css')
    else:
        css_provider.load_from_path('static/style.css')

    screen = Gdk.Screen.get_default()
    styleContext = Gtk.StyleContext()
    styleContext.add_provider_for_screen(
        screen,
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_USER
    )


def create():
    load_css()
    EmojiPicker()
