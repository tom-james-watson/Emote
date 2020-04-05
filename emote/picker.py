import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from emote import emojis


GRID_SIZE = 10


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
        search.connect('focus-in-event', self.on_search_focus)
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
        self.connect('window-state-event', self.on_window_state_event)

    def on_window_state_event(self, widget, event):
        '''If the window has just unfocussed, exit'''
        if not (event.new_window_state & Gdk.WindowState.FOCUSED):
            Gtk.main_quit()

    def on_flowbox_child_activated(self, flow_box, child):
        self.on_emoji_selected(child.emoji)

    def on_emoji_focus(self, flowbox_child, event):
        focused_flowbox = flowbox_child.parent

        for flowbox in self.flowboxes:
            if flowbox.category != focused_flowbox.category:
                flowbox.unselect_all()

    def on_search_focus(self, search_entry, event):
        for flowbox in self.flowboxes:
            flowbox.unselect_all()

    def create_emoji_list(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(False)

        emoji_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=GRID_SIZE
        )

        emoji_categories = emojis.get_emojis_by_category()

        self.flowboxes = []

        for category in emojis.get_category_order():
            category_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=GRID_SIZE
            )
            emoji_box.add(category_box)

            label_box = Gtk.Box()
            label = Gtk.Label()
            label.set_text(category)
            label.set_justify(Gtk.Justification.LEFT)
            label_box.pack_start(label, False, False, GRID_SIZE)
            category_box.add(label_box)

            flowbox = Gtk.FlowBox(
                valign=Gtk.Align.START,
                min_children_per_line=8,
                max_children_per_line=50,
                selection_mode=Gtk.SelectionMode.MULTIPLE
            )
            flowbox.category = category
            self.flowboxes.append(flowbox)
            flowbox.connect('child_activated', self.on_flowbox_child_activated)

            for emoji in emoji_categories[category]:
                btn = Gtk.Button(
                    label=emoji.char,
                    name='emoji_button',
                    can_focus=False,
                    relief=Gtk.ReliefStyle.NONE
                )
                btn.connect(
                    'clicked',
                    lambda widget: self.on_emoji_selected(widget.get_label())
                )
                flowbox_child = Gtk.FlowBoxChild()
                flowbox_child.add(btn)
                flowbox_child.parent = flowbox
                flowbox_child.emoji = emoji.char
                flowbox_child.connect('focus-in-event', self.on_emoji_focus)
                flowbox.add(flowbox_child)

            category_box.add(flowbox)

        scrolled.add(emoji_box)
        self.app_container.remove(self.spinner)
        self.app_container.pack_end(scrolled, True, True, 0)

        self.show_all()

    def on_emoji_selected(self, emoji):
        '''Copy the selected emoji to the clipboard'''
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
