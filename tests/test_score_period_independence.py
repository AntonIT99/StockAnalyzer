import unittest

import numpy as np
import pandas as pd

from stock_app.data import MarketDataMixin
from stock_app.technical import TechnicalAnalysisMixin


class Analyzer(TechnicalAnalysisMixin, MarketDataMixin):
    pass


SCORE_KEYS = (
    "weighted_technical_score",
    "daily_trend_score",
    "daily_trend_score_trend",
    "daily_trend_score_momentum",
    "daily_trend_score_momentum_max",
    "daily_trend_score_quality",
    "daily_trend_score_quality_max",
    "confirmation_score",
    "confirmation_max",
    "pullback_risk_score",
    "pullback_risk_categories",
    "overall_description",
)


def history_with_failed_high() -> pd.DataFrame:
    """Uptrend whose last bar trades above the 20-bar high and closes below it."""
    bars = 300
    close = 100 + np.arange(bars) * 0.2 + np.sin(np.arange(bars) / 3.0)
    data = pd.DataFrame({
        "Open": close - 0.1,
        "High": close + 0.5,
        "Low": close - 0.5,
        "Close": close,
        "Volume": 1000.0,
    }, index=pd.date_range("2024-01-01", periods=bars))
    previous_high = data["High"].iloc[-21:-1].max()
    last = data.index[-1]
    data.loc[last, ["Open", "High", "Low", "Close"]] = [
        previous_high - 1.0,
        previous_high + 3.0,
        previous_high - 2.0,
        previous_high - 1.5,
    ]
    return Analyzer.add_indicators(data)


class ScorePeriodIndependenceTests(unittest.TestCase):
    def setUp(self):
        self.data = history_with_failed_high()
        self.short_start = self.data.index[-5]
        self.long_start = self.data.index[-200]

    def summary(self, period_start):
        return Analyzer.calculate_signal_summary(
            self.data,
            period_start_as_of=period_start,
            interval="1d",
        )

    def test_fixture_depends_on_twenty_bar_history(self):
        full = Analyzer.calculate_daily_structural_summary(self.data, interval="1d")
        trimmed = Analyzer.calculate_daily_structural_summary(self.data.iloc[-5:], interval="1d")
        self.assertGreater(full["pullback_risk_categories"]["reversal_signals"], 0)
        self.assertEqual(trimmed["pullback_risk_categories"]["reversal_signals"], 0)

    def test_scores_do_not_depend_on_visible_period(self):
        short = self.summary(self.short_start)
        long = self.summary(self.long_start)
        for key in SCORE_KEYS:
            self.assertEqual(short[key], long[key], key)
        self.assertGreater(short["pullback_risk_categories"]["reversal_signals"], 0)

    def test_scores_match_full_history_scoring(self):
        expected = Analyzer.calculate_daily_structural_summary(self.data, interval="1d")
        short = self.summary(self.short_start)
        for key in ("weighted_technical_score", "pullback_risk_score", "confirmation_max"):
            self.assertEqual(short[key], expected[key], key)

    def test_period_price_figures_follow_visible_period(self):
        short = self.summary(self.short_start)
        long = self.summary(self.long_start)
        self.assertEqual(short["period_start_price"], self.data["Close"].iloc[-5])
        self.assertEqual(long["period_start_price"], self.data["Close"].iloc[-200])
        self.assertNotEqual(short["period_change"], long["period_change"])
        self.assertEqual(short["period_end_price"], long["period_end_price"])

    def test_period_start_baseline_uses_history_before_the_period(self):
        short = self.summary(self.short_start)
        baseline = Analyzer.calculate_daily_structural_summary(self.data.iloc[:-4], interval="1d")
        current = Analyzer.calculate_daily_structural_summary(self.data, interval="1d")
        self.assertEqual(
            short["score_changes_period_start"],
            Analyzer.build_score_change_rows(current, baseline),
        )
        self.assertEqual(baseline["confirmation_max"], current["confirmation_max"])

    def test_as_of_excludes_later_bars_from_scores_and_period(self):
        as_of = self.data.index[-1]
        cut = Analyzer.calculate_signal_summary(
            self.data,
            daily_summary_as_of=as_of,
            period_start_as_of=self.short_start,
            interval="1d",
        )
        expected = Analyzer.calculate_daily_structural_summary(self.data.iloc[:-1], interval="1d")
        self.assertEqual(cut["current_price"], self.data["Close"].iloc[-2])
        self.assertEqual(cut["period_end_price"], self.data["Close"].iloc[-2])
        self.assertEqual(cut["weighted_technical_score"], expected["weighted_technical_score"])
        self.assertEqual(cut["pullback_risk_score"], expected["pullback_risk_score"])


if __name__ == "__main__":
    unittest.main()
