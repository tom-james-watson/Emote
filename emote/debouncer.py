from threading import Timer
from typing import Callable
from gi.repository import GLib

# Debounce interval in seconds.
DEBOUNCE_INTERVAL = 0.2


class SearchDebouncer:
    def __init__(self, search_callback: Callable[[str], str]):
        self.callback = lambda query: GLib.idle_add(search_callback, query)
        self.timer: Timer = None

    def search(self, query: str):
        if self.timer:
            self.timer.cancel()

        self.timer = Timer(DEBOUNCE_INTERVAL, self.callback, args=(query,))
        self.timer.start()
