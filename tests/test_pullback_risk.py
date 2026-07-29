import unittest

import pandas as pd

from stock_app.technical import TechnicalAnalysisMixin


class PullbackRiskTests(unittest.TestCase):
    def test_atr_extension_calculation_and_missing_values(self):
        self.assertAlmostEqual(
            TechnicalAnalysisMixin.calculate_atr_extension(110, 100, 4),
            2.5,
        )
        self.assertAlmostEqual(
            TechnicalAnalysisMixin.calculate_atr_extension(94, 100, 4),
            -1.5,
        )
        self.assertIsNone(TechnicalAnalysisMixin.calculate_atr_extension(110, 100, 0))
        self.assertIsNone(TechnicalAnalysisMixin.calculate_atr_extension(110, None, 4))

    def test_macd_histogram_falling_for_three_bars(self):
        state = TechnicalAnalysisMixin.calculate_macd_histogram_state(
            pd.Series([1.0, 0.8, 0.5, 0.1])
        )
        self.assertEqual(state["direction"], "Falling")
        self.assertTrue(state["falling_3_bars"])

    def test_rsi_and_macd_bearish_divergence(self):
        close = pd.Series([90.0] * 19 + [100.0, 101.0])
        rsi = pd.Series([60.0] * 19 + [80.0, 74.0])
        histogram = pd.Series([0.5] * 19 + [2.0, 1.0])
        self.assertTrue(
            TechnicalAnalysisMixin.detect_bearish_divergence(close, rsi, 5)
        )
        self.assertTrue(
            TechnicalAnalysisMixin.detect_bearish_divergence(close, histogram)
        )

    def test_bollinger_breakout_failure(self):
        self.assertTrue(
            TechnicalAnalysisMixin.detect_bollinger_breakout_failure(
                pd.Series([11.0, 9.5]),
                pd.Series([10.0, 10.0]),
                pd.Series([8.0, 8.0]),
            )
        )

    def test_low_volume_new_high(self):
        close = pd.Series(list(range(20)) + [21])
        rvol = pd.Series([1.0] * 20 + [0.58])
        self.assertTrue(TechnicalAnalysisMixin.detect_low_volume_new_high(close, rvol))

    def test_spike_rejection_candle(self):
        data = pd.DataFrame({
            "Open": [10.0] * 20 + [18.0],
            "High": list(range(1, 21)) + [22.0],
            "Low": [9.0] * 20 + [17.0],
            "Close": [10.0] * 20 + [18.5],
        })
        self.assertTrue(TechnicalAnalysisMixin.detect_spike_rejection_candle(data))
        data.loc[data.index[-1], "Close"] = data.loc[data.index[-1], "Open"]
        self.assertFalse(TechnicalAnalysisMixin.detect_spike_rejection_candle(data))

    def test_category_caps_and_total_score_boundaries(self):
        all_risks = {
            "atr_extension": 4.0,
            "rsi_above_80": True,
            "rsi_falling_above_70": True,
            "macd_histogram_falling_3_bars": True,
            "rsi_bearish_divergence": True,
            "macd_bearish_divergence": True,
            "low_volume_new_high": True,
            "rising_price_low_volume": True,
            "bollinger_breakout_failure": True,
            "spike_rejection_candle": True,
            "failed_previous_high": True,
            "current_rvol": 0.5,
        }
        result = TechnicalAnalysisMixin.calculate_pullback_risk(all_risks)
        self.assertEqual(result["categories"]["momentum_exhaustion"], 30)
        self.assertEqual(result["categories"]["participation_risk"], 20)
        self.assertEqual(result["categories"]["reversal_signals"], 25)
        self.assertGreater(result["raw_categories"]["momentum_exhaustion"], 30)
        self.assertEqual(
            result["details"]["price_extension"][0]["points"],
            25,
        )
        self.assertEqual(
            sum(metric["points"] for metric in result["details"]["reversal_signals"]),
            40,
        )
        self.assertEqual(result["score"], 100.0)
        self.assertEqual(
            TechnicalAnalysisMixin.calculate_pullback_risk({})["score"],
            0.0,
        )

    def test_risk_label_boundaries(self):
        cases = {
            24: "Low",
            25: "Moderate",
            49: "Moderate",
            50: "Elevated",
            69: "Elevated",
            70: "High",
        }
        for score, expected in cases.items():
            with self.subTest(score=score):
                self.assertEqual(
                    TechnicalAnalysisMixin.classify_pullback_risk(score),
                    expected,
                )

    def test_insufficient_history_returns_false_without_risk(self):
        short = pd.Series([1.0, 2.0, 3.0])
        self.assertFalse(
            TechnicalAnalysisMixin.detect_bearish_divergence(short, short)
        )
        self.assertFalse(
            TechnicalAnalysisMixin.detect_low_volume_new_high(
                short,
                pd.Series([0.5, 0.5, 0.5]),
            )
        )
        indicators = TechnicalAnalysisMixin.calculate_pullback_indicators(
            pd.DataFrame({"Close": short})
        )
        self.assertEqual(
            TechnicalAnalysisMixin.calculate_pullback_risk(indicators)["score"],
            0.0,
        )

    def test_high_risk_does_not_turn_strongly_bullish_score_bearish(self):
        description = TechnicalAnalysisMixin.describe_technical_score_with_risk(90, 90)
        self.assertEqual(description, "Bullish Trend — High Pullback Risk")
        self.assertIn("Bullish", description)
        self.assertEqual(
            TechnicalAnalysisMixin.describe_technical_score_with_risk(90, 39),
            "Strongly Bullish",
        )
        self.assertEqual(
            TechnicalAnalysisMixin.describe_technical_score_with_risk(90, 40),
            "Bullish but Extended",
        )
        self.assertEqual(
            TechnicalAnalysisMixin.describe_technical_score_with_risk(70, 50),
            "Bullish with Elevated Risk",
        )

    def test_general_assessment_uses_category_subscores(self):
        aligned = {
            name: {"percentage": 85.0}
            for name in ("trend", "momentum", "setup", "confirmation")
        }
        weak_confirmation = {
            **{
                name: {"percentage": 100.0}
                for name in ("trend", "momentum", "setup")
            },
            "confirmation": {"percentage": 25.0},
        }
        aligned_assessment = TechnicalAnalysisMixin.describe_category_aware_assessment(
            85,
            aligned,
            20,
        )
        mixed_assessment = TechnicalAnalysisMixin.describe_category_aware_assessment(
            85,
            weak_confirmation,
            20,
        )
        self.assertEqual(aligned_assessment, "Strongly Bullish")
        self.assertEqual(mixed_assessment, "Bullish — Confirmation Weak")
        self.assertNotEqual(aligned_assessment, mixed_assessment)

    def test_general_assessment_preserves_friendly_trend_context(self):
        categories = {
            "trend": {"percentage": 40.0},
            "momentum": {"percentage": 80.0},
            "setup": {"percentage": 60.0},
            "confirmation": {"percentage": 40.0},
        }
        assessment = TechnicalAnalysisMixin.describe_category_aware_assessment(
            55,
            categories,
            20,
            trend_context_label="Early Recovery",
        )
        self.assertEqual(
            assessment,
            "Early Recovery — Trend & Confirmation Weak",
        )


if __name__ == "__main__":
    unittest.main()
