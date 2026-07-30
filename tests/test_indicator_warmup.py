import unittest

import pandas as pd

from stock_app.data import MarketDataMixin


class IndicatorWarmupTests(unittest.TestCase):
    def test_hourly_download_uses_explicit_date_range(self):
        self.assertIsNone(MarketDataMixin.get_intraday_download_period("1h", "2mo"))

    def test_hourly_download_includes_sma200_warmup(self):
        visible_start = pd.Timestamp("2026-06-01 12:00")

        download_start = MarketDataMixin.get_download_start(visible_start, "1h")

        self.assertEqual(download_start, pd.Timestamp("2026-04-02 12:00"))

    def test_shorter_intraday_intervals_keep_their_provider_period(self):
        self.assertEqual(MarketDataMixin.get_intraday_download_period("15m", "2wk"), "60d")


if __name__ == "__main__":
    unittest.main()
