import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import gi

gi.require_version("Pango", "1.0")
from gi.repository import Pango

from emote import config, emoji_font


class EmojiFontTests(TestCase):
    def tearDown(self):
        emoji_font.create_font_map("system")

    def test_unicode18_catalogue_and_joined_emoji_render_as_single_glyphs(self):
        with (Path(config.static_dir) / "emojis.csv").open() as source:
            new = [
                row["emoji"] for row in csv.DictReader(source) if row["unicode"] == "18"
            ]
        self.assertEqual(len(new), 19)
        font_map, bundled = emoji_font.create_font_map("noto")
        self.assertTrue(bundled)
        layout = Pango.Layout.new(font_map.create_context())
        layout.set_font_description(Pango.FontDescription(emoji_font.BUNDLED_FAMILY))
        attributes = Pango.AttrList()
        attributes.insert(Pango.attr_fallback_new(False))
        layout.set_attributes(attributes)
        for char in new + ["🧑‍🩰", "🧑🏽‍🩰", "👩🏽‍🦽‍➡️", "🏳️‍🌈"]:
            with self.subTest(emoji=char):
                layout.set_text(char, -1)
                self.assertEqual(layout.get_unknown_glyphs_count(), 0)
                run = layout.get_iter().get_run_readonly()
                self.assertEqual(run.glyphs.num_glyphs, 1)
                self.assertEqual(
                    run.item.analysis.font.describe().get_family(),
                    emoji_font.BUNDLED_FAMILY,
                )

    def test_switching_to_system_removes_the_bundled_font(self):
        emoji_font.create_font_map("noto")
        font_map, bundled = emoji_font.create_font_map("system")
        self.assertFalse(bundled)
        font = font_map.load_font(
            font_map.create_context(), Pango.FontDescription(emoji_font.BUNDLED_FAMILY)
        )
        self.assertNotEqual(font.describe().get_family(), emoji_font.BUNDLED_FAMILY)

    def test_missing_font_falls_back_instead_of_preventing_startup(self):
        emoji_font.create_font_map("system")
        with TemporaryDirectory() as directory:
            with patch.object(config, "static_dir", directory), patch("builtins.print"):
                font_map, bundled = emoji_font.create_font_map("noto")
        self.assertFalse(bundled)
        self.assertIsNotNone(font_map)
