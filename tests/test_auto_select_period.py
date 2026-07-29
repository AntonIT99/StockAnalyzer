import unittest

from stock_app.config import AUTO_SELECT_PERIOD, AUTO_SELECT_PERIODS_BY_INTERVAL
from stock_app.periods import PeriodSelectionMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class AutoSelectPeriodTests(unittest.TestCase):
    def test_resolves_the_configured_period_for_each_interval(self):
        for interval, expected_period in AUTO_SELECT_PERIODS_BY_INTERVAL.items():
            app = type("App", (PeriodSelectionMixin,), {
                "period_var": Value(AUTO_SELECT_PERIOD),
                "interval_var": Value(interval),
            })()
            self.assertEqual(app.get_effective_period(), expected_period)
            self.assertEqual(app.get_interval_rule_period(), expected_period)

    def test_auto_select_offers_every_configured_interval(self):
        app = type("App", (PeriodSelectionMixin,), {
            "period_var": Value(AUTO_SELECT_PERIOD),
            "interval_var": Value("1d"),
        })()
        self.assertEqual(app.get_allowed_intervals_for_current_period(), list(AUTO_SELECT_PERIODS_BY_INTERVAL))


if __name__ == "__main__":
    unittest.main()
