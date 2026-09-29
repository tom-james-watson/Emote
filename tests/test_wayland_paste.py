import unittest

from emote.wayland_paste import WaylandPaste


class WaylandPasteTests(unittest.TestCase):
    def test_paste_is_rejected_until_keyboard_is_ready(self):
        backend = WaylandPaste()

        self.assertFalse(backend.paste())

    def test_ready_paste_is_queued(self):
        backend = WaylandPaste()
        backend._ready.set()

        self.assertTrue(backend.paste())
        self.assertTrue(backend._requests.get_nowait())

    def test_close_immediately_removes_readiness(self):
        backend = WaylandPaste()
        backend._ready.set()

        backend.close()

        self.assertFalse(backend.is_ready)
        self.assertFalse(backend.paste())


if __name__ == "__main__":
    unittest.main()
