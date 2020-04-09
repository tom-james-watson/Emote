import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from emote import emojis, user_data


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
        self.set_default_size(500, 450)
        self.set_keep_above(True)

        self.search_scrolled = None
        self.current_emojis = []

        self.app_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.app_container)

        self.init_header()
        self.init_category_selectors()
        self.init_search()
        self.render_selected_emoji_category()

        self.show_all()
        self.present_with_time(open_time)

        # Delay registering events by 100ms. For some reason FOCUS of Window is
        # momentarily False during window creation.
        GLib.timeout_add(500, self.register_window_state_event_handler)

        self.connect("key-press-event", self.on_key_press_event)

    def init_header(self):
        header = Gtk.HeaderBar(title='Emote')
        header.set_subtitle('Select an emoji to copy it')
        self.set_titlebar(header)

    def init_category_selectors(self):
        hbox = Gtk.Box()

        self.category_selectors = []
        self.selected_emoji_category = 'recent'

        for (category, _, category_image) in emojis.get_category_order():
            category_selector = Gtk.ToggleButton(
                label=category_image,
                name='category_selector_button'
            )
            category_selector.category = category

            if category == self.selected_emoji_category:
                category_selector.set_active(True)

            self.category_selectors.append(category_selector)

            category_selector.connect(
                'toggled',
                self.on_category_selector_toggled
            )

            hbox.pack_start(category_selector, True, False, GRID_SIZE)

        self.app_container.pack_start(hbox, False, False, GRID_SIZE)

    def init_search(self):
        search_box = Gtk.Box()
        self.search_entry = Gtk.SearchEntry()
        search_box.pack_start(self.search_entry, True, True, GRID_SIZE)
        self.search_entry.connect('focus-in-event', self.on_search_focus)
        self.search_entry.connect('changed', self.on_search_changed)
        self.search_entry.connect(
            "key-press-event",
            self.on_search_entry_key_press_event
        )
        self.app_container.add(search_box)

        GLib.idle_add(self.search_entry.grab_focus)

    def register_window_state_event_handler(self):
        self.connect('window-state-event', self.on_window_state_event)

    def on_window_state_event(self, widget, event):
        '''If the window has just unfocussed, exit'''
        if not (event.new_window_state & Gdk.WindowState.FOCUSED):
            self.destroy()

    def on_key_press_event(self, widget, event):
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)
        shift = (state & Gdk.ModifierType.SHIFT_MASK)
        tab = keyval_name == 'Tab' or keyval_name == 'ISO_Left_Tab'

        if ctrl and keyval_name == 'f':
            self.search_entry.grab_focus()
        elif ctrl and shift and tab:
            self.on_cycle_category(True)
        elif ctrl and tab:
            self.on_cycle_category()
        elif keyval_name == 'Escape':
            self.destroy()
        else:
            return False

        return True

    def on_search_entry_key_press_event(self, widget, event):
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)

        if keyval_name == 'Return':
            if len(self.current_emojis) > 0:
                self.on_emoji_selected(self.current_emojis[0]['char'])
        else:
            return False

        return True

    def on_category_selector_toggled(self, toggled_category_selector):
        if not toggled_category_selector.get_active():
            return

        self.selected_emoji_category = toggled_category_selector.category

        for category_selector in self.category_selectors:
            if category_selector.category != self.selected_emoji_category:
                category_selector.set_active(False)

        self.search_entry.set_text('')
        self.render_selected_emoji_category()

    def on_cycle_category(self, backwards=False):
        index = None

        for (i, category_selector) in enumerate(self.category_selectors):
            if category_selector.category == self.selected_emoji_category:
                index = i
                break

        if backwards:
            if index == 0:
                index = -1
            else:
                index -= 1
        else:
            if index == len(self.category_selectors) - 1:
                index = 0
            else:
                index += 1

        toggled_category_selector = self.category_selectors[index]
        toggled_category_selector.set_active(True)

        self.on_category_selector_toggled(toggled_category_selector)

    def on_flowbox_child_activated(self, flow_box, child):
        self.on_emoji_selected(child.emoji)

    def on_search_focus(self, search_entry, event):
        if self.emoji_flowbox:
            self.emoji_flowbox.unselect_all()

    def on_search_changed(self, search_entry):
        query = self.search_entry.props.text

        if query == '':
            if self.search_scrolled:
                self.search_scrolled.destroy()
                self.search_scrolled = None

            # Retoggle the previously selected emoji category
            for category_selector in self.category_selectors:
                if category_selector.category == self.selected_emoji_category:
                    category_selector.set_active(True)

            self.render_selected_emoji_category()

        else:
            self.app_container.remove(self.category_scrolled)
            self.render_emoji_search_results(query)

    def render_emoji_search_results(self, query):
        if self.search_scrolled:
            self.search_scrolled.destroy()

        for category_selector in self.category_selectors:
            category_selector.set_active(False)

        self.search_scrolled = Gtk.ScrolledWindow()
        self.search_scrolled.set_hexpand(False)

        self.search_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=GRID_SIZE
        )
        self.search_box.pack_start(
            self.create_emoji_flowbox(emojis.search(query)),
            True,
            True,
            GRID_SIZE
        )

        self.search_scrolled.add(self.search_box)

        self.app_container.pack_start(self.search_scrolled, True, True, 0)
        self.show_all()

    def render_selected_emoji_category(self):
        if hasattr(self, 'category_scrolled'):
            self.app_container.remove(self.category_scrolled)

        self.category_scrolled = Gtk.ScrolledWindow()
        self.category_scrolled.set_hexpand(False)

        category = self.selected_emoji_category
        category_display_name = None

        for (c, display_name, _) in emojis.get_category_order():
            if c == category:
                category_display_name = display_name
                break

        category_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=GRID_SIZE
        )

        label_box = Gtk.Box()
        label = Gtk.Label()
        label.set_name('category_label')
        label.set_text(category_display_name)
        label.set_justify(Gtk.Justification.LEFT)
        label_box.pack_start(label, False, False, GRID_SIZE)
        category_box.pack_start(Gtk.Box(), False, False, GRID_SIZE / 2)
        category_box.add(label_box)

        category_box.pack_start(
            self.create_emoji_flowbox(
                emojis.get_emojis_by_category()[category],
                category=category
            ),
            True,
            True,
            0
        )

        self.category_scrolled.add(category_box)
        self.app_container.pack_end(self.category_scrolled, True, True, 0)

        self.show_all()

    def create_emoji_flowbox(self, emojis, category=None):
        flowbox = Gtk.FlowBox(
            valign=Gtk.Align.START,
            max_children_per_line=10,
            selection_mode=Gtk.SelectionMode.MULTIPLE,
            homogeneous=True
        )

        self.emoji_flowbox = flowbox
        self.current_emojis = emojis

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
            flowbox.add(flowbox_child)

        return flowbox

    def on_emoji_selected(self, emoji):
        '''Copy the selected emoji to the clipboard'''
        self.hide()

        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(emoji, -1)

        user_data.update_recent_emojis(emoji)
        emojis.update_recent_category()

        self.destroy()
