import unittest

from stock_app.config import TECHNICAL_SCORE_WEIGHTS
from stock_app.technical import TechnicalAnalysisMixin


class WeightedTechnicalScoreTests(unittest.TestCase):
    def test_weights_add_up_to_one(self):
        self.assertAlmostEqual(sum(TECHNICAL_SCORE_WEIGHTS.values()), 1.0)

    def test_normalizes_different_category_maximums_and_contributions(self):
        result = TechnicalAnalysisMixin.calculate_weighted_technical_score(15, 3, 2, 1)
        self.assertAlmostEqual(result["categories"]["trend"]["percentage"], 100.0)
        self.assertAlmostEqual(result["categories"]["trend"]["contribution"], 40.0)
        self.assertAlmostEqual(result["categories"]["setup"]["percentage"], 200 / 3)
        self.assertAlmostEqual(result["categories"]["setup"]["contribution"], 10.0)
        self.assertAlmostEqual(result["categories"]["confirmation"]["contribution"], 20 / 3)
        self.assertAlmostEqual(result["score"], 81 + 2 / 3)

    def test_zero_maximum_does_not_divide_by_zero(self):
        result = TechnicalAnalysisMixin.calculate_weighted_category_score(0, 0, 0.4)
        self.assertEqual(result, {"percentage": 0.0, "contribution": 0.0})
        inactive = TechnicalAnalysisMixin.calculate_weighted_category_score(None, 0, 0.4)
        self.assertEqual(inactive, {"percentage": 0.0, "contribution": 0.0})

    def test_classification_boundaries(self):
        cases = {
            100: "Strongly Bullish",
            80: "Strongly Bullish",
            79.999: "Bullish",
            65: "Bullish",
            64.999: "Neutral / Mixed",
            45: "Neutral / Mixed",
            44.999: "Bearish",
            30: "Bearish",
            29.999: "Strongly Bearish",
            0: "Strongly Bearish",
        }
        for score, expected in cases.items():
            with self.subTest(score=score):
                self.assertEqual(
                    TechnicalAnalysisMixin.classify_weighted_technical_score(score),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
