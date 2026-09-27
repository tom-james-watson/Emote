"""A continuous emoji catalogue for GTK 4."""

import os
import subprocess
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from emote import (
    config,
    css,
    debouncer,
    emojis,
    guide,
    keyboard_shortcuts,
    settings,
    user_data,
)

CATEGORY_ICONS = {
    "recent": "emote-category-recent-symbolic",
    "smileys-people": "emote-category-smileys-people-symbolic",
    "animals-nature": "emote-category-animals-nature-symbolic",
    "food-drink": "emote-category-food-drink-symbolic",
    "activities": "emote-category-activities-symbolic",
    "travel-places": "emote-category-travel-places-symbolic",
    "objects": "emote-category-objects-symbolic",
    "symbols": "emote-category-symbols-symbolic",
    "flags": "emote-category-flags-symbolic",
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
            if self.pending_width_update is not None:
                GLib.source_remove(self.pending_width_update)
            # Rebuilding the list for every intermediate width while the user
            # drags the window can repeatedly replace its model during layout.
            # Wait until the resize settles and rebuild once at the final width.
            self.pending_width_update = GLib.timeout_add(100, self.notify_width_changed)

    def notify_width_changed(self):
        self.pending_width_update = None
        self.width_changed(self.last_width)
        return GLib.SOURCE_REMOVE


class EmojiPicker(Adw.ApplicationWindow):
    def __init__(self, application, update_accelerator, show_welcome=False):
        super().__init__(application=application, title="Emote")
        self.update_accelerator = update_accelerator
        self.set_default_size(*user_data.load_picker_size())
        self.set_size_request(-1, 300)
        self.set_resizable(True)
        self.set_hide_on_close(False)

        self.appended = []
        self.display_emojis = []
        self.emoji_rows = {}
        self.category_rows = {}
        self.visible_rows = {}
        self.visible_buttons = {}
        self.selected_index = 0
        self.skintone_index = user_data.load_skintone_index()
        self.emoji_size = user_data.load_emoji_size()
        self.emojis_per_row = 1
        self.active_category = "recent"
        self.category_jump = None
        self.pending_category_restore = None
        self.pending_scroll_update = None
        self.search_scroll_position = None
        self.search_scroll_category = None
        self.search_selected_index = None
        self.pending_search_scroll_restore = None
        self.search_scroll_restore_handler = None
        self.search_scroll_restore_target = None
        self.searching = False
        self.was_active = False
        self.pending_inactive_close = None
        self.recent_dirty = False
        self.search_debouncer = debouncer.SearchDebouncer(self.apply_search)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.add_css_class("picker")
        root.add_css_class(f"emoji-size-{self.emoji_size}")
        self.root = root
        self.set_content(root)
        toolbar = Adw.ToolbarView()
        toolbar.set_top_bar_style(Adw.ToolbarStyle.RAISED)
        toolbar.set_bottom_bar_style(Adw.ToolbarStyle.RAISED)
        root.append(toolbar)

        self.build_header()
        toolbar.add_top_bar(self.header)
        self.build_navigation()
        toolbar.add_top_bar(self.navigation)
        self.build_list()
        toolbar.set_content(self.scroller)
        self.build_footer()
        toolbar.add_bottom_bar(self.footer)

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

        menu = Gio.Menu()
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

    def build_navigation(self):
        self.navigation = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True, spacing=2
        )
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
            image.set_pixel_size(20)
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
        if self.pending_category_restore is not None:
            GLib.source_remove(self.pending_category_restore)
            self.pending_category_restore = None
        query = self.search_entry.get_text().strip()
        if query:
            self.apply_search(query)
        else:
            category = self.active_category
            self.show_catalogue()
            if category != "recent":
                self.pending_category_restore = GLib.timeout_add(
                    100, self.restore_category_after_resize, category
                )

    def prepare_for_open(self):
        self.cancel_search_scroll_restore()
        self.search_scroll_position = None
        self.search_scroll_category = None
        self.search_selected_index = None
        self.appended.clear()
        self.selection_label.set_text("")
        self.selection_label.set_visible(False)
        self.search_debouncer.cancel()
        columns = self.columns_for_width(self.scroller.last_width, self.emoji_size)
        width_changed = self.scroller.last_width > 0 and columns != self.emojis_per_row
        if width_changed:
            self.emojis_per_row = columns
        if self.search_entry.get_text() or self.searching or width_changed:
            self.search_entry.set_text("")
            self.search_debouncer.cancel()
            self.show_catalogue()
        elif self.recent_dirty:
            self.refresh_recent_rows()
        self.selected_index = 0
        self.update_visible_selection()
        self.update_preview()
        self.scroller.get_vadjustment().set_value(0)
        self.set_active_category("recent")
        GLib.idle_add(self.search_entry.grab_focus)

    def prepare_for_close(self):
        self.search_debouncer.cancel()
        self.cancel_search_scroll_restore()
        self.category_jump = None
        if self.scroller.pending_width_update is not None:
            GLib.source_remove(self.scroller.pending_width_update)
            self.scroller.pending_width_update = None
        if self.pending_category_restore is not None:
            GLib.source_remove(self.pending_category_restore)
            self.pending_category_restore = None
        if self.pending_scroll_update is not None:
            GLib.source_remove(self.pending_scroll_update)
            self.pending_scroll_update = None
        if self.pending_inactive_close is not None:
            GLib.source_remove(self.pending_inactive_close)
            self.pending_inactive_close = None
        dialog = self.get_visible_dialog()
        if dialog:
            dialog.close()

    def refresh_recent_rows(self):
        emojis.update_recent_category()
        entries = emojis.get_emojis_by_category()["recent"][: self.emojis_per_row * 2]
        old_row_count = self.category_rows["smileys-people"] - 1
        old_entry_count = sum(
            len(self.rows.get_item(i).entries) for i in range(1, old_row_count + 1)
        )
        recent_rows = [
            PickerRow(
                "recent", None, entries[offset : offset + self.emojis_per_row], offset
            )
            for offset in range(0, len(entries), self.emojis_per_row)
        ]
        self.rows.splice(1, old_row_count, recent_rows)
        index_shift = len(entries) - old_entry_count
        for row_number in range(1 + len(recent_rows), self.rows.get_n_items()):
            row = self.rows.get_item(row_number)
            if row.title is None:
                row.start_index += index_shift
        self.display_emojis[:old_entry_count] = entries

        self.category_rows = {}
        self.emoji_rows = {}
        for row_number in range(self.rows.get_n_items()):
            row = self.rows.get_item(row_number)
            if row.title is not None:
                self.category_rows[row.category] = row_number
            else:
                for index in range(row.start_index, row.start_index + len(row.entries)):
                    self.emoji_rows[index] = row_number

        self.visible_buttons.clear()
        for box, row in tuple(self.visible_rows.items()):
            if row.title is not None:
                continue
            for offset, button in enumerate(box.emoji_buttons[: len(row.entries)]):
                index = row.start_index + offset
                button.emoji_index = index
                self.visible_buttons[index] = button
        self.recent_dirty = False

    def restore_category_after_resize(self, category):
        self.pending_category_restore = None
        if self.get_visible():
            self.on_category_clicked(None, category)
        return GLib.SOURCE_REMOVE

    def show_catalogue(self, reset_scroll=True):
        emojis.update_recent_category()
        self.recent_dirty = False
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
        self.replace_rows(rows, reset_scroll=reset_scroll)
        self.searching = False
        self.set_active_category("recent")

    def apply_search(self, query):
        query = query.strip()
        if not query:
            if not self.searching:
                return
            position = self.search_scroll_position
            category = self.search_scroll_category
            selected_index = self.search_selected_index
            self.show_catalogue(reset_scroll=False)
            self.search_scroll_position = None
            self.search_scroll_category = None
            self.search_selected_index = None
            if selected_index is not None and self.display_emojis:
                self.selected_index = min(selected_index, len(self.display_emojis) - 1)
                self.update_visible_selection()
                self.update_preview()
            if position is not None:
                self.schedule_search_scroll_restore(position, category)
            return
        if not self.searching:
            self.search_scroll_position = self.scroller.get_vadjustment().get_value()
            self.search_scroll_category = self.active_category
            self.search_selected_index = self.selected_index
            self.nav_items[self.active_category].set_active(False)
            self.nav_icons[self.active_category].add_css_class("dim-label")
        self.searching = True
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

    def replace_rows(self, rows, reset_scroll=True):
        self.cancel_search_scroll_restore()
        if self.pending_category_restore is not None:
            GLib.source_remove(self.pending_category_restore)
            self.pending_category_restore = None
        if self.pending_scroll_update is not None:
            GLib.source_remove(self.pending_scroll_update)
            self.pending_scroll_update = None
        self.category_jump = None
        for box in tuple(self.visible_rows):
            for button in box.emoji_buttons:
                button.remove_css_class("keyboard-selected")
        self.selected_index = 0
        self.visible_rows.clear()
        self.visible_buttons.clear()
        self.rows.splice(0, self.rows.get_n_items(), rows)
        self.update_preview()
        if reset_scroll:
            self.list_view.scroll_to(0, Gtk.ListScrollFlags.NONE, None)
            self.scroller.get_vadjustment().set_value(0)

    def cancel_search_scroll_restore(self):
        if self.pending_search_scroll_restore is not None:
            GLib.source_remove(self.pending_search_scroll_restore)
            self.pending_search_scroll_restore = None
        if self.search_scroll_restore_handler is not None:
            self.scroller.get_vadjustment().disconnect(self.search_scroll_restore_handler)
            self.search_scroll_restore_handler = None
        self.search_scroll_restore_target = None

    def schedule_search_scroll_restore(self, position, category):
        self.search_scroll_restore_target = (position, category)
        adjustment = self.scroller.get_vadjustment()
        self.search_scroll_restore_handler = adjustment.connect(
            "changed", self.try_restore_search_scroll
        )
        self.pending_search_scroll_restore = GLib.timeout_add(
            400, self.finish_search_scroll_restore
        )
        self.try_restore_search_scroll(adjustment)

    def try_restore_search_scroll(self, adjustment, force=False):
        if self.search_scroll_restore_target is None:
            return
        position, category = self.search_scroll_restore_target
        maximum = max(0, adjustment.get_upper() - adjustment.get_page_size())
        if maximum < position and not force:
            return
        self.cancel_search_scroll_restore()
        adjustment.set_value(min(position, maximum))
        self.set_active_category(category)

    def finish_search_scroll_restore(self):
        self.pending_search_scroll_restore = None
        self.try_restore_search_scroll(self.scroller.get_vadjustment(), force=True)
        return GLib.SOURCE_REMOVE

    def setup_row(self, _factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.title_label = Gtk.Label(xalign=0)
        box.title_label.add_css_class("category-title")
        box.title_label.add_css_class("dim-label")
        box.title_label.set_visible(False)
        box.append(box.title_label)
        box.emoji_buttons = []
        box.bound_row = None
        box.hovered_index = None

        motion = Gtk.EventControllerMotion.new()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect("enter", self.on_row_motion, box)
        motion.connect("motion", self.on_row_motion, box)
        motion.connect("leave", self.on_row_leave, box)
        box.add_controller(motion)

        right_click = Gtk.GestureClick.new()
        right_click.set_button(3)
        right_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        right_click.connect("pressed", self.on_row_right_pressed, box)
        box.add_controller(right_click)
        list_item.set_child(box)
        list_item.set_selectable(False)
        list_item.set_activatable(False)

    def bind_row(self, _factory, list_item):
        row = list_item.get_item()
        box = list_item.get_child()
        box.bound_row = row
        box.hovered_index = None
        self.visible_rows[box] = row
        box.set_homogeneous(row.title is None)
        box.remove_css_class("category-row")
        box.remove_css_class("emoji-row")

        if row.title is not None:
            box.add_css_class("category-row")
            box.title_label.set_text(row.title)
            box.title_label.set_visible(True)
            for button in box.emoji_buttons:
                button.emoji_index = None
                button.remove_css_class("keyboard-selected")
                button.set_visible(False)
            return

        box.add_css_class("emoji-row")
        box.title_label.set_visible(False)
        while len(box.emoji_buttons) < self.emojis_per_row:
            button = Gtk.Button()
            button.set_has_frame(False)
            button.set_hexpand(True)
            button.add_css_class("emoji-cell")
            button.set_focusable(False)
            button.emoji_index = None
            button.connect("clicked", self.on_bound_button_clicked)
            box.append(button)
            box.emoji_buttons.append(button)

        for offset, button in enumerate(box.emoji_buttons):
            if offset >= self.emojis_per_row:
                button.emoji_index = None
                button.set_visible(False)
                continue
            if offset >= len(row.entries):
                button.emoji_index = None
                button.set_label("")
                button.set_tooltip_text(None)
                button.set_sensitive(False)
                button.remove_css_class("keyboard-selected")
                button.set_visible(True)
                continue
            emoji = row.entries[offset]
            index = row.start_index + offset
            button.emoji_index = index
            button.set_label(self.get_skintone_char(emoji))
            button.set_tooltip_text(emoji["name"])
            button.set_sensitive(True)
            button.set_visible(True)
            if index == self.selected_index:
                button.add_css_class("keyboard-selected")
            else:
                button.remove_css_class("keyboard-selected")
            self.visible_buttons[index] = button

    def unbind_row(self, _factory, list_item):
        row = list_item.get_item()
        box = list_item.get_child()
        if self.visible_rows.get(box) is row:
            self.visible_rows.pop(box)
        if row and row.title is None:
            for offset, button in enumerate(box.emoji_buttons[: len(row.entries)]):
                index = row.start_index + offset
                if self.visible_buttons.get(index) is button:
                    self.visible_buttons.pop(index)
        box.bound_row = None
        box.hovered_index = None
        for button in box.emoji_buttons:
            button.emoji_index = None
            button.remove_css_class("keyboard-selected")

    def on_bound_button_clicked(self, button):
        if button.emoji_index is not None:
            self.select_emoji(button.emoji_index)

    def row_index_at(self, box, x):
        if box.bound_row is None or box.bound_row.title is not None:
            return None
        for button in box.emoji_buttons:
            if button.emoji_index is None or not button.get_visible():
                continue
            result = button.compute_bounds(box)
            if result:
                rect = result[1] if isinstance(result, tuple) else result
                if rect.get_x() <= x < rect.get_x() + rect.get_width():
                    return button.emoji_index
        return None

    def on_row_motion(self, _controller, x, _y, box):
        index = self.row_index_at(box, x)
        if box.hovered_index != index:
            box.hovered_index = index
            self.update_preview(index)

    def on_row_leave(self, _controller, box):
        if box.hovered_index is not None:
            box.hovered_index = None
            self.update_preview()

    def on_row_right_pressed(self, _gesture, _n_press, x, _y, box):
        index = self.row_index_at(box, x)
        if index is not None:
            self.append_emoji(index)

    def on_category_clicked(self, _button, category):
        self.cancel_search_scroll_restore()
        if self.searching or self.search_entry.get_text():
            self.search_entry.set_text("")
            self.search_debouncer.cancel()
            self.search_scroll_position = None
            self.search_scroll_category = None
            self.search_selected_index = None
            self.show_catalogue()
        self.category_jump = category
        self.set_active_category(category)
        target_index = self.category_rows[category]
        position = self.category_scroll_position(target_index)
        if position is not None:
            self.scroller.get_vadjustment().set_value(position)
        else:
            self.list_view.scroll_to(target_index, Gtk.ListScrollFlags.NONE, None)
        GLib.timeout_add(100, self.finish_category_jump, category)

    def category_scroll_position(self, target_index):
        # Offscreen list rows may have no allocation. Their measured heights
        # include list spacing; a mapped row anchors the sum to scroll space.
        boxes = {row: box for box, row in self.visible_rows.items()}
        heights_by_kind = {}
        for row, box in boxes.items():
            height = box.get_parent().measure(Gtk.Orientation.VERTICAL, -1)[1]
            if height <= 0:
                return None
            kind = row.title is not None
            if kind in heights_by_kind and heights_by_kind[kind] != height:
                heights_by_kind[kind] = None
            elif kind not in heights_by_kind:
                heights_by_kind[kind] = height

        adjustment = self.scroller.get_vadjustment()
        row_top = 0
        target_top = None
        layout_offsets = []
        for index in range(self.rows.get_n_items()):
            row = self.rows.get_item(index)
            box = boxes.get(row)
            if index == target_index:
                target_top = row_top
            if box is not None and box.get_mapped():
                result = box.compute_bounds(self.scroller)
                if result:
                    rect = result[1] if isinstance(result, tuple) else result
                    layout_offsets.append(
                        adjustment.get_value() + rect.get_y() - row_top
                    )
            if box is None:
                height = heights_by_kind.get(row.title is not None)
            else:
                height = box.get_parent().measure(Gtk.Orientation.VERTICAL, -1)[1]
            if height is None:
                return None
            row_top += height
        if not layout_offsets or max(layout_offsets) - min(layout_offsets) > 1:
            return None
        return target_top + layout_offsets[0]

    def finish_category_jump(self, category):
        if self.category_jump == category:
            self.category_jump = None
            self.set_active_category(category)
        return GLib.SOURCE_REMOVE

    def on_scroll_changed(self, _adjustment):
        if self.searching or self.category_jump or self.search_scroll_restore_target:
            return
        if self.pending_scroll_update is None:
            self.pending_scroll_update = GLib.idle_add(self.update_category_from_scroll)

    def update_category_from_scroll(self):
        self.pending_scroll_update = None
        if self.searching or self.category_jump or self.search_scroll_restore_target:
            return GLib.SOURCE_REMOVE
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
        if closest and closest[1] in self.nav_items:
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
            self.schedule_inactive_close()

    def on_menu_active_changed(self, button, _property):
        if not button.get_active():
            self.schedule_inactive_close()

    def schedule_inactive_close(self):
        if self.pending_inactive_close is None:
            self.pending_inactive_close = GLib.timeout_add(75, self.close_if_inactive)

    def close_if_inactive(self):
        self.pending_inactive_close = None
        if self.is_active() or self.menu_button.get_active():
            return GLib.SOURCE_REMOVE
        if self.get_visible_dialog() is None:
            self.get_application().close_picker_window()
        return GLib.SOURCE_REMOVE

    def on_key_pressed(self, _controller, keyval, _keycode, state):
        if self.get_visible_dialog() is not None:
            return False
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
            self.move_selection_vertical(1)
            return True
        if keyval == Gdk.KEY_Up:
            self.move_selection_vertical(-1)
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
        self.set_selected_index(
            max(0, min(len(self.display_emojis) - 1, self.selected_index + delta))
        )

    def set_selected_index(self, index):
        self.cancel_search_scroll_restore()
        self.selected_index = index
        self.update_visible_selection()
        self.update_preview()
        self.list_view.scroll_to(
            self.emoji_rows[self.selected_index], Gtk.ListScrollFlags.NONE, None
        )

    def update_visible_selection(self):
        for box in tuple(self.visible_rows):
            for button in box.emoji_buttons:
                if (
                    button.emoji_index is not None
                    and button.emoji_index == self.selected_index
                ):
                    button.add_css_class("keyboard-selected")
                else:
                    button.remove_css_class("keyboard-selected")

    def move_selection_vertical(self, direction):
        if not self.display_emojis:
            return

        current_row_index = self.emoji_rows[self.selected_index]
        current_row = self.rows.get_item(current_row_index)
        column = self.selected_index - current_row.start_index
        row_index = current_row_index + direction

        while 0 <= row_index < self.rows.get_n_items():
            row = self.rows.get_item(row_index)
            if row.title is None:
                self.set_selected_index(
                    row.start_index + min(column, len(row.entries) - 1)
                )
                return
            row_index += direction

    def get_skintone_char(self, emoji):
        variants = emoji["skintone"]
        if not variants or self.skintone_index == 0:
            return emoji["char"]
        return variants.get(str(self.skintone_index), emoji)["char"]

    def set_skin_tone(self, index):
        if index < 0 or index >= len(user_data.SKINTONES):
            return
        if index == self.skintone_index:
            return
        self.skintone_index = index
        user_data.update_skintone_index(index)
        rows = [self.rows.get_item(i) for i in range(self.rows.get_n_items())]
        scroll_position = self.scroller.get_vadjustment().get_value()
        # Update current cells before replacing rows unbinds them.
        for emoji_index, button in tuple(self.visible_buttons.items()):
            if emoji_index < len(self.display_emojis):
                button.set_label(
                    self.get_skintone_char(self.display_emojis[emoji_index])
                )

        # Fresh row objects make Gtk.ListView rebind cells with the new tone.
        refreshed_rows = [
            PickerRow(row.category, row.title, row.entries, row.start_index)
            for row in rows
        ]
        self.rows.splice(0, len(rows), refreshed_rows)
        self.update_preview()
        GLib.idle_add(self.restore_grid_scroll_position, scroll_position)

    def restore_grid_scroll_position(self, position):
        self.scroller.get_vadjustment().set_value(position)
        return GLib.SOURCE_REMOVE

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

    def append_emoji(self, index):
        emoji = self.get_skintone_char(self.display_emojis[index])
        self.appended.append(emoji)
        self.copy_to_clipboard("".join(self.appended))
        user_data.update_recent_emojis(emoji)
        self.recent_dirty = True
        self.selection_label.set_text("".join(self.appended))
        self.selection_label.set_visible(True)

    def select_emoji(self, index):
        emoji = self.get_skintone_char(self.display_emojis[index])
        content = "".join(self.appended) + emoji
        self.copy_to_clipboard(content)
        user_data.update_recent_emojis(emoji)
        self.recent_dirty = True
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
        self.show_dialog(
            keyboard_shortcuts.KeyboardShortcuts(self, self.update_accelerator)
        )

    def open_guide(self):
        self.show_dialog(guide.Guide(self))
        return GLib.SOURCE_REMOVE

    def show_dialog(self, dialog):
        dialog.present(self)

    def open_about(self):
        dialog = Adw.AboutDialog(
            application_name="Emote",
            application_icon=config.app_id,
            version=os.environ.get(
                "FLATPAK_APP_VERSION", os.environ.get("SNAP_VERSION", "dev build")
            ),
            developers=["Tom Watson", "Vincent Emonet"],
            artists=["Tom Watson, Matthew Wong"],
            documenters=["Irene Auñón"],
            copyright=f"© Tom Watson {datetime.now().year}",
            website="https://github.com/tom-james-watson/emote",
            comments="Popup emoji picker for Linux",
            license_type=Gtk.License.GPL_3_0,
        )
        self.show_dialog(dialog)
