from collections import defaultdict
from pathlib import Path
import shelve
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from emote import emojis, user_data


class EmojiSearchTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        shelf = patch.object(
            user_data, "SHELVE_PATH", str(Path(directory.name) / "data")
        )
        shelf.start()
        self.addCleanup(shelf.stop)
        for name, value in (
            ("all_emojis", []),
            ("emojis_by_category", defaultdict(list)),
        ):
            catalogue = patch.object(emojis, name, value)
            catalogue.start()
            self.addCleanup(catalogue.stop)
        emojis.init()

    def test_existing_users_start_without_invented_usage_counts(self):
        with shelve.open(user_data.SHELVE_PATH) as db:
            db[user_data.RECENT_EMOJIS] = ["🚀", "🙂"]
            db[user_data.SKINTONE_INDEX] = 3

        self.assertEqual(user_data.load_emoji_usage_counts(), {})
        user_data.update_recent_emojis("🚀")

        self.assertEqual(user_data.load_emoji_usage_counts(), {"🚀": 1})
        self.assertEqual(user_data.load_recent_emojis(), ["🚀", "🙂"])
        self.assertEqual(user_data.load_skintone_index(), 3)

    def test_counts_persist_and_combine_skin_tones_and_qualified_variants(self):
        for char in ("✌", "✌️", "✌🏽", "✌🏿"):
            user_data.update_recent_emojis(char)

        self.assertEqual(user_data.load_emoji_usage_counts(), {"✌": 4})

    def test_usage_counts_survive_leaving_recent_history(self):
        user_data.update_recent_emojis("🚀")
        for emoji in emojis.all_emojis[: user_data.MAX_RECENT_EMOJIS]:
            user_data.update_recent_emojis(emoji["char"])

        self.assertNotIn("🚀", user_data.load_recent_emojis())
        self.assertEqual(user_data.load_emoji_usage_counts()["🚀"], 1)

    def test_unused_results_keep_catalogue_order(self):
        expected = [
            emoji
            for emoji in emojis.all_emojis
            if "rocket" in emoji["keywords"] or "rocket" in emoji["name"].lower()
        ]
        self.assertGreater(len(expected), 1)
        self.assertEqual(emojis.search("ROCKET"), expected)

    def test_search_ranks_by_frequency_rather_than_recency(self):
        user_data.update_recent_emojis("🚀")
        user_data.update_recent_emojis("🚀")
        user_data.update_recent_emojis("🧑‍🚀")

        results = emojis.search("rocket")

        self.assertEqual(user_data.load_recent_emojis()[0], "🧑‍🚀")
        self.assertEqual([emoji["char"] for emoji in results[:2]], ["🚀", "🧑‍🚀"])

    def test_equal_counts_keep_catalogue_order_and_do_not_reorder_categories(self):
        original = list(emojis.all_emojis)
        matches = emojis.search("rocket")
        for emoji in reversed(matches):
            user_data.update_recent_emojis(emoji["char"])

        self.assertEqual(emojis.search("rocket"), matches)
        self.assertEqual(emojis.all_emojis, original)

    def test_skin_tone_usage_promotes_base_emoji_in_search(self):
        user_data.update_recent_emojis("👩🏽‍🚀")

        self.assertEqual(emojis.search("rocket")[0]["char"], "👩‍🚀")

    def test_frequently_used_emoji_must_still_match_query(self):
        user_data.update_recent_emojis("🚀")

        self.assertNotIn("🚀", [emoji["char"] for emoji in emojis.search("cat")])
        self.assertEqual(emojis.search("no such emoji 123456"), [])
