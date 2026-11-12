import unittest

import numpy as np
import pandas as pd

from stock_app.config import TECHNICAL_SCORE_WEIGHTS, TREND_STRUCTURE_SCORE_MAX
from stock_app.technical import TechnicalAnalysisMixin as T


def uptrend(bars: int) -> pd.DataFrame:
    close = 100 + np.arange(bars) * 0.3 + np.sin(np.arange(bars) / 4.0) * 0.4
    data = pd.DataFrame({
        "Open": close - 0.1,
        "High": close + 0.6,
        "Low": close - 0.6,
        "Close": close,
        "Volume": 1000.0 + 50 * np.cos(np.arange(bars) / 3.0),
    }, index=pd.date_range("2024-01-01", periods=bars))
    return T.add_indicators(data)


class WeightRenormalizationTests(unittest.TestCase):
    def test_unscored_category_passes_its_weight_to_the_others(self):
        result = T.calculate_weighted_technical_score(15, 6, 3, None, confirmation_max=0)
        categories = result["categories"]
        self.assertAlmostEqual(result["score"], 100.0)
        self.assertFalse(categories["confirmation"]["active"])
        self.assertEqual(categories["confirmation"]["contribution"], 0.0)
        self.assertAlmostEqual(
            categories["trend"]["effective_weight"],
            TECHNICAL_SCORE_WEIGHTS["trend"] / (1 - TECHNICAL_SCORE_WEIGHTS["confirmation"]),
        )
        self.assertAlmostEqual(sum(c["effective_weight"] for c in categories.values()), 1.0)

    def test_all_categories_scored_keeps_the_configured_weights(self):
        result = T.calculate_weighted_technical_score(9, 3, 2, 1)
        for name, category in result["categories"].items():
            self.assertTrue(category["active"])
            self.assertEqual(category["effective_weight"], TECHNICAL_SCORE_WEIGHTS[name])
        self.assertEqual(T.calculate_weighted_technical_score(15, 6, 3, 4)["score"], 100.0)

    def test_scored_category_with_zero_points_still_counts(self):
        result = T.calculate_weighted_technical_score(15, 6, 3, 0)
        self.assertTrue(result["categories"]["confirmation"]["active"])
        self.assertAlmostEqual(result["score"], 80.0)

    def test_nothing_scored_gives_zero_without_dividing_by_zero(self):
        result = T.calculate_weighted_technical_score(None, None, None, None, 0, 0, 0, 0)
        self.assertEqual(result["score"], 0.0)

    def test_assessment_does_not_call_an_unscored_category_weak(self):
        categories = T.calculate_weighted_technical_score(15, 6, 3, None, confirmation_max=0)["categories"]
        assessment = T.describe_category_aware_assessment(100.0, categories, 0)
        self.assertNotIn("Confirmation", assessment)
        self.assertNotIn("Weak", assessment)


class MissingTrendLayerTests(unittest.TestCase):
    def test_layer_without_history_is_left_out_of_the_maximum(self):
        score = T.calculate_bullish_structure_score(uptrend(150))
        self.assertIsNone(score["long_term_trend_score"])
        self.assertEqual(score["short_term_trend_score"], 5)
        self.assertEqual(score["medium_term_trend_score"], 5)
        self.assertEqual(score["trend_max"], 10)
        self.assertEqual(score["trend_score"], 10)
        trend = score["weighted_contributions"]["trend"]
        self.assertEqual(trend["max_points"], 10)
        self.assertAlmostEqual(trend["percentage"], 100.0)
        self.assertEqual(score["max_score"], 10 + score["momentum_max"] + score["quality_max"])

    def test_summary_reports_the_reduced_trend_maximum(self):
        summary = T.calculate_daily_structural_summary(uptrend(150), interval="1d")
        self.assertEqual(summary["daily_trend_score_trend_max"], 10)
        self.assertEqual(summary["daily_trend_score_trend"], 10)

    def test_full_history_keeps_the_fifteen_point_scale(self):
        score = T.calculate_bullish_structure_score(uptrend(320))
        self.assertIsNotNone(score["long_term_trend_score"])
        self.assertEqual(score["trend_max"], TREND_STRUCTURE_SCORE_MAX)
        self.assertEqual(score["weighted_contributions"]["trend"]["max_points"], TREND_STRUCTURE_SCORE_MAX)


class InvestmentViewTests(unittest.TestCase):
    def test_no_verdict_without_fundamentals(self):
        self.assertEqual(T.calculate_investment_view("Unknown", "Unknown", "Strongly Bullish"), "N/A")
        self.assertEqual(T.calculate_investment_view("Unknown", "Cheap", "Bearish"), "N/A")

    def test_verdicts_with_fundamentals_are_unchanged(self):
        self.assertEqual(T.calculate_investment_view("Strong", "Cheap", "Bullish"), "Attractive")
        self.assertEqual(T.calculate_investment_view("Strong", "Cheap", "Bearish"), "Watchlist")
        self.assertEqual(T.calculate_investment_view("Weak", "Unknown", "Bearish"), "Risky")
        self.assertEqual(T.calculate_investment_view("Stable", "Fair", "Bullish"), "Watchlist")


if __name__ == "__main__":
    unittest.main()
