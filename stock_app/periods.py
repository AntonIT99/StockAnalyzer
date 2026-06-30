"""Period, interval, and lookback selection rules."""

from .config import CUSTOM_PERIOD, INTERVAL_DURATIONS, INTERVAL_MAX_LOOKBACKS, INTERVAL_OPTIONS, PERIOD_DURATIONS, PERIOD_OPTIONS

class PeriodSelectionMixin:
    def get_allowed_intervals_for_current_period(self):
        allowed_intervals = self.get_allowed_intervals(
            self.get_interval_rule_period(),
            self.get_interval_rule_period_duration()
        )
        if self.period_var.get() != CUSTOM_PERIOD:
            return allowed_intervals
        try:
            visible_start, _visible_end = self.get_custom_visible_window()
        except ValueError:
            return allowed_intervals
        return [
            interval
            for interval in allowed_intervals
            if self.is_interval_within_yfinance_lookback(interval, visible_start)
        ]

    @classmethod
    def get_allowed_intervals(cls, period, period_duration=None):
        if period_duration is None:
            period_duration = PERIOD_DURATIONS.get(period)
        return [
            interval
            for interval in INTERVAL_OPTIONS
            if cls.is_interval_allowed_for_period(interval, period_duration)
        ]

    @staticmethod
    def is_interval_allowed_for_period(interval, period_duration):
        max_lookback = INTERVAL_MAX_LOOKBACKS[interval]
        if period_duration is None:
            return max_lookback is None
        if INTERVAL_DURATIONS[interval] >= period_duration:
            return False
        return max_lookback is None or period_duration < max_lookback

    @classmethod
    def is_interval_within_yfinance_lookback(cls, interval, visible_start):
        max_lookback = INTERVAL_MAX_LOOKBACKS[interval]
        if max_lookback is None:
            return True
        oldest_allowed_start = cls.host_now() - max_lookback
        return visible_start >= oldest_allowed_start

    def get_interval_rule_period(self):
        if self.period_var.get() != CUSTOM_PERIOD:
            return self.period_var.get()
        custom_duration = self.get_custom_period_duration(default_period="6mo")
        return self.get_smallest_covering_standard_period(custom_duration)

    def get_interval_rule_period_duration(self):
        return PERIOD_DURATIONS.get(self.get_interval_rule_period())

    @staticmethod
    def get_smallest_covering_standard_period(period_duration):
        for period in PERIOD_OPTIONS:
            standard_duration = PERIOD_DURATIONS.get(period)
            if standard_duration is not None and period_duration <= standard_duration:
                return period
        return "max"
