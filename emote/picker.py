import os
import time
from datetime import datetime
import gi
from itertools import zip_longest

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Gio, Pango
from gi.repository.GdkPixbuf import Pixbuf
from emote import emojis, user_data, settings, keyboard_shortcuts, guide, config


GRID_SIZE = 10
EMOJIS_PER_ROW = 10


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


class EmojiPicker(Gtk.Window):
    def __init__(self, open_time, update_accelerator, update_theme, show_welcome):
        Gtk.Window.__init__(
            self,
            title="Emote",
            window_position=Gtk.WindowPosition.CENTER,
            resizable=False,
            deletable=False,
            name="emote_window",
        )
        self.set_default_size(500, 450)
        self.set_keep_above(True)
        self.dialog_open = False
        self.update_accelerator = update_accelerator
        self.update_theme = update_theme
        self.search_scrolled = None
        self.emoji_append_list = []
        self.current_emojis = []
        self.first_emoji_widget = None
        self.target_emoji = None

        self.app_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.app_container)

        self.init_header()
        self.init_category_selectors()
        self.init_action_bar()
        self.render_selected_emoji_category()

        self.show_all()
        self.present_with_time(open_time)

        self.check_welcome(show_welcome)

        # Delay registering events by 100ms. For some reason FOCUS of Window is
        # momentarily False during window creation.
        GLib.timeout_add(500, self.register_window_state_event_handler)

        self.connect("key-press-event", self.on_key_press_event)

    def init_header(self):
        header = Gtk.HeaderBar(name="header")

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("focus-in-event", self.on_search_focused)
        self.search_entry.connect("changed", self.on_search_changed)
        self.search_entry.connect(
            "key-press-event", self.on_search_entry_key_press_event
        )
        header.set_custom_title(self.search_entry)

        GLib.idle_add(self.search_entry.grab_focus)

        self.menu_popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        items_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        if config.is_snap or config.is_dev:
            prefs_btn = Gtk.ModelButton("Preferences")
            prefs_btn.set_alignment(0, 0.5)
            prefs_btn.connect("clicked", lambda prefs_btn: self.open_preferences())
            items_box.pack_start(prefs_btn, False, True, 0)

        keyboard_shortcuts_btn = Gtk.ModelButton("Keyboard Shortcuts")
        keyboard_shortcuts_btn.set_alignment(0, 0.5)
        keyboard_shortcuts_btn.connect(
            "clicked", lambda keyboard_shortcuts_btn: self.open_keyboard_shortcuts()
        )
        items_box.pack_start(keyboard_shortcuts_btn, False, True, 0)

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

        menu_button = Gtk.MenuButton(name="menu_button")
        menu_button.set_popover(self.menu_popover)
        icon = Gio.ThemedIcon(name="open-menu-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        menu_button.show()
        menu_button.add(image)
        header.pack_end(menu_button)

        self.set_titlebar(header)

    def init_category_selectors(self):
        self.categories_box = Gtk.Box(margin_bottom=GRID_SIZE, margin_top=GRID_SIZE)

        self.category_selectors = []
        self.selected_emoji_category = "recent"

        for (category, _, category_image) in emojis.get_category_order():
            category_selector = Gtk.ToggleButton(
                label=category_image, name="category_selector_button"
            )
            category_selector.set_tooltip_text(self.get_category_display_name(category))
            category_selector.category = category

            if category == self.selected_emoji_category:
                category_selector.set_active(True)

            self.category_selectors.append(category_selector)

            category_selector.connect("toggled", self.on_category_selector_toggled)

            self.categories_box.pack_start(category_selector, True, False, GRID_SIZE)

        self.app_container.add(self.categories_box)

    def init_action_bar(self):
        self.action_bar = Gtk.ActionBar()

        self.emoji_preview_box = Gtk.Box(
            spacing=GRID_SIZE, margin=GRID_SIZE, orientation=Gtk.Orientation.HORIZONTAL
        )

        self.previewed_emoji_label = Gtk.Label(" ")
        self.previewed_emoji_label.set_name("previewed_emoji_label")
        self.previewed_emoji_label.set_alignment(0, 0.2)
        self.emoji_preview_box.pack_start(self.previewed_emoji_label, False, False, 0)

        self.emoji_preview_box_text = Gtk.Box(
            spacing=0, orientation=Gtk.Orientation.VERTICAL
        )
        self.previewed_emoji_name_label = Gtk.Label(
            " ", ellipsize=Pango.EllipsizeMode.END
        )
        self.previewed_emoji_name_label.set_name("previewed_emoji_name_label")
        self.previewed_emoji_name_label.set_alignment(0, 0.2)
        self.emoji_preview_box_text.pack_start(
            self.previewed_emoji_name_label, False, False, 0
        )

        self.previewed_emoji_shortcode_label = Gtk.Label(
            " ", ellipsize=Pango.EllipsizeMode.END
        )
        self.previewed_emoji_shortcode_label.set_name("previewed_emoji_shortcode_label")
        self.previewed_emoji_shortcode_label.set_alignment(0, 0.2)
        self.emoji_preview_box_text.pack_start(
            self.previewed_emoji_shortcode_label, False, False, 0
        )

        self.emoji_preview_box.pack_start(self.emoji_preview_box_text, False, False, 0)

        self.action_bar.pack_start(self.emoji_preview_box)

        self.selected_box = Gtk.Box(
            spacing=GRID_SIZE, margin=GRID_SIZE, margin_bottom=0, expand=False
        )

        self.emoji_append_list_preview = Gtk.Label(
            " ", max_width_chars=25, ellipsize=Pango.EllipsizeMode.START
        )
        self.emoji_append_list_preview.set_name("emoji_append_list_preview")
        self.selected_box.pack_start(self.emoji_append_list_preview, False, False, 0)

        self.action_bar.pack_end(self.selected_box)

        self.action_bar.show_all()
        self.selected_box.hide()

        self.app_container.pack_end(self.action_bar, False, False, 0)

    def show_emoji_preview(self, char):
        emoji = emojis.get_emoji_by_char(char)
        self.previewed_emoji_label.set_text(emoji["char"])
        self.previewed_emoji_shortcode_label.set_text(f':{emoji["name"]}:')
        self.previewed_emoji_name_label.set_text(
            " ".join([part.capitalize() for part in emoji["name"].split("_")])
        )

    def reset_emoji_preview(self):
        if len(self.current_emojis) > 0:
            self.show_emoji_preview(self.target_emoji)
        else:
            self.previewed_emoji_label.set_text(" ")
            self.previewed_emoji_name_label.set_text(" ")
            self.previewed_emoji_shortcode_label.set_text(" ")

    def update_emoji_append_list_preview(self):
        self.emoji_append_list_preview.show_all()
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

        if config.is_debug:
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
        settings_window = settings.Settings(self.update_theme)
        settings_window.connect("destroy", self.on_close_dialog)

    def open_keyboard_shortcuts(self):
        self.dialog_open = True
        keyboard_shortcuts_window = keyboard_shortcuts.KeyboardShortcuts(
            self.update_accelerator
        )
        keyboard_shortcuts_window.connect("destroy", self.on_close_dialog)

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
            artists=["Tom Watson, Matthew Wong"],
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
        elif keyval_name == "Down" and self.first_emoji_widget:
            self.first_emoji_widget.grab_focus()
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

    def on_search_focused(self, search_entry, event):
        if len(self.current_emojis) > 0:
            self.target_emoji = self.current_emojis[0]["char"]
        self.reset_emoji_preview()

    def on_search_changed(self, search_entry):
        query = self.search_entry.props.text

        if query == "":
            if self.search_scrolled:
                self.search_scrolled.destroy()
                self.search_scrolled = None

            self.categories_box.show()

            self.render_selected_emoji_category()

        else:
            self.app_container.remove(self.category_scrolled)
            self.render_emoji_search_results(query)

    def render_emoji_search_results(self, query):
        if self.search_scrolled:
            self.search_scrolled.destroy()

        self.search_scrolled = Gtk.ScrolledWindow()
        self.search_scrolled.set_hexpand(False)

        search_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=GRID_SIZE,
            margin_top=GRID_SIZE,
        )
        search_box.pack_start(
            self.create_emoji_results(emojis.search(query)), False, False, 0
        )

        self.search_scrolled.add(search_box)
        self.app_container.pack_start(self.search_scrolled, True, True, 0)
        self.app_container.reorder_child(self.search_scrolled, 2)

        self.show_all()
        self.categories_box.hide()

    def get_category_display_name(self, category):
        category_display_name = None

        for (c, display_name, _) in emojis.get_category_order():
            if c == category:
                category_display_name = display_name
                break

        return category_display_name

    def render_selected_emoji_category(self):
        if hasattr(self, "category_scrolled"):
            self.app_container.remove(self.category_scrolled)

        self.category_scrolled = Gtk.ScrolledWindow()
        self.category_scrolled.set_hexpand(False)

        category = self.selected_emoji_category

        category_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        label_box = Gtk.Box()
        label = Gtk.Label(margin_right=GRID_SIZE, margin_left=GRID_SIZE)
        label.set_name("category_label")
        label.set_text(self.get_category_display_name(category))
        label.set_justify(Gtk.Justification.LEFT)
        label_box.pack_start(label, False, False, 0)
        category_box.pack_start(Gtk.Box(), False, False, 0)
        category_box.add(label_box)

        category_box.pack_start(
            self.create_emoji_results(emojis.get_emojis_by_category()[category], True),
            False,
            False,
            0,
        )

        self.category_scrolled.add(category_box)
        self.app_container.pack_start(self.category_scrolled, True, True, 0)
        self.app_container.reorder_child(self.category_scrolled, 2)

        self.show_all()

    def create_emoji_results(self, emojis, for_category=False):
        self.current_emojis = emojis

        if len(emojis) > 0:
            self.target_emoji = emojis[0]["char"]
        self.reset_emoji_preview()

        results_grid = Gtk.Grid(
            orientation=Gtk.Orientation.VERTICAL,
            margin=GRID_SIZE,
            margin_bottom=0,
            margin_top=GRID_SIZE if for_category else 0,
        )
        results_grid.set_row_homogeneous(True)
        results_grid.set_column_homogeneous(True)

        row = 0

        for emoji_row in grouper(emojis, EMOJIS_PER_ROW, None):
            row += 1
            column = 0

            for emoji in emoji_row:
                column += 1

                if emoji is None:
                    btn = Gtk.Button(
                        label=" ",
                        name="emoji_button",
                        can_focus=False,
                        relief=Gtk.ReliefStyle.NONE,
                        sensitive=False,
                    )
                else:
                    btn = Gtk.Button(
                        label=emoji["char"],
                        name="emoji_button",
                        relief=Gtk.ReliefStyle.NONE,
                    )
                    btn.connect("event", self.on_emoji_btn_event)

                if row == 1 and column == 1:
                    self.first_emoji_widget = btn

                btn.set_size_request(10, 10)

                btn_af = Gtk.AspectFrame(
                    xalign=0.5, yalign=0.5, ratio=1.0, name="emoji_button_af"
                )
                btn_af.add(btn)

                results_grid.attach(btn_af, column, row, 1, 1)

        return results_grid

    def on_emoji_btn_event(self, btn, event):
        emoji = btn.get_label()

        if event.type == Gdk.EventType.BUTTON_PRESS:
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

        elif event.type == Gdk.EventType.KEY_PRESS:
            keyval = event.keyval
            keyval_name = Gdk.keyval_name(keyval)
            shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)

            if shift and keyval_name == "Return":
                self.on_emoji_append(emoji)
            elif keyval_name == "Return":
                self.on_emoji_select(emoji)

        elif event.type == Gdk.EventType.ENTER_NOTIFY:
            self.show_emoji_preview(emoji)

        elif event.type == Gdk.EventType.LEAVE_NOTIFY:
            self.reset_emoji_preview()

        elif event.type == Gdk.EventType.FOCUS_CHANGE:
            self.target_emoji = emoji
            self.show_emoji_preview(emoji)

    def on_emoji_append(self, emoji):
        """Append the selected emoji to the clipboard"""
        print(f"Appending {emoji} to selection")
        self.emoji_append_list.append(emoji)

        if len(self.emoji_append_list) == 1:
            self.selected_box.show_all()
            self.previewed_emoji_name_label.set_max_width_chars(20)
            self.previewed_emoji_shortcode_label.set_max_width_chars(20)

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

        if not config.is_wayland:
            os.system("xdotool key ctrl+v")

    def add_emoji_to_recent(self, emoji):
        user_data.update_recent_emojis(emoji)
        emojis.update_recent_category()

    def copy_to_clipboard(self, content):
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(content, -1)
