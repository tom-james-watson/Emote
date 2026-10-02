"""X11 shortcut listener kept separate from GTK's toolkit version."""

import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk


class X11Hotkey:
    def __init__(self, callback):
        self.callback = callback
        self.stop_event = None
        self.thread = None

    def bind(self, accelerator):
        self.close()
        if not accelerator:
            return

        connection = None
        try:
            from Xlib import X, XK, display

            valid, keyval, modifiers = Gtk.accelerator_parse(accelerator)
            if not valid:
                return
            key_name = Gdk.keyval_name(keyval)
            keysym = XK.string_to_keysym(key_name)
            if not keysym:
                keysym = keyval
            connection = display.Display()
            keycode = connection.keysym_to_keycode(keysym)
            if not keycode:
                connection.close()
                return

            mask = 0
            if modifiers & Gdk.ModifierType.CONTROL_MASK:
                mask |= X.ControlMask
            if modifiers & Gdk.ModifierType.ALT_MASK:
                mask |= X.Mod1Mask
            if modifiers & Gdk.ModifierType.SHIFT_MASK:
                mask |= X.ShiftMask
            if modifiers & Gdk.ModifierType.SUPER_MASK:
                mask |= X.Mod4Mask

            root = connection.screen().root
            lock_masks = (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask)
            for lock_mask in lock_masks:
                root.grab_key(
                    keycode, mask | lock_mask, True, X.GrabModeAsync, X.GrabModeAsync
                )
            connection.sync()
        except Exception as exc:
            print("Could not register X11 shortcut:", exc)
            if connection:
                connection.close()
            return

        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._listen,
            args=(connection, root, keycode, mask, lock_masks, self.stop_event),
            daemon=True,
        )
        self.thread.start()

    def _listen(self, connection, root, keycode, mask, lock_masks, stop_event):
        from Xlib import X

        try:
            while not stop_event.wait(0.04):
                while connection.pending_events():
                    event = connection.next_event()
                    if event.type == X.KeyPress:
                        # GTK has not seen this Xlib event. Give it the user
                        # timestamp so the window manager can transfer focus.
                        GLib.idle_add(self.callback, f"_TIME{event.time}")
        finally:
            for lock_mask in lock_masks:
                root.ungrab_key(keycode, mask | lock_mask)
            connection.sync()
            connection.close()

    def close(self):
        if self.stop_event:
            self.stop_event.set()
            if self.thread:
                self.thread.join(timeout=1)
        self.stop_event = None
        self.thread = None
