import importlib
import os
from unittest import TestCase
from unittest.mock import patch

from emote import config


class VersionTests(TestCase):
    def tearDown(self):
        importlib.reload(config)

    def load_version(self, **environ):
        clean = {
            key: value
            for key, value in os.environ.items()
            if key not in ("EMOTE_VERSION", "SNAP_VERSION")
        }
        with patch.dict(os.environ, {**clean, **environ}, clear=True):
            return importlib.reload(config).version

    def test_launcher_version_is_preferred(self):
        self.assertEqual(
            self.load_version(EMOTE_VERSION="5.1.0", SNAP_VERSION="4.0"), "5.1.0"
        )

    def test_snap_version_is_used_without_launcher(self):
        self.assertEqual(self.load_version(SNAP_VERSION="5.1.0"), "5.1.0")

    def test_source_checkout_reports_dev_build(self):
        self.assertEqual(self.load_version(), "dev build")
