import unittest

import numpy as np
import pandas as pd

from stock_app.data import MarketDataMixin
from stock_app.ohlcv import mark_volume_completion, resample_ohlcv
from stock_app.technical import TechnicalAnalysisMixin as T


def prices():
    close = 100 + np.arange(240) * 0.05 + np.sin(np.arange(240)) * 0.1
    return pd.DataFrame({
        "Open": close, "High": close + 2, "Low": close - 2,
        "Close": close, "Volume": 100.0,
    }, index=pd.date_range("2025-01-01", periods=240))


class VolumeScoringTests(unittest.TestCase):
    def test_volume_baseline_excludes_current_bar_and_zero_baseline(self):
        data = pd.DataFrame({"Volume": [100.0] * 20 + [1000.0]})
        result = T.calculate_volume_indicators(data)
        self.assertEqual(result["VOLUME_SMA20"].iloc[-1], 100)
        self.assertEqual(result["RVOL20"].iloc[-1], 10)
        self.assertTrue(pd.isna(result["RVOL20"].iloc[19]))
        result = T.calculate_volume_indicators(pd.DataFrame({"Volume": [0.0] * 21}))
        self.assertTrue(pd.isna(result["RVOL20"].iloc[-1]))

    def test_volume_only_changes_one_confirmation_point(self):
        data = prices()
        low = T.calculate_bullish_structure_score(T.add_indicators(data.copy()))
        data.iloc[-1, data.columns.get_loc("Volume")] = 150
        high = T.calculate_bullish_structure_score(T.add_indicators(data.copy()))
        self.assertEqual(low["quality_score"], high["quality_score"])
        self.assertEqual(high["quality_max"], 3)
        self.assertEqual(high["confirmation_max"], 4)
        self.assertEqual(high["confirmation_score"] - low["confirmation_score"], 1)

    def test_partial_bar_uses_previous_completed_volume_and_price(self):
        data = prices()
        data.iloc[-2, data.columns.get_loc("Volume")] = 150
        data["VOLUME_COMPLETE"] = True
        data.iloc[-1, data.columns.get_loc("VOLUME_COMPLETE")] = False
        data.iloc[-1, data.columns.get_loc("Volume")] = 1
        indicators = T.add_indicators(data.copy())
        self.assertTrue(T.volume_confirmation(indicators))
        summary = T.calculate_daily_structural_summary(indicators)
        self.assertTrue(summary["volume_provisional"])
        self.assertEqual(summary["daily_rvol20"], 1.5)
        self.assertLess(summary["live_rvol20"], 0.02)
        self.assertEqual(summary["volume_scored_as_of"], str(data.index[-2]))
        risks = T.calculate_pullback_indicators(indicators)
        self.assertFalse(risks["rising_price_low_volume"])
        self.assertFalse(risks["low_volume_new_high"])

    def test_confirmation_does_not_reuse_missing_volume(self):
        data = T.add_indicators(prices())
        data.iloc[-1, data.columns.get_loc("RVOL20")] = np.nan
        self.assertIsNone(T.volume_confirmation(data))

    def test_no_completed_volume_does_not_create_confirmation(self):
        data = prices()
        data["VOLUME_COMPLETE"] = False
        data = T.add_indicators(data)
        self.assertIsNone(T.volume_confirmation(data))
        self.assertTrue(data["RVOL20"].isna().all())
        self.assertFalse(T.calculate_pullback_indicators(data)["low_volume_new_high_available"])

    def test_partial_volume_cannot_enter_future_baselines(self):
        data = pd.DataFrame({"Volume": [100.0] * 20 + [10000.0, 200.0]})
        data["VOLUME_COMPLETE"] = True
        data.loc[20, "VOLUME_COMPLETE"] = False
        result = T.calculate_volume_indicators(data)
        self.assertEqual(result["VOLUME_SMA20"].iloc[-1], 100)
        self.assertEqual(result["RVOL20"].iloc[-1], 2)

    def test_daily_structural_baseline_matches_regular_indicators(self):
        data = prices()
        self.assertTrue(T.add_indicators(data.copy())["RVOL20"].equals(
            T.add_daily_structural_indicators(data)["DAILY_RVOL20"]))

    def test_completion_boundaries(self):
        cases = [
            ("1d", "2026-10-16", "2026-10-16 23:00", False),
            ("1d", "2026-10-16", "2026-10-17", True),
            ("1wk", "2026-10-12", "2026-10-16", False),
            ("1wk", "2026-10-12", "2026-10-19", True),
            ("1mo", "2026-10-01", "2026-10-31", False),
            ("3mo", "2026-10-01", "2027-01-01", True),
            ("6mo", "2026-10-16", "2026-11-01", False),
            ("1y", "2026-10-16", "2027-01-01", True),
            ("1h", "2026-10-16 15:30", "2026-10-16 16:00", False),
            ("15m", "2026-10-16 15:30", "2026-10-16 15:45", True),
        ]
        for interval, date, now, expected in cases:
            with self.subTest(interval=interval, now=now):
                result = mark_volume_completion(pd.DataFrame({"Volume": [100]}, index=[pd.Timestamp(date)]), interval, pd.Timestamp(now))
                self.assertEqual(bool(result["VOLUME_COMPLETE"].iloc[-1]), expected)

    def test_fallback_preserves_daily_data_and_fills_missing_bars(self):
        data = prices().iloc[-2:].copy()
        original = data.copy()
        hourly = pd.concat([data.tail(1), data.tail(1).rename(index=lambda x: x + pd.Timedelta(days=1))])
        hourly["Volume"] = 20
        app = type("App", (MarketDataMixin,), {
            "download_recent_intraday_for_daily_fallback": lambda self, ticker: hourly,
            "resample_ohlcv": staticmethod(resample_ohlcv),
            "is_missing_value": staticmethod(pd.isna),
        })()
        result = app.append_missing_daily_bars_from_intraday("TEST", data)
        pd.testing.assert_frame_equal(result.loc[original.index], original, check_freq=False)
        self.assertEqual(result["Volume"].iloc[-1], 20)

    def test_resampling_preserves_completion_boundary_for_relabelled_bar(self):
        data = prices()
        for rule, interval in [("6ME", "6mo"), ("YE", "1y")]:
            with self.subTest(rule=rule):
                result = resample_ohlcv(data, rule)
                self.assertEqual(result.index[-1], data.index[-1])
                boundary = result["VOLUME_PERIOD_END"].iloc[-1] + pd.Timedelta(days=1)
                before = mark_volume_completion(result, interval, boundary - pd.Timedelta(hours=1))
                after = mark_volume_completion(result, interval, boundary)
                self.assertFalse(before["VOLUME_COMPLETE"].iloc[-1])
                self.assertTrue(after["VOLUME_COMPLETE"].iloc[-1])


if __name__ == "__main__":
    unittest.main()
