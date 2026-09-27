"""A continuous emoji catalogue for GTK 4."""

import os
import subprocess
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango

from emote import config, debouncer, emojis, guide, keyboard_shortcuts, settings, user_data

CATEGORY_ICONS = {
    "recent": "emoji-recent-symbolic",
    "smileys-people": "emoji-people-symbolic",
    "animals-nature": "emoji-nature-symbolic",
    "food-drink": "emoji-food-symbolic",
    "activities": "emoji-activities-symbolic",
    "travel-places": "emoji-travel-symbolic",
    "objects": "emoji-objects-symbolic",
    "symbols": "emoji-symbols-symbolic",
    "flags": "emoji-flags-symbolic",
}


class PickerRow(GObject.Object):
    def __init__(self, category, title, entries=(), start_index=0):
        super().__init__()
        self.category = category
        self.title = title
        self.entries = entries
        self.start_index = start_index


class WidthAwareScrolledWindow(Gtk.ScrolledWindow):
    def __init__(self, width_changed):
        super().__init__()
        self.width_changed = width_changed
        self.last_width = 0
        self.pending_width_update = None

    def do_size_allocate(self, width, height, baseline):
        Gtk.ScrolledWindow.do_size_allocate(self, width, height, baseline)
        if width > 0 and width != self.last_width:
            self.last_width = width
            if self.pending_width_update is None:
                self.pending_width_update = GLib.idle_add(self.notify_width_changed)

    def notify_width_changed(self):
        self.pending_width_update = None
        self.width_changed(self.last_width)
        return GLib.SOURCE_REMOVE


