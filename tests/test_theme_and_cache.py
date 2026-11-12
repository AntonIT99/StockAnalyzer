import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import matplotlib
import pandas as pd

from stock_app import cache, theme
from stock_app.config import CACHE_TTLS


class ThemeTests(unittest.TestCase):
    def tearDown(self):
        theme.set_theme(theme.LIGHT)

    def test_light_theme_leaves_colours_unchanged(self):
        theme.set_theme(theme.LIGHT)
        for color in ("#111827", "#16a34a", "white", "#abcdef"):
            self.assertEqual(theme.themed(color), color)
        self.assertFalse(theme.is_dark())

    def test_dark_theme_swaps_surface_and_text_colours(self):
        theme.set_theme(theme.DARK)
        self.assertTrue(theme.is_dark())
        self.assertNotEqual(theme.themed("white"), "white")
        self.assertNotEqual(theme.themed("#111827"), "#111827")
        self.assertEqual(theme.themed("#111827"), theme.themed("#111827".upper()))
        self.assertEqual(theme.themed("#f97316"), "#f97316")

    def test_switching_back_restores_matplotlib_defaults(self):
        before = {key: matplotlib.rcParams[key] for key in ("figure.facecolor", "axes.facecolor", "text.color")}
        theme.set_theme(theme.DARK)
        self.assertEqual(theme.figure_background(), "#0f172a")
        self.assertNotEqual(matplotlib.rcParams["text.color"], before["text.color"])
        theme.set_theme(theme.LIGHT)
        for key, value in before.items():
            self.assertEqual(matplotlib.rcParams[key], value)

    def test_unknown_theme_name_falls_back_to_light(self):
        theme.set_theme("sepia")
        self.assertEqual(theme.current_theme(), theme.LIGHT)


class CachePruneTests(unittest.TestCase):
    def test_removes_only_cache_files_older_than_every_ttl(self):
        max_ttl = max(CACHE_TTLS.values())
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            fresh = cache_dir / "fresh.pkl"
            stale = cache_dir / "stale.pkl"
            other = cache_dir / "notes.txt"
            for path in (fresh, stale, other):
                path.write_bytes(b"x")
            old = (pd.Timestamp.now(tz="UTC") - max_ttl - pd.Timedelta(hours=2)).timestamp()
            os.utime(stale, (old, old))
            os.utime(other, (old, old))
            with mock.patch.object(cache, "CACHE_DIR", cache_dir):
                removed = cache.prune_expired_cache()
            self.assertEqual(removed, 1)
            self.assertTrue(fresh.exists())
            self.assertFalse(stale.exists())
            self.assertTrue(other.exists())

    def test_missing_cache_directory_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(cache, "CACHE_DIR", Path(directory) / "does-not-exist"):
                self.assertEqual(cache.prune_expired_cache(), 0)


if __name__ == "__main__":
    unittest.main()
