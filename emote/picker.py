import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from emote import emojis


GRID_SIZE = 10


class EmojiPicker(Gtk.Window):

    def __init__(self, open_time):
        Gtk.Window.__init__(
            self,
            title='Emote',
            window_position=Gtk.WindowPosition.CENTER,
            resizable=False,
            deletable=False
        )
        self.set_default_size(350, 450)

        header = Gtk.HeaderBar(title='Emote')
        header.set_subtitle('Select an emoji to copy it')
        self.set_titlebar(header)

        self.app_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        search_box = Gtk.Box()
        search = Gtk.SearchEntry()
        search_box.pack_start(search, True, True, GRID_SIZE)
        search.connect('focus-in-event', self.on_search_focus)
        search.connect('changed', self.on_search_changed)
        self.app_container.pack_start(search_box, False, False, GRID_SIZE)

        self.spinner = Gtk.Spinner()
        self.spinner.start()
        self.app_container.pack_start(self.spinner, False, False, GRID_SIZE)

        self.add(self.app_container)

        self.search_scrolled = None
        self.search_flowbox = None

        self.set_keep_above(True)
        self.present_with_time(open_time)

        self.show_all()

        # Delay registering events by 100ms. For some reason FOCUS of Window is
        # momentarily False during window creation.
        GLib.timeout_add(500, self.register_window_state_event_handler)

        # Release the main loop before creating the emoji list
        GLib.idle_add(self.create_emoji_list)

        GLib.idle_add(search.grab_focus)

    def register_window_state_event_handler(self):
        self.connect('window-state-event', self.on_window_state_event)

    def on_window_state_event(self, widget, event):
        '''If the window has just unfocussed, exit'''
        if not (event.new_window_state & Gdk.WindowState.FOCUSED):
            self.destroy()

    def on_flowbox_child_activated(self, flow_box, child):
        self.on_emoji_selected(child.emoji)

    def on_emoji_focus(self, flowbox_child, event):
        focused_flowbox = flowbox_child.parent

        for flowbox in self.flowboxes:
            if (
                hasattr(flowbox, 'category') and
                hasattr(focused_flowbox, 'category') and
                flowbox.category != focused_flowbox.category
            ):
                flowbox.unselect_all()

    def on_search_focus(self, search_entry, event):
        for flowbox in self.flowboxes:
            flowbox.unselect_all()

        if self.search_flowbox:
            self.search_flowbox.unselect_all()

    def on_search_changed(self, search_entry):
        query = search_entry.props.text

        if query == '':
            self.search_flowbox = None
            if self.search_scrolled:
                self.search_scrolled.destroy()
                self.search_scrolled = None
            self.app_container.pack_end(self.scrolled, True, True, 0)
            return

        self.app_container.remove(self.scrolled)

        if self.search_scrolled:
            self.search_scrolled.destroy()

        self.search_scrolled = Gtk.ScrolledWindow()
        self.search_scrolled.set_hexpand(False)

        self.search_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=GRID_SIZE
        )
        self.search_flowbox = self.create_emoji_flowbox(emojis.search(query))
        self.search_box.pack_start(self.search_flowbox, True, True, 0)
        self.search_scrolled.add(self.search_box)
        self.app_container.pack_start(self.search_scrolled, True, True, 0)
        self.show_all()

    def create_emoji_list(self):
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_hexpand(False)

        self.categories_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=GRID_SIZE
        )

        emoji_categories = emojis.get_emojis_by_category()

        self.flowboxes = []

        for (category, category_display_name) in emojis.get_category_order():
            category_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=GRID_SIZE
            )
            self.categories_box.add(category_box)

            label_box = Gtk.Box()
            label = Gtk.Label()
            label.set_text(category_display_name)
            label.set_justify(Gtk.Justification.LEFT)
            label_box.pack_start(label, False, False, GRID_SIZE)
            category_box.add(label_box)

            category_box.add(
                self.create_emoji_flowbox(
                    emoji_categories[category],
                    category=category
                )
            )

        self.scrolled.add(self.categories_box)
        self.app_container.remove(self.spinner)
        self.app_container.pack_end(self.scrolled, True, True, 0)

        self.show_all()

    def create_emoji_flowbox(self, emojis, category=None):
        flowbox = Gtk.FlowBox(
            valign=Gtk.Align.START,
            # min_children_per_line=8,
            max_children_per_line=10,
            selection_mode=Gtk.SelectionMode.MULTIPLE,
            homogeneous=True
        )

        if category:
            flowbox.category = category

        self.flowboxes.append(flowbox)
        flowbox.connect('child_activated', self.on_flowbox_child_activated)

        for emoji in emojis:
            btn = Gtk.Button(
                label=emoji['char'],
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
            flowbox_child.emoji = emoji['char']
            flowbox_child.connect('focus-in-event', self.on_emoji_focus)
            flowbox.add(flowbox_child)

        return flowbox

    def on_emoji_selected(self, emoji):
        '''Copy the selected emoji to the clipboard'''
        self.hide()

        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(emoji, -1)

        self.destroy()
