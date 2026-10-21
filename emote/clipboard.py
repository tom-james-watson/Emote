"""Temporarily own the clipboard while an automatic paste is in progress."""

from gi.repository import Gdk, Gio, GLib

from emote import config, user_data

RESTORE_DELAY_MS = 500
SNAPSHOT_TIMEOUT_MS = 3000
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024


def restoration_enabled():
    auto_paste = (
        user_data.load_wayland_auto_paste_choice() is True
        if config.is_wayland
        else user_data.load_x11_auto_paste_enabled()
    )
    return auto_paste and user_data.load_restore_clipboard_enabled()


class ClipboardPaste:
    def __init__(self, owner, generation, needs_portal):
        self.owner = owner
        self.generation = generation
        self.needs_portal = needs_portal

    def __call__(self):
        self.owner._paste_sent(self.generation)

    @property
    def cancelled(self):
        return self.generation != self.owner._generation

    def use_portal(self, setter, cancel, watch=None):
        def attach():
            if self.generation == self.owner._generation:
                if self.owner.portal_restoration:
                    self.owner._portal_setter = setter
                self.owner._portal_cancel = cancel
                if watch is not None:
                    watch(self.owner.cancel)
            else:
                cancel()
            return GLib.SOURCE_REMOVE

        GLib.idle_add(attach)


class ClipboardRestore:
    def __init__(self, clipboard, needs_portal=False, portal_restoration=True):
        self.clipboard = clipboard
        self.needs_portal = needs_portal
        self.portal_restoration = portal_restoration
        self._generation = 0
        self._provider = None
        self._snapshot = None
        self._has_snapshot = False
        self._timer = None
        self._capture = None
        self._portal_setter = None
        self._portal_cancel = None
        clipboard.connect("changed", self._changed)

    def _owns_clipboard(self):
        return (
            self._provider is not None
            and self.clipboard.get_content() == self._provider
        )

    def _changed(self, _clipboard):
        if self._provider is not None and not self._owns_clipboard():
            self.cancel()
        elif self._capture is not None:
            self._capture.fail("The clipboard changed while it was being saved.")

    def cancel(self):
        self._generation += 1
        if self._portal_cancel is not None:
            self._portal_cancel()
            self._portal_cancel = None
        if self._timer is not None:
            GLib.source_remove(self._timer)
            self._timer = None
        self._snapshot = None
        self._has_snapshot = False
        self._provider = None
        self._portal_setter = None
        if self._capture is not None:
            self._capture.fail("Clipboard saving was cancelled.")

    def copy(self, text, callback):
        """Call callback(paste_sent, error) after copying, or without changing on error."""
        if self._capture is not None:
            return
        preserve = restoration_enabled()
        reuse = preserve and self._has_snapshot and self._owns_clipboard()
        snapshot = self._snapshot if reuse else None
        self.cancel()
        generation = self._generation

        def ready(provider, error=None):
            self._capture = None
            if error is not None:
                callback(None, error)
                return
            if generation != self._generation:
                return
            self._snapshot = provider
            self._has_snapshot = preserve
            self._provider = Gdk.ContentProvider.new_for_value(text)
            # changed is synchronous on some backends: set our expected owner first.
            if not self.clipboard.set_content(self._provider):
                self.cancel()
                callback(None, "Could not copy the emoji to the clipboard.")
                return
            callback(
                ClipboardPaste(self, generation, preserve and self.needs_portal), None
            )

        if not preserve or reuse:
            ready(snapshot)
        else:
            self._capture = ClipboardSnapshot(self.clipboard, ready)
            self._capture.start()

    def _paste_sent(self, generation):
        # This callback can arrive from the Wayland input thread.
        GLib.idle_add(self._schedule_restore, generation)

    def _schedule_restore(self, generation):
        if generation == self._generation and self._has_snapshot:
            if self._timer is not None:
                GLib.source_remove(self._timer)
            self._timer = GLib.timeout_add(RESTORE_DELAY_MS, self._restore, generation)
        return GLib.SOURCE_REMOVE

    def _restore(self, generation):
        self._timer = None
        if generation != self._generation:
            return GLib.SOURCE_REMOVE
        if restoration_enabled() and self._owns_clipboard():
            snapshot = self._snapshot
            setter = self._portal_setter or self.clipboard.set_content
            # Once restored, its portal must continue serving the saved bytes.
            if self._portal_setter is not None:
                self._portal_cancel = None
            self.cancel()
            setter(snapshot)
        else:
            self.cancel()
        return GLib.SOURCE_REMOVE


class ClipboardSnapshot:
    """Materialize every offered MIME representation before replacing its owner."""

    def __init__(self, clipboard, callback):
        self.clipboard = clipboard
        self.callback = callback
        self.cancellable = Gio.Cancellable()
        self.providers = []
        self.total = 0
        self.timer = None
        self.stream = None

    def start(self):
        self.formats = list(self.clipboard.get_formats().get_mime_types())
        if not self.formats:
            if not self.clipboard.get_formats().is_empty():
                self.fail("The clipboard contains a format that cannot be saved.")
            else:
                self.finish(None)
            return
        self.timer = GLib.timeout_add(SNAPSHOT_TIMEOUT_MS, self._timeout)
        self._next_format()

    def _timeout(self):
        self.timer = None
        self.fail("Saving the clipboard took too long.")
        return GLib.SOURCE_REMOVE

    def _next_format(self):
        if not self.formats:
            self.finish(Gdk.ContentProvider.new_union(self.providers))
            return
        self.mime_type = self.formats.pop(0)
        self.data = bytearray()
        self.clipboard.read_async(
            [self.mime_type], GLib.PRIORITY_DEFAULT, self.cancellable, self._opened
        )

    def _opened(self, clipboard, result):
        try:
            stream, _mime_type = clipboard.read_finish(result)
            if self.callback is None:
                stream.close(None)
                return
            self.stream = stream
            self._read()
        except GLib.Error as error:
            self.fail(str(error))

    def _read(self):
        self.stream.read_bytes_async(
            65536, GLib.PRIORITY_DEFAULT, self.cancellable, self._received
        )

    def _received(self, stream, result):
        try:
            chunk = stream.read_bytes_finish(result)
            if self.callback is None:
                return
            self.total += chunk.get_size()
            if self.total > MAX_SNAPSHOT_BYTES:
                self.fail("The clipboard is too large to save (over 32 MiB).")
                return
            if chunk.get_size():
                self.data.extend(chunk.get_data())
                self._read()
                return
            stream.close(None)
            self.stream = None
            self.providers.append(
                Gdk.ContentProvider.new_for_bytes(
                    self.mime_type, GLib.Bytes.new(self.data)
                )
            )
            self._next_format()
        except GLib.Error as error:
            self.fail(str(error))

    def finish(self, provider, error=None):
        if self.callback is None:
            return
        callback, self.callback = self.callback, None
        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None
        self.cancellable.cancel()
        if self.stream is not None:
            self.stream.close_async(GLib.PRIORITY_DEFAULT, None, None)
            self.stream = None
        callback(provider, error)

    def fail(self, error):
        self.finish(None, error)
