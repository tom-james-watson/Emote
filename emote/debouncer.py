from typing import Callable
from gi.repository import GLib

# Debounce interval in seconds.
DEBOUNCE_INTERVAL = 0.2


class SearchDebouncer:
    def __init__(self, search_callback: Callable[[str], None]):
        self.callback = search_callback
        self.source_id = None

    def search(self, query: str):
        self.cancel()
        self.source_id = GLib.timeout_add(
            int(DEBOUNCE_INTERVAL * 1000), self._run, query
        )

    def _run(self, query):
        self.source_id = None
        self.callback(query)
        return GLib.SOURCE_REMOVE

    def cancel(self):
        if self.source_id is not None:
            GLib.source_remove(self.source_id)
            self.source_id = None
