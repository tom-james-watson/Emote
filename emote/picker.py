import os
import time
from datetime import datetime
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Gio
from gi.repository.GdkPixbuf import Pixbuf
from emote import emojis, user_data, settings, guide, config


GRID_SIZE = 10


class EmojiPicker(Gtk.Window):
    def __init__(self, open_time, update_accelerator, show_welcome):
        Gtk.Window.__init__(
            self,
            title="Emote",
            window_position=Gtk.WindowPosition.CENTER,
            resizable=False,
            deletable=False,
        )
        self.set_default_size(500, 450)
        self.set_keep_above(True)
        self.dialog_open = False
        self.update_accelerator = update_accelerator
        self.search_scrolled = None
        self.emoji_append_list = []
        self.current_emojis = []

        self.app_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.app_container)

        self.init_header()
        self.init_search()
        self.init_category_selectors()
        self.render_selected_emoji_category()

        self.show_all()
        self.present_with_time(open_time)

        self.check_welcome(show_welcome)

        # Delay registering events by 100ms. For some reason FOCUS of Window is
        # momentarily False during window creation.
        GLib.timeout_add(500, self.register_window_state_event_handler)

        self.connect("key-press-event", self.on_key_press_event)

    def init_header(self):
        header = Gtk.HeaderBar(title="Emote")

        self.menu_popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        items_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        if not config.is_wayland:
            prefs_btn = Gtk.ModelButton("Preferences")
            prefs_btn.set_alignment(0, 0.5)
            prefs_btn.connect("clicked", lambda prefs_btn: self.open_preferences())
            items_box.pack_start(prefs_btn, False, True, 0)

        guide_btn = Gtk.ModelButton("Guide")
        guide_btn.set_alignment(0, 0.5)
        guide_btn.connect("clicked", lambda guide_btn: self.open_guide())
        items_box.pack_start(guide_btn, False, True, 0)

        about_btn = Gtk.ModelButton("About")
        about_btn.set_alignment(0, 0.5)
        about_btn.connect("clicked", lambda about_btn: self.open_about())
        items_box.pack_start(about_btn, False, True, 0)

        vbox.pack_start(items_box, False, False, GRID_SIZE)
        hbox.pack_start(vbox, False, False, GRID_SIZE)
        hbox.show_all()
        self.menu_popover.add(hbox)
        self.menu_popover.set_position(Gtk.PositionType.BOTTOM)

        menu_button = Gtk.MenuButton()
        menu_button.set_popover(self.menu_popover)
        icon = Gio.ThemedIcon(name="open-menu-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        menu_button.show()
        menu_button.add(image)
        header.pack_start(menu_button)

        self.set_titlebar(header)

    def init_category_selectors(self):
        hbox = Gtk.Box(margin_bottom=GRID_SIZE)

        self.category_selectors = []
        self.selected_emoji_category = "recent"

        for (category, _, category_image) in emojis.get_category_order():
            category_selector = Gtk.ToggleButton(
                label=category_image, name="category_selector_button"
            )
            category_selector.category = category

            if category == self.selected_emoji_category:
                category_selector.set_active(True)

            self.category_selectors.append(category_selector)

            category_selector.connect("toggled", self.on_category_selector_toggled)

            hbox.pack_start(category_selector, True, False, GRID_SIZE)

        self.app_container.add(hbox)

    def init_search(self):
        search_box = Gtk.Box()
        self.search_entry = Gtk.SearchEntry()
        search_box.pack_start(self.search_entry, True, True, GRID_SIZE)
        self.search_entry.connect("focus-in-event", self.on_search_focus)
        self.search_entry.connect("changed", self.on_search_changed)
        self.search_entry.connect(
            "key-press-event", self.on_search_entry_key_press_event
        )
        self.app_container.pack_start(search_box, False, False, GRID_SIZE)

        GLib.idle_add(self.search_entry.grab_focus)

    def add_emoji_append_list_preview(self):
        preview_box = Gtk.Box(spacing=GRID_SIZE, margin=GRID_SIZE, margin_bottom=0)

        label = Gtk.Label()
        label.set_name("emoji_append_list_preview_label")
        label.set_text("Selected Emoji:")
        label.set_alignment(0, 0.2)
        preview_box.pack_start(label, False, True, 0)

        self.emoji_append_list_preview = Gtk.Entry()
        self.emoji_append_list_preview.set_name("emoji_append_list_preview")
        self.emoji_append_list_preview.set_alignment(0)
        self.emoji_append_list_preview.set_sensitive(False)
        preview_box.pack_start(self.emoji_append_list_preview, True, True, 0)
        preview_box.show_all()

        self.app_container.pack_start(preview_box, False, False, 0)

    def update_emoji_append_list_preview(self):
        self.emoji_append_list_preview.set_text("".join(self.emoji_append_list))

    def check_welcome(self, show_welcome):
        """Show the guide the first time we run the app"""
        if show_welcome:
            self.open_guide()

    def register_window_state_event_handler(self):
        self.connect("window-state-event", self.on_window_state_event)

    def on_window_state_event(self, widget, event):
        """If the window has just unfocussed, exit"""
        if self.dialog_open:
            return

        if not (event.new_window_state & Gdk.WindowState.FOCUSED):
            self.destroy()

    def on_key_press_event(self, widget, event):
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        state = event.state
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        tab = keyval_name == "Tab" or keyval_name == "ISO_Left_Tab"

        if ctrl and keyval_name == "f":
            self.search_entry.grab_focus()
        elif ctrl and shift and tab:
            self.on_cycle_category(True)
        elif ctrl and tab:
            self.on_cycle_category()
        elif keyval_name == "Escape":
            self.destroy()
        else:
            return False

        return True

    def open_preferences(self):
        self.dialog_open = True
        settings_window = settings.Settings(self.update_accelerator)
        settings_window.connect("destroy", self.on_close_dialog)

    def open_guide(self):
        self.dialog_open = True
        guide_window = guide.Guide()
        guide_window.connect("destroy", self.on_close_dialog)

    def open_about(self):
        logo_path = (
            f"{config.snap_root}/static/logo.svg"
            if config.is_snap
            else "static/logo.svg"
        )
        logo = Pixbuf.new_from_file(logo_path)

        about_dialog = Gtk.AboutDialog(
            transient_for=self,
            modal=True,
            logo=logo,
            program_name="Emote",
            title="About Emote",
            version=os.environ.get("SNAP_VERSION", "dev build"),
            authors=["Tom Watson"],
            artists=["Twitter, Inc and other contributors (App Icon)"],
            documenters=["Irene Auñón"],
            copyright=f"© Tom Watson {datetime.now().year}",
            website_label="Source Code",
            website="https://github.com/tom-james-watson/emote",
            comments="Modern popup emoji picker",
            license_type=Gtk.License.GPL_3_0,
        )

        self.dialog_open = True
        about_dialog.present()
        about_dialog.connect("destroy", self.on_close_dialog)

    def on_close_dialog(self, dialog):
        self.dialog_open = False

    def on_search_entry_key_press_event(self, widget, event):
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)

        if shift and keyval_name == "Return":
            if len(self.current_emojis) > 0:
                self.on_emoji_append(self.current_emojis[0]["char"])
        elif keyval_name == "Return":
            if len(self.current_emojis) > 0:
                self.on_emoji_select(self.current_emojis[0]["char"])
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

        self.search_entry.set_text("")
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
        toggled_category_selector.grab_focus()

        self.on_category_selector_toggled(toggled_category_selector)

    def on_flowbox_event(self, flow_box, event):
        if event.type != Gdk.EventType.KEY_PRESS:
            return

        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)

        emoji = flow_box.get_selected_children()[0].emoji

        if shift and keyval_name == "Return":
            self.on_emoji_append(emoji)
        elif keyval_name == "Return":
            self.on_emoji_select(emoji)

    def on_search_focus(self, search_entry, event):
        if self.emoji_flowbox:
            self.emoji_flowbox.unselect_all()

    def on_search_changed(self, search_entry):
        query = self.search_entry.props.text

        if query == "":
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
            orientation=Gtk.Orientation.VERTICAL, spacing=GRID_SIZE
        )
        self.search_box.pack_start(
            self.create_emoji_flowbox(emojis.search(query)), True, True, GRID_SIZE
        )

        self.search_scrolled.add(self.search_box)

        self.app_container.pack_start(self.search_scrolled, True, True, 0)
        self.app_container.reorder_child(self.search_scrolled, 2)
        self.show_all()

    def render_selected_emoji_category(self):
        if hasattr(self, "category_scrolled"):
            self.app_container.remove(self.category_scrolled)

        self.category_scrolled = Gtk.ScrolledWindow()
        self.category_scrolled.set_hexpand(False)

        category = self.selected_emoji_category
        category_display_name = None

        for (c, display_name, _) in emojis.get_category_order():
            if c == category:
                category_display_name = display_name
                break

        category_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        label_box = Gtk.Box()
        label = Gtk.Label(margin_right=GRID_SIZE, margin_left=GRID_SIZE)
        label.set_name("category_label")
        label.set_text(category_display_name)
        label.set_justify(Gtk.Justification.LEFT)
        label_box.pack_start(label, False, False, 0)
        category_box.pack_start(Gtk.Box(), False, False, 0)
        category_box.add(label_box)

        category_box.pack_start(
            self.create_emoji_flowbox(
                emojis.get_emojis_by_category()[category], category=category
            ),
            True,
            True,
            0,
        )

        self.category_scrolled.add(category_box)
        self.app_container.pack_start(self.category_scrolled, True, True, 0)
        self.app_container.reorder_child(self.category_scrolled, 2)

        self.show_all()

    def create_emoji_flowbox(self, emojis, category=None):
        flowbox = Gtk.FlowBox(
            valign=Gtk.Align.START,
            max_children_per_line=9,
            min_children_per_line=9,
            selection_mode=Gtk.SelectionMode.SINGLE,
            homogeneous=True,
        )

        self.emoji_flowbox = flowbox
        self.current_emojis = emojis

        flowbox.connect("event", self.on_flowbox_event)

        for emoji in emojis:
            btn = Gtk.Button(
                label=emoji["char"],
                name="emoji_button",
                can_focus=False,
                relief=Gtk.ReliefStyle.NONE,
            )
            btn.set_tooltip_text(emoji["name"])
            btn.connect("event", self.on_emoji_btn_event)
            flowbox_child = Gtk.FlowBoxChild()
            flowbox_child.add(btn)
            flowbox_child.parent = flowbox
            flowbox_child.emoji = emoji["char"]
            flowbox.add(flowbox_child)

        return flowbox

    def on_emoji_btn_event(self, btn, event):
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return

        if event.button.button == 1:
            # Left mouse clicked
            state = event.state
            shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

            if shift:
                self.on_emoji_append(btn.get_label())
            else:
                self.on_emoji_select(btn.get_label())

        if event.button.button == 3:
            # Right mouse clicked
            self.on_emoji_append(btn.get_label())

    def on_emoji_append(self, emoji):
        """Append the selected emoji to the clipboard"""
        print(f"Appending {emoji} to selection")
        self.emoji_append_list.append(emoji)

        if len(self.emoji_append_list) == 1:
            self.add_emoji_append_list_preview()

        self.update_emoji_append_list_preview()

        self.copy_to_clipboard("".join(self.emoji_append_list))
        self.add_emoji_to_recent(emoji)

    def on_emoji_select(self, emoji):
        """
        Copy the selected emoji to the clipboard, close the picker window and
        make the user's system perform a paste after 150ms, pasting the emoji
        to the currently focussed application window.

        If we have been appending other emojis first, add this final one first.
        """
        self.hide()

        if len(self.emoji_append_list) > 0:
            self.on_emoji_append(emoji)
        else:
            print(f"Selecting {emoji}")
            self.add_emoji_to_recent(emoji)
            self.copy_to_clipboard(emoji)

        self.destroy()

        time.sleep(0.15)

        if config.is_wayland:
            ydotool_path = (
                f"{config.snap_root}/static/ydotool"
                if config.is_snap
                else "static/ydotool"
            )
            os.system(f"{ydotool_path} key ctrl+v")
        else:
            os.system("xdotool key ctrl+v")

    def add_emoji_to_recent(self, emoji):
        user_data.update_recent_emojis(emoji)
        emojis.update_recent_category()

    def copy_to_clipboard(self, content):
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(content, -1)