class EmojiPicker(Gtk.ApplicationWindow):
    def __init__(self, application, update_accelerator, show_welcome=False):
        super().__init__(application=application, title="Emote")
        self.update_accelerator = update_accelerator
        self.set_default_size(*user_data.load_picker_size())
        self.set_size_request(-1, 300)
        self.set_resizable(True)
        self.set_decorated(False)
        self.set_hide_on_close(False)

        self.appended = []
        self.display_emojis = []
        self.emoji_rows = {}
        self.category_rows = {}
        self.visible_rows = {}
        self.visible_buttons = {}
        self.selected_index = 0
        self.keyboard_selection_visible = False
        self.skintone_index = user_data.load_skintone_index()
        self.emoji_size = user_data.load_emoji_size()
        self.emojis_per_row = 1
        self.active_category = "recent"
        self.category_jump = None
        self.searching = False
        self.dialogs = []
        self.was_active = False
        self.search_debouncer = debouncer.SearchDebouncer(self.apply_search)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.add_css_class("picker")
        root.add_css_class(f"emoji-size-{self.emoji_size}")
        self.root = root
        self.set_child(root)

        self.build_header()
        root.append(self.header)
        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.build_navigation()
        root.append(self.navigation)
        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.build_list()
        root.append(self.scroller)
        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.build_footer()
        root.append(self.footer)

        keys = Gtk.EventControllerKey.new()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.on_key_pressed)
        self.add_controller(keys)
        self.connect("notify::is-active", self.on_active_changed)
        self.connect("close-request", self.on_close_request)

        GLib.idle_add(self.search_entry.grab_focus)
        if show_welcome:
            GLib.idle_add(self.open_guide)

    def build_header(self):
        self.header = Gtk.WindowHandle()
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.add_css_class("picker-header")
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search emoji")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        bar.append(self.search_entry)

        tone_options = (
            "Default",
            "Light",
            "Medium-light",
            "Medium",
            "Medium-dark",
            "Dark",
        )
        tone_menu = Gio.Menu()
        for index, (hand, label) in enumerate(zip(user_data.SKINTONES, tone_options)):
            item = Gio.MenuItem.new(f"{hand}  {label}", None)
            item.set_action_and_target_value("win.skin-tone", GLib.Variant("i", index))
            tone_menu.append_item(item)

        menu = Gio.Menu()
        tone_section = Gio.Menu()
        tone_section.append_submenu("Skin Tone", tone_menu)
        menu.append_section(None, tone_section)
        standard_section = Gio.Menu()
        standard_section.append("Preferences", "win.preferences")
        standard_section.append("Keyboard Shortcuts", "win.shortcuts")
        standard_section.append("Guide", "win.guide")
        standard_section.append("About Emote", "win.about")
        menu.append_section(None, standard_section)
        self.menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        self.menu_button.set_tooltip_text("Menu")
        self.menu_button.set_menu_model(menu)
        self.menu_button.connect("notify::active", self.on_menu_active_changed)
        bar.append(self.menu_button)
        self.header.set_child(bar)

        for name, callback in (
            ("preferences", self.open_preferences),
            ("shortcuts", self.open_shortcuts),
            ("guide", self.open_guide),
            ("about", self.open_about),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _action, _param, fn=callback: fn())
            self.add_action(action)

        self.skin_tone_action = Gio.SimpleAction.new_stateful(
            "skin-tone", GLib.VariantType.new("i"), GLib.Variant("i", self.skintone_index)
        )
        self.skin_tone_action.connect("change-state", self.on_skin_tone_changed)
        self.add_action(self.skin_tone_action)

    def build_navigation(self):
        self.navigation = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True, spacing=2)
        self.navigation.add_css_class("category-navigation")
        self.nav_items = {}
        self.nav_icons = {}
        first_button = None

        for category, label, _icon in emojis.get_category_order():
            button = Gtk.ToggleButton()
            if first_button is None:
                first_button = button
            else:
                button.set_group(first_button)
            image = Gtk.Image.new_from_icon_name(CATEGORY_ICONS[category])
            image.set_pixel_size(22)
            image.add_css_class("dim-label")
            button.set_child(image)
            button.set_tooltip_text(label)
            button.set_has_frame(False)
            button.set_halign(Gtk.Align.CENTER)
            button.set_size_request(36, 36)
            button.add_css_class("circular")
            button.connect("clicked", self.on_category_clicked, category)
            self.navigation.append(button)
            self.nav_items[category] = button
            self.nav_icons[category] = image
        self.set_active_category("recent")

    def build_list(self):
        self.rows = Gio.ListStore.new(PickerRow)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.setup_row)
        factory.connect("bind", self.bind_row)
        factory.connect("unbind", self.unbind_row)
        self.list_view = Gtk.ListView.new(Gtk.NoSelection.new(self.rows), factory)
        self.list_view.add_css_class("emoji-list")
        self.list_view.set_single_click_activate(False)
        self.scroller = WidthAwareScrolledWindow(self.on_grid_width_changed)
        self.scroller.set_vexpand(True)
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_child(self.list_view)
        self.scroller.get_vadjustment().connect("value-changed", self.on_scroll_changed)

    def build_footer(self):
        self.footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.footer.add_css_class("preview-footer")
        self.preview_emoji = Gtk.Label()
        self.preview_emoji.add_css_class("preview-emoji")
        self.preview_emoji.set_valign(Gtk.Align.CENTER)
        self.footer.append(self.preview_emoji)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        labels.set_valign(Gtk.Align.CENTER)
        self.preview_name = Gtk.Label(xalign=0)
        self.preview_name.add_css_class("preview-name")
        self.preview_name.add_css_class("heading")
        self.preview_name.set_ellipsize(Pango.EllipsizeMode.END)
        self.preview_shortcode = Gtk.Label(xalign=0)
        self.preview_shortcode.add_css_class("preview-shortcode")
        self.preview_shortcode.add_css_class("dim-label")
        self.preview_shortcode.set_ellipsize(Pango.EllipsizeMode.END)
        labels.append(self.preview_name)
        labels.append(self.preview_shortcode)
        self.footer.append(labels)

        self.selection_label = Gtk.Label()
        self.selection_label.add_css_class("selection-count")
        self.selection_label.add_css_class("dim-label")
        self.selection_label.set_ellipsize(Pango.EllipsizeMode.START)
        self.selection_label.set_max_width_chars(12)
        self.selection_label.set_visible(False)
        self.selection_label.set_valign(Gtk.Align.CENTER)
        self.footer.append(self.selection_label)

    @staticmethod
    def columns_for_width(width, size):
        # Keep roughly 20 px around each emoji, then share any spare
        # width evenly across the row.
        return max(1, (width - 8) // (size + 20))

    def on_grid_width_changed(self, width):
        columns = self.columns_for_width(width, self.emoji_size)
        if columns != self.emojis_per_row or self.rows.get_n_items() == 0:
            self.emojis_per_row = columns
            self.refresh_rows()

    def set_emoji_size(self, size):
        size = user_data.normalize_emoji_size(size)
        if size == self.emoji_size:
            return
        self.root.remove_css_class(f"emoji-size-{self.emoji_size}")
        self.emoji_size = size
        self.emojis_per_row = self.columns_for_width(self.scroller.get_width(), size)
        self.root.add_css_class(f"emoji-size-{size}")
        user_data.update_emoji_size(size)
        self.refresh_rows()

    def refresh_rows(self):
        query = self.search_entry.get_text().strip()
        if query:
            self.apply_search(query)
        else:
            category = self.active_category
            self.show_catalogue()
            if category != "recent":
                GLib.timeout_add(100, self.restore_category_after_resize, category)

    def restore_category_after_resize(self, category):
        self.on_category_clicked(None, category)
        return GLib.SOURCE_REMOVE

    def show_catalogue(self):
        emojis.update_recent_category()
        rows = []
        self.display_emojis = []
        self.emoji_rows = {}
        self.category_rows = {}
        categories = emojis.get_emojis_by_category()
        for category, title, _icon in emojis.get_category_order():
            entries = categories.get(category, [])
            if category == "recent":
                entries = entries[: self.emojis_per_row * 2]
            self.category_rows[category] = len(rows)
            rows.append(PickerRow(category, title))
            for offset in range(0, len(entries), self.emojis_per_row):
                start = len(self.display_emojis)
                chunk = entries[offset : offset + self.emojis_per_row]
                rows.append(PickerRow(category, None, chunk, start))
                for index in range(start, start + len(chunk)):
                    self.emoji_rows[index] = len(rows) - 1
                self.display_emojis.extend(chunk)
        self.replace_rows(rows)
        self.navigation.set_visible(True)
        self.searching = False
        self.set_active_category("recent")

    def apply_search(self, query):
        query = query.strip()
        if not query:
            self.show_catalogue()
            return
        self.searching = True
        self.navigation.set_visible(False)
        self.display_emojis = emojis.search(query)
        self.emoji_rows = {}
        rows = [PickerRow("search", f"Results for “{query}”")]
        for offset in range(0, len(self.display_emojis), self.emojis_per_row):
            chunk = self.display_emojis[offset : offset + self.emojis_per_row]
            rows.append(PickerRow("search", None, chunk, offset))
            for index in range(offset, offset + len(chunk)):
                self.emoji_rows[index] = len(rows) - 1
        if not self.display_emojis:
            rows.append(PickerRow("search", "No matching emoji"))
        self.replace_rows(rows)

    def replace_rows(self, rows):
        self.visible_rows.clear()
        self.visible_buttons.clear()
        self.rows.splice(0, self.rows.get_n_items(), rows)
        self.selected_index = 0
        self.keyboard_selection_visible = False
        self.update_preview()
        self.scroller.get_vadjustment().set_value(0)

    def setup_row(self, _factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        list_item.set_child(box)
        list_item.set_selectable(False)
        list_item.set_activatable(False)

    def bind_row(self, _factory, list_item):
        row = list_item.get_item()
        box = list_item.get_child()
        self.visible_rows[box] = row
        box.set_homogeneous(row.title is None)
        box.remove_css_class("category-row")
        box.remove_css_class("emoji-row")

        if row.title is not None:
            box.add_css_class("category-row")
            label = Gtk.Label(label=row.title, xalign=0)
            label.add_css_class("category-title")
            label.add_css_class("dim-label")
            box.append(label)
            return

        box.add_css_class("emoji-row")
        for offset, emoji in enumerate(row.entries):
            index = row.start_index + offset
            char = self.get_skintone_char(emoji)
            button = Gtk.Button(label=char)
            button.set_has_frame(False)
            button.set_hexpand(True)
            button.set_tooltip_text(emoji["name"])
            button.add_css_class("emoji-cell")
            button.set_focusable(False)
            if self.keyboard_selection_visible and index == self.selected_index:
                button.add_css_class("keyboard-selected")
            button.connect("clicked", self.on_emoji_clicked, index)

            motion = Gtk.EventControllerMotion.new()
            motion.connect("enter", lambda *_args, i=index: self.update_preview(i))
            motion.connect("leave", lambda *_args: self.update_preview())
            button.add_controller(motion)

            right_click = Gtk.GestureClick.new()
            right_click.set_button(3)
            right_click.connect("pressed", lambda *_args, i=index: self.append_emoji(i))
            button.add_controller(right_click)

            box.append(button)
            self.visible_buttons[index] = button
        for _ in range(self.emojis_per_row - len(row.entries)):
            spacer = Gtk.Box()
            spacer.set_hexpand(True)
            box.append(spacer)

    def unbind_row(self, _factory, list_item):
        row = list_item.get_item()
        box = list_item.get_child()
        self.visible_rows.pop(box, None)
        if row and row.title is None:
            for index in range(row.start_index, row.start_index + len(row.entries)):
                self.visible_buttons.pop(index, None)
        child = box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            box.remove(child)
            child = next_child

    def on_category_clicked(self, _button, category):
        if self.searching:
            self.search_entry.set_text("")
            self.show_catalogue()
        self.category_jump = category
        self.set_active_category(category)
        self.list_view.scroll_to(self.category_rows[category], Gtk.ListScrollFlags.NONE, None)
        GLib.timeout_add(50, self.align_category_at_top, category, 0)

    def align_category_at_top(self, category, attempt):
        target_row = self.rows.get_item(self.category_rows[category])
        for box, row in tuple(self.visible_rows.items()):
            if row is not target_row or not box.get_mapped():
                continue
            result = box.compute_bounds(self.scroller)
            if result:
                rect = result[1] if isinstance(result, tuple) else result
                adjustment = self.scroller.get_vadjustment()
                adjustment.set_value(adjustment.get_value() + rect.get_y())
            self.set_active_category(category)
            self.footer.queue_draw()
            GLib.timeout_add(200, self.finish_category_jump, category)
            return GLib.SOURCE_REMOVE
        if attempt < 10:
            GLib.timeout_add(50, self.align_category_at_top, category, attempt + 1)
        else:
            self.finish_category_jump(category)
        return GLib.SOURCE_REMOVE

    def finish_category_jump(self, category):
        if self.category_jump == category:
            self.category_jump = None
            self.set_active_category(category)
        return GLib.SOURCE_REMOVE

    def on_scroll_changed(self, _adjustment):
        if self.searching or self.category_jump:
            return
        GLib.idle_add(self.update_category_from_scroll)

    def update_category_from_scroll(self):
        closest = None
        for box, row in tuple(self.visible_rows.items()):
            if not box.get_mapped():
                continue
            result = box.compute_bounds(self.scroller)
            if not result:
                continue
            rect = result[1] if isinstance(result, tuple) else result
            y = rect.get_y()
            if y + rect.get_height() / 2 < 0 or y > self.scroller.get_height():
                continue
            if closest is None or y < closest[0]:
                closest = (y, row.category)
        if closest:
            self.set_active_category(closest[1])
        return GLib.SOURCE_REMOVE

    def set_active_category(self, category):
        if hasattr(self, "nav_items"):
            if self.active_category != category:
                self.nav_icons[self.active_category].add_css_class("dim-label")
            self.nav_icons[category].remove_css_class("dim-label")
            self.nav_items[category].set_active(True)
        self.active_category = category

    def on_search_changed(self, entry):
        self.search_debouncer.search(entry.get_text())

    def on_close_request(self, _window):
        self.get_application().close_picker_window()
        return True

    def on_active_changed(self, _window, _property):
        if self.is_active():
            self.was_active = True
        elif self.was_active:
            GLib.timeout_add(75, self.close_if_inactive)

    def on_menu_active_changed(self, button, _property):
        if not button.get_active():
            GLib.timeout_add(75, self.close_if_inactive)

    def close_if_inactive(self):
        if self.is_active() or self.menu_button.get_active():
            return GLib.SOURCE_REMOVE
        self.dialogs = [dialog for dialog in self.dialogs if dialog.get_visible()]
        if not self.dialogs:
            self.get_application().close_picker_window()
        return GLib.SOURCE_REMOVE

    def on_key_pressed(self, _controller, keyval, _keycode, state):
        control = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if keyval == Gdk.KEY_Escape:
            self.get_application().close_picker_window()
            return True
        if control and keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self.search_entry.grab_focus()
            return True
        if control and keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            self.cycle_category(-1 if shift else 1)
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and self.display_emojis:
            if shift:
                self.append_emoji(self.selected_index)
            else:
                self.select_emoji(self.selected_index)
            return True
        if keyval == Gdk.KEY_Down:
            self.move_selection(self.emojis_per_row)
            return True
        if keyval == Gdk.KEY_Up:
            self.move_selection(-self.emojis_per_row)
            return True
        if self.get_focus() is not self.search_entry:
            if keyval == Gdk.KEY_Right:
                self.move_selection(1)
                return True
            if keyval == Gdk.KEY_Left:
                self.move_selection(-1)
                return True
        return False

    def cycle_category(self, delta):
        categories = list(self.nav_items)
        index = categories.index(self.active_category)
        self.on_category_clicked(None, categories[(index + delta) % len(categories)])

    def move_selection(self, delta):
        if not self.display_emojis:
            return
        old = self.visible_buttons.get(self.selected_index)
        if old:
            old.remove_css_class("keyboard-selected")
        self.keyboard_selection_visible = True
        self.selected_index = max(0, min(len(self.display_emojis) - 1, self.selected_index + delta))
        new = self.visible_buttons.get(self.selected_index)
        if new:
            new.add_css_class("keyboard-selected")
        self.update_preview()
        self.list_view.scroll_to(self.emoji_rows[self.selected_index], Gtk.ListScrollFlags.NONE, None)

    def get_skintone_char(self, emoji):
        variants = emoji["skintone"]
        if not variants or self.skintone_index == 0:
            return emoji["char"]
        return variants.get(str(self.skintone_index), emoji)["char"]

    def on_skin_tone_changed(self, _action, value):
        self.set_skin_tone(value.get_int32())

    def set_skin_tone(self, index):
        if index < 0 or index >= len(user_data.SKINTONES):
            return
        if index == self.skintone_index:
            return
        self.skintone_index = index
        self.skin_tone_action.set_state(GLib.Variant("i", index))
        user_data.update_skintone_index(index)
        for emoji_index, button in tuple(self.visible_buttons.items()):
            if emoji_index < len(self.display_emojis):
                button.set_label(self.get_skintone_char(self.display_emojis[emoji_index]))
        self.update_preview()

    def update_preview(self, index=None):
        if not self.display_emojis:
            self.preview_emoji.set_text("")
            self.preview_name.set_text("No emoji")
            self.preview_shortcode.set_text("")
            return
        emoji = self.display_emojis[self.selected_index if index is None else index]
        self.preview_emoji.set_text(self.get_skintone_char(emoji))
        self.preview_name.set_text(emoji["name"])
        self.preview_shortcode.set_text(f':{emoji["shortcode"]}:')

    def on_emoji_clicked(self, _button, index):
        self.select_emoji(index)

    def append_emoji(self, index):
        emoji = self.get_skintone_char(self.display_emojis[index])
        self.appended.append(emoji)
        self.copy_to_clipboard("".join(self.appended))
        user_data.update_recent_emojis(emoji)
        self.selection_label.set_text("".join(self.appended))
        self.selection_label.set_visible(True)

    def select_emoji(self, index):
        emoji = self.get_skintone_char(self.display_emojis[index])
        content = "".join(self.appended) + emoji
        self.copy_to_clipboard(content)
        user_data.update_recent_emojis(emoji)
        self.get_application().close_picker_window()
        if not config.is_wayland:
            GLib.timeout_add(150, self.paste_x11)

    def copy_to_clipboard(self, content):
        Gdk.Display.get_default().get_clipboard().set(content)

    def paste_x11(self):
        subprocess.Popen(["xdotool", "key", "ctrl+v"])
        return GLib.SOURCE_REMOVE

    def open_preferences(self):
        self.show_dialog(settings.Settings(self))

    def open_shortcuts(self):
        self.show_dialog(keyboard_shortcuts.KeyboardShortcuts(self, self.update_accelerator))

    def open_guide(self):
        self.show_dialog(guide.Guide(self))
        return GLib.SOURCE_REMOVE

    def show_dialog(self, dialog):
        self.dialogs = [open_dialog for open_dialog in self.dialogs if open_dialog.get_visible()]
        self.dialogs.append(dialog)
        dialog.present()

    def open_about(self):
        dialog = Gtk.AboutDialog(
            transient_for=self,
            modal=True,
            program_name="Emote",
            title="About Emote",
            version=os.environ.get(
                "FLATPAK_APP_VERSION", os.environ.get("SNAP_VERSION", "dev build")
            ),
            authors=["Tom Watson", "Vincent Emonet"],
            artists=["Tom Watson, Matthew Wong"],
            documenters=["Irene Auñón"],
            copyright=f"© Tom Watson {datetime.now().year}",
            website="https://github.com/tom-james-watson/emote",
            comments="Popup emoji picker for Linux",
            license_type=Gtk.License.GPL_3_0,
        )
        self.show_dialog(dialog)
