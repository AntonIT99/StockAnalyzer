"""Technical indicators, scoring, and signal summary calculations."""

from typing import Any
import pandas as pd
from .config import ATR_PCT_HEALTHY_MAX, ATR_PCT_HEALTHY_MIN, BULLISH_STRUCTURE_SCORE_MAX, CONFIRMATION_SCORE_MAX, EXTENDED_BULLISH_SCORE_MAX

class TechnicalAnalysisMixin:
    @staticmethod
    def latest_valid_value(series):
        values = series.dropna()
        if values.empty:
            return None
        return values.iloc[-1]

    @staticmethod
    def previous_valid_value(series):
        values = series.dropna()
        if len(values) < 2:
            return None
        return values.iloc[-2]

    @staticmethod
    def is_valid_number(value: Any) -> bool:
        return value is not None and not pd.isna(value)

    @staticmethod
    def first_available_series(data: pd.DataFrame, *columns: str) -> pd.Series:
        for column in columns:
            if column in data.columns:
                return data[column]
        return pd.Series(dtype=float)

    @classmethod
    def greater_than(cls, left: float | None, right: float | None) -> bool | None:
        if not cls.is_valid_number(left) or not cls.is_valid_number(right):
            return None
        return left > right

    @staticmethod
    def score_optional_checks(checks: list[bool | None], max_score: int, min_valid: int = 1) -> int | None:
        valid_checks = [check for check in checks if check is not None]
        if len(valid_checks) < min_valid:
            return None
        passed = sum(1 for check in valid_checks if check)
        return int((passed / len(valid_checks) * max_score) + 0.5)

    @staticmethod
    def classify_trend_layer_score(score: int | None) -> str:
        if score is None:
            return "N/A"
        if score <= 1:
            return "Bearish"
        if score == 2:
            return "Slightly Bearish"
        if score == 3:
            return "Mixed"
        if score == 4:
            return "Bullish"
        return "Strongly Bullish"

    @staticmethod
    def trend_layer_is_bullish(score: int | None) -> bool:
        return score is not None and score >= 4

    @staticmethod
    def trend_layer_is_bearish(score: int | None) -> bool:
        return score is not None and score <= 2

    @classmethod
    def calculate_weighted_trend_score(
        cls,
        short_term_score: int | None,
        medium_term_score: int | None,
        long_term_score: int | None
    ) -> int | None:
        if short_term_score is None and medium_term_score is None and long_term_score is None:
            return None
        short_term = 3 if short_term_score is None else short_term_score
        medium_term = 3 if medium_term_score is None else medium_term_score
        long_term = 3 if long_term_score is None else long_term_score
        weighted_score = (
            (short_term / 5) * 2
            + (medium_term / 5) * 3
            + (long_term / 5) * 3
        )
        return int(weighted_score + 0.5)

    @classmethod
    def classify_trend_phase(
        cls,
        short_term_score: int | None,
        medium_term_score: int | None,
        long_term_score: int | None
    ) -> str:
        short_bullish = cls.trend_layer_is_bullish(short_term_score)
        medium_bullish = cls.trend_layer_is_bullish(medium_term_score)
        long_bullish = cls.trend_layer_is_bullish(long_term_score)
        short_bearish = cls.trend_layer_is_bearish(short_term_score)
        medium_bearish = cls.trend_layer_is_bearish(medium_term_score)
        long_bearish = cls.trend_layer_is_bearish(long_term_score)
        if short_bullish and medium_bullish and long_bullish:
            return "Confirmed Uptrend"
        if short_bearish and medium_bearish and long_bearish:
            return "Confirmed Downtrend"
        if short_bullish and medium_bearish and long_bearish:
            return "Early Recovery"
        if short_bullish and medium_term_score is not None and medium_term_score >= 3 and long_bearish:
            return "Recovery Attempt"
        if short_bearish and long_bullish:
            return "Pullback"
        return "Mixed / Transition"

    @classmethod
    def is_strongly_bearish_setup(
        cls,
        short_term_score: int | None,
        medium_term_score: int | None,
        long_term_score: int | None,
        momentum_score: int | None = None,
        trend_direction: str | None = None,
        confirmation_score: int | None = None
    ) -> bool:
        long_bearish = cls.trend_layer_is_bearish(long_term_score)
        medium_bearish = cls.trend_layer_is_bearish(medium_term_score)
        short_bearish_or_deteriorating = (
            cls.trend_layer_is_bearish(short_term_score)
            or trend_direction == "Deteriorating"
        )
        momentum_weak = momentum_score is not None and momentum_score <= 1
        confirmation_weak = confirmation_score is None or confirmation_score <= 1
        return (
            long_bearish
            and medium_bearish
            and short_bearish_or_deteriorating
            and momentum_weak
            and confirmation_weak
        )

    @classmethod
    def refine_trend_label_with_direction(
        cls,
        label: str,
        trend_phase: str,
        trend_direction: str,
        short_term_score: int | None,
        medium_term_score: int | None,
        long_term_score: int | None
    ) -> str:
        if label == "N/A":
            return label
        recovery_phase = trend_phase in {"Early Recovery", "Recovery Attempt"}
        if recovery_phase and trend_direction != "Deteriorating":
            return trend_phase
        if "Bearish" in label and trend_direction == "Improving":
            return "Bearish, Improving"
        if label == "Mixed":
            return "Neutral / Transition"
        if (
            cls.trend_layer_is_bullish(short_term_score)
            and cls.trend_layer_is_bearish(long_term_score)
            and not cls.trend_layer_is_bullish(medium_term_score)
        ):
            return "Mixed Bearish"
        return label

    @staticmethod
    def calculate_volume_indicators(data: pd.DataFrame) -> pd.DataFrame:
        if "Volume" not in data.columns:
            return data
        data["VOLUME_SMA20"] = data["Volume"].rolling(20).mean()
        data["RVOL20"] = data["Volume"] / data["VOLUME_SMA20"]
        data["RVOL"] = data["RVOL20"]
        data["VOLUME_EMA20"] = data["Volume"].ewm(span=20, adjust=False).mean()
        data["VOLUME_EMA50"] = data["Volume"].ewm(span=50, adjust=False).mean()
        data["VOLUME_SPIKE"] = data["Volume"] > (2 * data["VOLUME_SMA20"])
        return data

    @classmethod
    def calculate_volume_trend(cls, data: pd.DataFrame) -> str:
        ema20 = cls.latest_valid_value(data.get("VOLUME_EMA20", pd.Series(dtype=float)))
        ema50 = cls.latest_valid_value(data.get("VOLUME_EMA50", pd.Series(dtype=float)))
        if ema20 is None or ema50 is None or pd.isna(ema20) or pd.isna(ema50) or ema50 == 0:
            return "Neutral"
        relative_gap = abs(ema20 - ema50) / ema50
        if relative_gap < 0.01:
            return "Neutral"
        return "Rising" if ema20 > ema50 else "Falling"

    @classmethod
    def compare_price_to_level(cls, price: float | None, level: float | None) -> str:
        if not cls.is_valid_number(price) or not cls.is_valid_number(level):
            return "n/a"
        return "Above" if price >= level else "Below"

    @classmethod
    def percentage_distance(cls, value: float | None, reference: float | None) -> float | None:
        if not cls.is_valid_number(value) or not cls.is_valid_number(reference) or reference == 0:
            return None
        return (value - reference) / reference

    @classmethod
    def format_value_hierarchy(cls, values: list[tuple[str, float | None]]) -> str:
        valid_values = [
            (label, value)
            for label, value in values
            if cls.is_valid_number(value)
        ]
        if not valid_values:
            return "Not enough data"
        ordered_values = sorted(valid_values, key=lambda item: item[1], reverse=True)
        return " > ".join(label for label, _value in ordered_values)

    @classmethod
    def format_slope_state(cls, label: str, current: float | None, previous: float | None) -> str:
        if not cls.is_valid_number(current) or not cls.is_valid_number(previous):
            return f"{label} N/A"
        if previous == 0:
            return f"{label} N/A"
        relative_change = (current - previous) / abs(previous)
        if abs(relative_change) <= 0.0005:
            return f"{label} \u2192"
        return f"{label} \u2197" if relative_change > 0 else f"{label} \u2198"

    @classmethod
    def format_cross_state(cls, sma50: float | None, sma200: float | None) -> str:
        if not cls.is_valid_number(sma50) or not cls.is_valid_number(sma200) or sma200 == 0:
            return "Cross Neutral"
        relative_gap = abs(sma50 - sma200) / abs(sma200)
        if relative_gap <= 0.0005:
            return "Cross Neutral"
        return "Golden Cross" if sma50 > sma200 else "Death Cross"

    @staticmethod
    def format_trend_horizon(interval: str | None, layer: str) -> str:
        fallback = {
            "fast": "~20 bars",
            "intermediate": "~50-100 bars",
            "slow": "~200 bars"
        }
        horizons = {
            "5m": {
                "fast": "~1-2h",
                "intermediate": "~4-8h",
                "slow": "~2 trading days"
            },
            "15m": {
                "fast": "~1 day",
                "intermediate": "~2-4 days",
                "slow": "~1-2 weeks"
            },
            "30m": {
                "fast": "~2 days",
                "intermediate": "~1-2 weeks",
                "slow": "~4 weeks"
            },
            "1h": {
                "fast": "~2-3 days",
                "intermediate": "~1-3 weeks",
                "slow": "~5 weeks"
            },
            "1d": {
                "fast": "~1 month",
                "intermediate": "~3-6 months",
                "slow": "~1 year"
            },
            "1wk": {
                "fast": "~5 months",
                "intermediate": "~1-2 years",
                "slow": "~4 years"
            }
        }
        interval_key = str(interval or "").lower()
        return horizons.get(interval_key, fallback).get(layer, fallback.get(layer, "~bars"))

    @classmethod
    def calculate_period_price_summary(cls, data: pd.DataFrame) -> dict[str, float | None]:
        if data.empty or "Close" not in data.columns:
            return {
                "period_start_price": None,
                "period_end_price": None,
                "period_average_price": None,
                "period_change": None,
                "period_end_vs_average": None
            }
        closes = data["Close"].dropna()
        if closes.empty:
            return {
                "period_start_price": None,
                "period_end_price": None,
                "period_average_price": None,
                "period_change": None,
                "period_end_vs_average": None
            }
        start_price = closes.iloc[0]
        end_price = closes.iloc[-1]
        average_price = closes.mean()
        return {
            "period_start_price": start_price,
            "period_end_price": end_price,
            "period_average_price": average_price,
            "period_change": cls.percentage_distance(end_price, start_price),
            "period_end_vs_average": cls.percentage_distance(end_price, average_price)
        }

    @staticmethod
    def format_summary_percent(value: float | None) -> str:
        if value is None or pd.isna(value):
            return "N/A"
        return f"{value * 100:+.1f}%"

    @staticmethod
    def calculate_52w_levels(data: pd.DataFrame) -> tuple[float | None, float | None]:
        if data.empty or "Close" not in data.columns:
            return None, None
        end = data.index[-1]
        try:
            start = end - pd.DateOffset(years=1)
            window = data.loc[data.index >= start]
        except (TypeError, ValueError, AttributeError):
            window = data.tail(252)
        if len(window) < 50:
            return None, None
        high_source = window["High"] if "High" in window.columns else window["Close"]
        low_source = window["Low"] if "Low" in window.columns else window["Close"]
        return high_source.max(), low_source.min()

    @staticmethod
    def calculate_cross_from_columns(data: pd.DataFrame, sma50_column: str, sma200_column: str) -> str:
        if not {sma50_column, sma200_column}.issubset(data.columns):
            return "N/A"
        cross_data = data[[sma50_column, sma200_column]].dropna()
        if cross_data.empty:
            return "N/A"
        current = cross_data.iloc[-1]
        if current[sma50_column] > current[sma200_column]:
            state = "Golden State"
        elif current[sma50_column] < current[sma200_column]:
            state = "Death State"
        else:
            state = "None"
        if len(cross_data) >= 2:
            previous = cross_data.iloc[-2]
            if previous[sma50_column] <= previous[sma200_column] and current[sma50_column] > current[sma200_column]:
                return "Golden Cross"
            if previous[sma50_column] >= previous[sma200_column] and current[sma50_column] < current[sma200_column]:
                return "Death Cross"
        return state

    @staticmethod
    def calculate_cross(data: pd.DataFrame) -> str:
        return TechnicalAnalysisMixin.calculate_cross_from_columns(data, "SMA50", "SMA200")

    @staticmethod
    def calculate_daily_cross(data: pd.DataFrame) -> str:
        daily_cross = TechnicalAnalysisMixin.calculate_cross_from_columns(data, "DAILY_SMA50", "DAILY_SMA200")
        if daily_cross != "N/A":
            return daily_cross
        return TechnicalAnalysisMixin.calculate_cross_from_columns(data, "SMA50", "SMA200")

    @classmethod
    def classify_bullish_structure_score(
        cls,
        score: int | None,
        trend_score: int | None = None,
        short_term_score: int | None = None,
        medium_term_score: int | None = None,
        long_term_score: int | None = None,
        momentum_score: int | None = None,
        trend_phase: str = "N/A",
        trend_direction: str | None = None
    ) -> str:
        if score is None:
            return "N/A"
        recovery_phase = trend_phase in {"Early Recovery", "Recovery Attempt"}
        if score >= 12:
            if recovery_phase:
                return trend_phase
            if trend_phase != "Confirmed Uptrend":
                return "Bullish"
            return "Strong Bullish"
        if score >= 9:
            if recovery_phase:
                return trend_phase
            return "Bullish"
        if score >= 6:
            if recovery_phase:
                return trend_phase
            return "Neutral / Transition"
        if recovery_phase and trend_direction != "Deteriorating":
            return trend_phase
        if cls.is_strongly_bearish_setup(
            short_term_score,
            medium_term_score,
            long_term_score,
            momentum_score=momentum_score,
            trend_direction=trend_direction
        ):
            return "Strongly Bearish"
        if (
            cls.trend_layer_is_bullish(short_term_score)
            and cls.trend_layer_is_bearish(long_term_score)
        ):
            return "Bearish, Improving" if trend_direction == "Improving" else "Mixed Bearish"
        if trend_direction == "Improving" and trend_score is not None and trend_score <= 3:
            return "Bearish, Improving"
        return "Bearish"

    @classmethod
    def classify_trend_score(cls, score: int | None) -> str:
        return cls.classify_bullish_structure_score(score)

    @classmethod
    def classify_extended_bullish_score(
        cls,
        score: int | None,
        trend_score: int | None = None,
        short_term_score: int | None = None,
        medium_term_score: int | None = None,
        long_term_score: int | None = None,
        momentum_score: int | None = None,
        confirmation_score: int | None = None,
        trend_phase: str = "N/A",
        trend_direction: str | None = None
    ) -> str:
        if score is None:
            return "N/A"
        recovery_phase = trend_phase in {"Early Recovery", "Recovery Attempt"}
        if score >= 15:
            if recovery_phase:
                return trend_phase
            if trend_phase != "Confirmed Uptrend":
                return "Bullish Confirmed"
            return "Strong Bullish Confirmed"
        if score >= 12:
            if recovery_phase:
                return trend_phase
            return "Bullish Confirmed"
        if score >= 8:
            if recovery_phase:
                return trend_phase
            return "Neutral / Transition"
        if recovery_phase and trend_direction != "Deteriorating":
            return trend_phase
        if cls.is_strongly_bearish_setup(
            short_term_score,
            medium_term_score,
            long_term_score,
            momentum_score=momentum_score,
            trend_direction=trend_direction,
            confirmation_score=confirmation_score
        ):
            return "Strongly Bearish"
        if (
            cls.trend_layer_is_bullish(short_term_score)
            and cls.trend_layer_is_bearish(long_term_score)
        ):
            return "Bearish, Improving" if trend_direction == "Improving" else "Mixed Bearish"
        if trend_direction == "Improving" and trend_score is not None and trend_score <= 3:
            return "Bearish, Improving"
        return "Bearish"

    @staticmethod
    def calculate_investment_view(business_health: str, valuation: str, trend: str) -> str:
        business = str(business_health).lower()
        value = str(valuation).lower()
        trend_text = str(trend).lower()
        trend_bullish = "bullish" in trend_text
        trend_bearish = "bearish" in trend_text or "weak" in trend_text
        if business == "strong" and value == "cheap" and trend_bearish:
            return "Watchlist"
        if business == "strong" and value == "cheap" and trend_bullish:
            return "Attractive"
        if business == "weak" and trend_bearish:
            return "Risky"
        return "Watchlist"

    @classmethod
    def calculate_bullish_structure_score(cls, data: pd.DataFrame) -> dict[str, Any]:
        empty_score = {
            "score": None,
            "max_score": BULLISH_STRUCTURE_SCORE_MAX,
            "rating": "N/A",
            "trend_score": None,
            "short_term_trend_score": None,
            "short_term_trend_label": "N/A",
            "medium_term_trend_score": None,
            "medium_term_trend_label": "N/A",
            "long_term_trend_score": None,
            "long_term_trend_label": "N/A",
            "trend_phase": "N/A",
            "momentum_score": None,
            "quality_score": None,
            "confirmation_score": None,
            "confirmation_max": CONFIRMATION_SCORE_MAX,
            "extended_total_score": None,
            "extended_max_score": EXTENDED_BULLISH_SCORE_MAX,
            "extended_rating": "N/A",
            "current_price": None,
            "ema9": None,
            "ema12": None,
            "ema20": None,
            "ema50": None,
            "ema100": None,
            "ema200": None,
            "sma50": None,
            "sma200": None,
            "ema20_previous": None,
            "ema50_previous": None,
            "ema100_previous": None,
            "sma200_previous": None,
            "ema50_20_bars_ago": None,
            "rsi14": None,
            "macd": None,
            "macd_signal": None,
            "volume": None,
            "volume_sma20": None,
            "rvol20": None,
            "atr14": None,
            "atr_pct": None
        }
        if data is None or data.empty:
            return empty_score
        close_series = cls.first_available_series(data, "Close")
        ema9_series = cls.first_available_series(data, "DAILY_EMA9", "EMA9")
        ema12_series = cls.first_available_series(data, "DAILY_EMA12", "EMA12")
        ema20_series = cls.first_available_series(data, "DAILY_EMA20", "EMA20")
        ema50_series = cls.first_available_series(data, "DAILY_EMA50", "EMA50")
        ema100_series = cls.first_available_series(data, "DAILY_EMA100", "EMA100")
        ema200_series = cls.first_available_series(data, "DAILY_EMA200", "EMA200")
        sma50_series = cls.first_available_series(data, "DAILY_SMA50", "SMA50")
        sma200_series = cls.first_available_series(data, "DAILY_SMA200", "SMA200")
        rsi14_series = cls.first_available_series(data, "DAILY_RSI14", "RSI")
        macd_series = cls.first_available_series(data, "DAILY_MACD", "MACD")
        macd_signal_series = cls.first_available_series(data, "DAILY_MACD_SIGNAL", "MACD_SIGNAL")
        volume_series = cls.first_available_series(data, "Volume")
        volume_sma20_series = cls.first_available_series(data, "DAILY_VOLUME_SMA20", "VOLUME_SMA20")
        rvol20_series = cls.first_available_series(data, "DAILY_RVOL20", "RVOL20", "RVOL")
        atr14_series = cls.first_available_series(data, "DAILY_ATR14", "ATR14")
        atr_pct_series = cls.first_available_series(data, "DAILY_ATR_PCT", "ATR_PCT")

        current_price = cls.latest_valid_value(close_series)
        if not cls.is_valid_number(current_price):
            return empty_score
        ema9 = cls.latest_valid_value(ema9_series)
        ema12 = cls.latest_valid_value(ema12_series)
        ema20 = cls.latest_valid_value(ema20_series)
        ema50 = cls.latest_valid_value(ema50_series)
        ema100 = cls.latest_valid_value(ema100_series)
        ema200 = cls.latest_valid_value(ema200_series)
        sma50 = cls.latest_valid_value(sma50_series)
        sma200 = cls.latest_valid_value(sma200_series)
        ema20_previous = cls.previous_valid_value(ema20_series)
        ema50_previous = cls.previous_valid_value(ema50_series)
        ema100_previous = cls.previous_valid_value(ema100_series)
        sma200_previous = cls.previous_valid_value(sma200_series)
        ema50_20_bars_ago = None
        ema50_values = ema50_series.dropna()
        if len(ema50_values) >= 21:
            ema50_20_bars_ago = ema50_values.iloc[-21]
        rsi14 = cls.latest_valid_value(rsi14_series)
        macd = cls.latest_valid_value(macd_series)
        macd_signal = cls.latest_valid_value(macd_signal_series)
        volume = cls.latest_valid_value(volume_series)
        volume_sma20 = cls.latest_valid_value(volume_sma20_series)
        rvol20 = cls.latest_valid_value(rvol20_series)
        atr14 = cls.latest_valid_value(atr14_series)
        atr_pct = cls.latest_valid_value(atr_pct_series)

        short_term_checks = [
            cls.greater_than(current_price, ema9),
            cls.greater_than(current_price, ema20),
            cls.greater_than(ema9, ema20),
            cls.greater_than(ema20, ema20_previous),
            cls.greater_than(ema20, ema50)
        ]
        medium_term_checks = [
            cls.greater_than(current_price, ema50),
            cls.greater_than(current_price, sma50),
            cls.greater_than(ema50, ema100),
            cls.greater_than(ema50, ema50_previous),
            cls.greater_than(ema100, ema100_previous)
        ]
        long_term_checks = [
            cls.greater_than(current_price, ema200),
            cls.greater_than(current_price, sma200),
            cls.greater_than(ema100, ema200),
            cls.greater_than(sma50, sma200),
            cls.greater_than(sma200, sma200_previous)
        ]
        short_term_score = cls.score_optional_checks(short_term_checks, 5, min_valid=3)
        medium_term_score = cls.score_optional_checks(medium_term_checks, 5, min_valid=3)
        long_term_score = cls.score_optional_checks(long_term_checks, 5, min_valid=3)
        trend_score = cls.calculate_weighted_trend_score(
            short_term_score,
            medium_term_score,
            long_term_score
        )
        if trend_score is None:
            return {
                **empty_score,
                "current_price": current_price,
                "ema9": ema9,
                "ema12": ema12,
                "ema20": ema20,
                "ema50": ema50,
                "ema100": ema100,
                "ema200": ema200,
                "sma50": sma50,
                "sma200": sma200
            }
        trend_phase = cls.classify_trend_phase(
            short_term_score,
            medium_term_score,
            long_term_score
        )
        momentum_checks = [
            cls.greater_than(rsi14, 50),
            cls.greater_than(macd, macd_signal),
            cls.greater_than(macd, 0)
        ]
        ema20_extension_ok = None
        if cls.is_valid_number(current_price) and cls.is_valid_number(ema20):
            ema20_extension_ok = current_price <= ema20 * 1.08
        sma200_extension_ok = None
        if cls.is_valid_number(current_price) and cls.is_valid_number(sma200):
            sma200_extension_ok = current_price <= sma200 * 1.20
        quality_checks = [
            cls.greater_than(volume, volume_sma20),
            ema20_extension_ok,
            sma200_extension_ok
        ]
        momentum_score = cls.score_optional_checks(momentum_checks, 3)
        quality_score = cls.score_optional_checks(quality_checks, 3)
        momentum_score = 0 if momentum_score is None else momentum_score
        quality_score = 0 if quality_score is None else quality_score
        score = trend_score + momentum_score + quality_score
        rvol_confirmed = None
        if (
            cls.is_valid_number(rvol20)
            and cls.is_valid_number(current_price)
            and cls.is_valid_number(ema20)
        ):
            rvol_confirmed = rvol20 > 1.1 and current_price > ema20
        atr_pct_healthy = None
        if cls.is_valid_number(atr_pct):
            atr_pct_healthy = ATR_PCT_HEALTHY_MIN <= atr_pct <= ATR_PCT_HEALTHY_MAX
        confirmation_checks = [
            rvol_confirmed,
            cls.greater_than(volume, volume_sma20),
            atr_pct_healthy
        ]
        confirmation_score = cls.score_optional_checks(confirmation_checks, CONFIRMATION_SCORE_MAX)
        if confirmation_score is not None:
            extended_total_score = score + confirmation_score
            extended_rating = cls.classify_extended_bullish_score(
                extended_total_score,
                trend_score=trend_score,
                short_term_score=short_term_score,
                medium_term_score=medium_term_score,
                long_term_score=long_term_score,
                momentum_score=momentum_score,
                confirmation_score=confirmation_score,
                trend_phase=trend_phase
            )
        else:
            extended_total_score = None
            extended_rating = "N/A"
        return {
            "score": score,
            "max_score": BULLISH_STRUCTURE_SCORE_MAX,
            "rating": cls.classify_bullish_structure_score(
                score,
                trend_score=trend_score,
                short_term_score=short_term_score,
                medium_term_score=medium_term_score,
                long_term_score=long_term_score,
                momentum_score=momentum_score,
                trend_phase=trend_phase
            ),
            "trend_score": trend_score,
            "short_term_trend_score": short_term_score,
            "short_term_trend_label": cls.classify_trend_layer_score(short_term_score),
            "medium_term_trend_score": medium_term_score,
            "medium_term_trend_label": cls.classify_trend_layer_score(medium_term_score),
            "long_term_trend_score": long_term_score,
            "long_term_trend_label": cls.classify_trend_layer_score(long_term_score),
            "trend_phase": trend_phase,
            "momentum_score": momentum_score,
            "quality_score": quality_score,
            "confirmation_score": confirmation_score,
            "confirmation_max": CONFIRMATION_SCORE_MAX,
            "extended_total_score": extended_total_score,
            "extended_max_score": EXTENDED_BULLISH_SCORE_MAX,
            "extended_rating": extended_rating,
            "current_price": current_price,
            "ema9": ema9,
            "ema12": ema12,
            "ema20": ema20,
            "ema50": ema50,
            "ema100": ema100,
            "ema200": ema200,
            "sma50": sma50,
            "sma200": sma200,
            "ema20_previous": ema20_previous,
            "ema50_previous": ema50_previous,
            "ema100_previous": ema100_previous,
            "sma200_previous": sma200_previous,
            "ema50_20_bars_ago": ema50_20_bars_ago,
            "rsi14": rsi14,
            "macd": macd,
            "macd_signal": macd_signal,
            "volume": volume,
            "volume_sma20": volume_sma20,
            "rvol20": rvol20,
            "atr14": atr14,
            "atr_pct": atr_pct
        }

    @classmethod
    def calculate_daily_trend_score(cls, data: pd.DataFrame) -> int | None:
        return cls.calculate_bullish_structure_score(data)["score"]

    @classmethod
    def calculate_daily_structural_summary(
        cls,
        data: pd.DataFrame | None,
        as_of: pd.Timestamp | None = None,
        interval: str | None = None
    ) -> dict[str, Any]:
        empty_summary = {
            "daily_trend_score": None,
            "daily_trend_score_max": BULLISH_STRUCTURE_SCORE_MAX,
            "daily_trend_score_trend": None,
            "short_term_trend_score": None,
            "short_term_trend_label": "N/A",
            "medium_term_trend_score": None,
            "medium_term_trend_label": "N/A",
            "long_term_trend_score": None,
            "long_term_trend_label": "N/A",
            "trend_phase": "N/A",
            "trend_direction": "Stable",
            "trend_period_direction": "Stable",
            "daily_trend_score_momentum": None,
            "daily_trend_score_quality": None,
            "confirmation_score": None,
            "confirmation_max": CONFIRMATION_SCORE_MAX,
            "extended_total_score": None,
            "extended_max_score": EXTENDED_BULLISH_SCORE_MAX,
            "extended_rating": "N/A",
            "ema9": None,
            "ema20": None,
            "ema50": None,
            "ema100": None,
            "ema200": None,
            "sma50": None,
            "sma200": None,
            "fast_trend_horizon": cls.format_trend_horizon(interval, "fast"),
            "intermediate_trend_horizon": cls.format_trend_horizon(interval, "intermediate"),
            "slow_trend_horizon": cls.format_trend_horizon(interval, "slow"),
            "fast_trend_hierarchy": "Not enough data",
            "intermediate_trend_hierarchy": "Not enough data",
            "slow_trend_hierarchy": "Not enough data",
            "fast_trend_state": "EMA20 N/A",
            "intermediate_trend_state": "EMA50 N/A",
            "slow_trend_state": "Cross Neutral",
            "distance_daily_ema20": None,
            "daily_ema_stack": "N/A",
            "daily_ema20_vs_ema50": "N/A",
            "daily_ema50_vs_ema100": "N/A",
            "daily_ema100_vs_ema200": "N/A",
            "daily_sma50_vs_sma200": "N/A",
            "daily_ema50_change_20": None,
            "daily_ema20_trend": "N/A",
            "daily_ema50_trend": "N/A",
            "daily_ema100_trend": "N/A",
            "daily_sma200_trend": "N/A",
            "daily_rsi14": None,
            "daily_macd": None,
            "daily_macd_signal": None,
            "daily_macd_vs_signal": "N/A",
            "daily_macd_zero": "N/A",
            "daily_rvol20": None,
            "daily_atr_pct": None,
            "daily_atr_pct_state": "N/A",
            "distance_volume_sma20": None,
            "volume_vs_sma20": "N/A",
            "daily_ema20_extension": None,
            "daily_ema20_extension_state": "N/A",
            "daily_sma200_extension": None,
            "daily_sma200_extension_state": "N/A",
            "daily_trend": "N/A",
            "daily_cross": "N/A",
            "price_vs_daily_sma50": "n/a",
            "price_vs_daily_sma200": "n/a",
            "distance_daily_sma50": None,
            "distance_daily_sma200": None,
            "distance_52w_high": None,
            "distance_52w_low": None
        }
        if data is None or data.empty or "Close" not in data.columns:
            return empty_summary
        if as_of is not None:
            as_of = cls.align_timestamp_to_index(as_of, data.index)
            data = data.loc[data.index < as_of]
            if data.empty:
                return empty_summary
        current_price = cls.latest_valid_value(data["Close"])
        structure_score = cls.calculate_bullish_structure_score(data)
        ema9 = structure_score["ema9"]
        ema20 = structure_score["ema20"]
        ema50 = structure_score["ema50"]
        ema100 = structure_score["ema100"]
        ema200 = structure_score["ema200"]
        sma50 = structure_score["sma50"]
        sma200 = structure_score["sma200"]
        ema20_previous = structure_score["ema20_previous"]
        ema50_previous = structure_score["ema50_previous"]
        ema100_previous = structure_score["ema100_previous"]
        sma200_previous = structure_score["sma200_previous"]
        ema50_20_bars_ago = structure_score["ema50_20_bars_ago"]
        rsi14 = structure_score["rsi14"]
        macd = structure_score["macd"]
        macd_signal = structure_score["macd_signal"]
        volume = structure_score["volume"]
        volume_sma20 = structure_score["volume_sma20"]
        rvol20 = structure_score["rvol20"]
        atr_pct = structure_score["atr_pct"]
        high_52w, low_52w = cls.calculate_52w_levels(data)
        total_score = structure_score["score"]
        if total_score is None:
            return empty_summary
        daily_trend = structure_score["rating"]
        ema_stack_bullish = (
            cls.is_valid_number(ema20)
            and cls.is_valid_number(ema50)
            and cls.is_valid_number(ema100)
            and cls.is_valid_number(ema200)
            and ema20 > ema50 > ema100 > ema200
        )
        ema_stack_bearish = (
            cls.is_valid_number(ema20)
            and cls.is_valid_number(ema50)
            and cls.is_valid_number(ema100)
            and cls.is_valid_number(ema200)
            and ema20 < ema50 < ema100 < ema200
        )
        ema_stack = "Bullish" if ema_stack_bullish else "Bearish" if ema_stack_bearish else "Mixed"
        ema20_above_ema50 = cls.greater_than(ema20, ema50)
        ema50_above_ema100 = cls.greater_than(ema50, ema100)
        ema100_above_ema200 = cls.greater_than(ema100, ema200)
        sma50_above_sma200 = cls.greater_than(sma50, sma200)
        ema20_rising = cls.greater_than(ema20, ema20_previous)
        ema50_rising = cls.greater_than(ema50, ema50_previous)
        ema100_rising = cls.greater_than(ema100, ema100_previous)
        sma200_rising = cls.greater_than(sma200, sma200_previous)
        macd_above_signal = cls.greater_than(macd, macd_signal)
        macd_above_zero = cls.greater_than(macd, 0)
        volume_above_sma20 = cls.greater_than(volume, volume_sma20)
        ema20_extension = cls.percentage_distance(current_price, ema20)
        sma200_extension = cls.percentage_distance(current_price, sma200)
        fast_trend_hierarchy = cls.format_value_hierarchy([
            ("Price", current_price),
            ("EMA9", ema9),
            ("EMA20", ema20),
            ("EMA50", ema50)
        ])
        intermediate_trend_hierarchy = cls.format_value_hierarchy([
            ("Price", current_price),
            ("EMA50", ema50),
            ("SMA50", sma50),
            ("EMA100", ema100)
        ])
        slow_indicator_values = [
            ("EMA200", ema200),
            ("SMA200", sma200)
        ]
        valid_slow_indicators = [
            (label, value)
            for label, value in slow_indicator_values
            if cls.is_valid_number(value)
        ]
        if len(valid_slow_indicators) == 0:
            slow_trend_hierarchy = "Not enough data"
        elif len(valid_slow_indicators) == 1:
            slow_trend_hierarchy = valid_slow_indicators[0][0]
        else:
            slow_trend_hierarchy = cls.format_value_hierarchy([
                ("Price", current_price),
                *valid_slow_indicators
            ])
        fast_trend_state = cls.format_slope_state("EMA20", ema20, ema20_previous)
        intermediate_trend_state = cls.format_slope_state("EMA50", ema50, ema50_previous)
        slow_cross_state = cls.format_cross_state(sma50, sma200)
        slow_slope_state = cls.format_slope_state("SMA200", sma200, sma200_previous)
        if not valid_slow_indicators:
            slow_trend_state = "Not enough data"
        else:
            slow_trend_state = (
                slow_cross_state
                if slow_slope_state == "SMA200 N/A"
                else f"{slow_cross_state} / {slow_slope_state}"
            )

        def relation_text(passed: bool | None) -> str:
            if passed is None:
                return "N/A"
            return "Above" if passed else "Below"

        def trend_text(rising: bool | None) -> str:
            if rising is None:
                return "N/A"
            return "Rising" if rising else "Falling"

        def threshold_state(value: float | None, limit: float) -> str:
            if not cls.is_valid_number(value):
                return "N/A"
            return "OK" if value <= limit else "Extended"

        def atr_state(value: float | None) -> str:
            if not cls.is_valid_number(value):
                return "N/A"
            return "Healthy" if ATR_PCT_HEALTHY_MIN <= value <= ATR_PCT_HEALTHY_MAX else "Outside Range"

        return {
            "daily_trend_score": total_score,
            "daily_trend_score_max": structure_score["max_score"],
            "daily_trend_score_trend": structure_score["trend_score"],
            "short_term_trend_score": structure_score["short_term_trend_score"],
            "short_term_trend_label": structure_score["short_term_trend_label"],
            "medium_term_trend_score": structure_score["medium_term_trend_score"],
            "medium_term_trend_label": structure_score["medium_term_trend_label"],
            "long_term_trend_score": structure_score["long_term_trend_score"],
            "long_term_trend_label": structure_score["long_term_trend_label"],
            "trend_phase": structure_score["trend_phase"],
            "trend_direction": "Stable",
            "trend_period_direction": "Stable",
            "daily_trend_score_momentum": structure_score["momentum_score"],
            "daily_trend_score_quality": structure_score["quality_score"],
            "confirmation_score": structure_score["confirmation_score"],
            "confirmation_max": structure_score["confirmation_max"],
            "extended_total_score": structure_score["extended_total_score"],
            "extended_max_score": structure_score["extended_max_score"],
            "extended_rating": structure_score["extended_rating"],
            "ema9": ema9,
            "ema20": ema20,
            "ema50": ema50,
            "ema100": ema100,
            "ema200": ema200,
            "sma50": sma50,
            "sma200": sma200,
            "fast_trend_horizon": cls.format_trend_horizon(interval, "fast"),
            "intermediate_trend_horizon": cls.format_trend_horizon(interval, "intermediate"),
            "slow_trend_horizon": cls.format_trend_horizon(interval, "slow"),
            "fast_trend_hierarchy": fast_trend_hierarchy,
            "intermediate_trend_hierarchy": intermediate_trend_hierarchy,
            "slow_trend_hierarchy": slow_trend_hierarchy,
            "fast_trend_state": fast_trend_state,
            "intermediate_trend_state": intermediate_trend_state,
            "slow_trend_state": slow_trend_state,
            "distance_daily_ema20": cls.percentage_distance(current_price, ema20),
            "daily_ema_stack": ema_stack,
            "daily_ema20_vs_ema50": relation_text(ema20_above_ema50),
            "daily_ema50_vs_ema100": relation_text(ema50_above_ema100),
            "daily_ema100_vs_ema200": relation_text(ema100_above_ema200),
            "daily_sma50_vs_sma200": relation_text(sma50_above_sma200),
            "daily_ema50_change_20": cls.percentage_distance(ema50, ema50_20_bars_ago),
            "daily_ema20_trend": trend_text(ema20_rising),
            "daily_ema50_trend": trend_text(ema50_rising),
            "daily_ema100_trend": trend_text(ema100_rising),
            "daily_sma200_trend": trend_text(sma200_rising),
            "daily_rsi14": rsi14,
            "daily_macd": macd,
            "daily_macd_signal": macd_signal,
            "daily_macd_vs_signal": "N/A" if macd_above_signal is None else "Above Signal" if macd_above_signal else "Below Signal",
            "daily_macd_zero": "N/A" if macd_above_zero is None else "Above 0" if macd_above_zero else "Below 0",
            "daily_rvol20": rvol20,
            "daily_atr_pct": atr_pct,
            "daily_atr_pct_state": atr_state(atr_pct),
            "distance_volume_sma20": cls.percentage_distance(volume, volume_sma20),
            "volume_vs_sma20": relation_text(volume_above_sma20),
            "daily_ema20_extension": ema20_extension,
            "daily_ema20_extension_state": threshold_state(ema20_extension, 0.08),
            "daily_sma200_extension": sma200_extension,
            "daily_sma200_extension_state": threshold_state(sma200_extension, 0.20),
            "daily_trend": daily_trend,
            "daily_cross": cls.calculate_daily_cross(data),
            "price_vs_daily_sma50": cls.compare_price_to_level(current_price, sma50),
            "price_vs_daily_sma200": cls.compare_price_to_level(current_price, sma200),
            "distance_daily_sma50": cls.percentage_distance(current_price, sma50),
            "distance_daily_sma200": cls.percentage_distance(current_price, sma200),
            "distance_52w_high": cls.percentage_distance(current_price, high_52w),
            "distance_52w_low": cls.percentage_distance(current_price, low_52w)
        }

    @classmethod
    def calculate_signal_summary(
        cls,
        data: pd.DataFrame,
        daily_data: pd.DataFrame | None = None,
        fundamentals: dict[str, dict[str, Any]] | None = None,
        daily_summary_as_of: pd.Timestamp | None = None,
        period_start_as_of: pd.Timestamp | None = None,
        interval: str | None = None
    ) -> dict[str, Any]:
        if fundamentals is None and isinstance(daily_data, dict):
            fundamentals = daily_data
            daily_data = None
        current_price = cls.latest_valid_value(data["Close"])
        current_rvol = cls.latest_valid_value(data.get("RVOL", pd.Series(dtype=float)))
        current_atr = cls.latest_valid_value(data.get("ATR14", pd.Series(dtype=float)))
        volume_trend = cls.calculate_volume_trend(data)
        period_price_summary = cls.calculate_period_price_summary(data)
        interval_summary = cls.calculate_daily_structural_summary(
            data,
            as_of=daily_summary_as_of,
            interval=interval
        )
        daily_context_summary = cls.calculate_daily_structural_summary(
            daily_data,
            as_of=daily_summary_as_of,
            interval="1d"
        )
        if daily_context_summary.get("distance_52w_high") is not None:
            interval_summary["distance_52w_high"] = daily_context_summary["distance_52w_high"]
        if daily_context_summary.get("distance_52w_low") is not None:
            interval_summary["distance_52w_low"] = daily_context_summary["distance_52w_low"]
        score_changes = cls.calculate_signal_score_changes(
            data,
            interval_summary,
            daily_summary_as_of=daily_summary_as_of,
            period_start_as_of=period_start_as_of,
            interval=interval
        )
        trend_direction = score_changes.get("trend_direction", "Stable")
        trend_period_direction = score_changes.get("trend_period_direction", "Stable")
        interval_summary["trend_direction"] = trend_direction
        interval_summary["trend_period_direction"] = trend_period_direction
        interval_summary["daily_trend"] = cls.refine_trend_label_with_direction(
            interval_summary.get("daily_trend", "N/A"),
            interval_summary.get("trend_phase", "N/A"),
            trend_direction,
            interval_summary.get("short_term_trend_score"),
            interval_summary.get("medium_term_trend_score"),
            interval_summary.get("long_term_trend_score")
        )
        interval_summary["extended_rating"] = cls.refine_trend_label_with_direction(
            interval_summary.get("extended_rating", "N/A"),
            interval_summary.get("trend_phase", "N/A"),
            trend_direction,
            interval_summary.get("short_term_trend_score"),
            interval_summary.get("medium_term_trend_score"),
            interval_summary.get("long_term_trend_score")
        )
        fundamentals = fundamentals or {}
        valuation = fundamentals.get("valuation_view", {}).get("value", "Unknown")
        business_health = fundamentals.get("business_health", {}).get("value", "Unknown")
        daily_trend = interval_summary["daily_trend"]
        investment_view = cls.calculate_investment_view(business_health, valuation, daily_trend)
        return {
            "current_price": current_price,
            **period_price_summary,
            **interval_summary,
            "trend_score": interval_summary["daily_trend_score"],
            "overall_trend": daily_trend,
            "cross": interval_summary["daily_cross"],
            "price_vs_sma50": interval_summary["price_vs_daily_sma50"],
            "price_vs_sma200": interval_summary["price_vs_daily_sma200"],
            "distance_sma50": interval_summary["distance_daily_sma50"],
            "distance_sma200": interval_summary["distance_daily_sma200"],
            "current_rvol": current_rvol,
            "atr14": current_atr,
            "volume_trend": volume_trend,
            "valuation": valuation,
            "business_health": business_health,
            "investment_view": investment_view,
            "price_vs_ema20": cls.compare_price_to_level(
                current_price,
                interval_summary.get("ema20")
            ),
            **score_changes
        }

    @staticmethod
    def calculate_score_direction(
        current_summary: dict[str, Any],
        baseline_summary: dict[str, Any] | None,
        score_key: str = "daily_trend_score_trend"
    ) -> str:
        if not baseline_summary:
            return "Stable"
        current_value = current_summary.get(score_key)
        baseline_value = baseline_summary.get(score_key)
        if current_value is None or baseline_value is None:
            return "Stable"
        current_score = int(current_value)
        baseline_score = int(baseline_value)
        if current_score > baseline_score:
            return "Improving"
        if current_score < baseline_score:
            return "Deteriorating"
        return "Stable"

    @classmethod
    def calculate_signal_score_changes(
        cls,
        daily_data: pd.DataFrame | None,
        current_summary: dict[str, Any],
        daily_summary_as_of: pd.Timestamp | None = None,
        period_start_as_of: pd.Timestamp | None = None,
        interval: str | None = None
    ) -> dict[str, Any]:
        empty_changes: dict[str, Any] = {
            "score_changes_last_day": [],
            "score_changes_period_start": [],
            "trend_direction": "Stable",
            "trend_period_direction": "Stable"
        }
        if daily_data is None or daily_data.empty:
            return empty_changes
        comparison_data = daily_data
        if daily_summary_as_of is not None:
            as_of = cls.align_timestamp_to_index(daily_summary_as_of, comparison_data.index)
            comparison_data = comparison_data.loc[comparison_data.index < as_of]
        if comparison_data.empty:
            return empty_changes
        previous_summary = (
            cls.calculate_daily_structural_summary(comparison_data.iloc[:-1], interval=interval)
            if len(comparison_data) >= 2
            else None
        )
        period_start_summary = None
        if period_start_as_of is None:
            period_start_summary = cls.calculate_daily_structural_summary(comparison_data.iloc[:1], interval=interval)
        else:
            period_start = cls.align_timestamp_to_index(
                pd.Timestamp(period_start_as_of),
                comparison_data.index
            )
            start_candidates = comparison_data.index[comparison_data.index >= period_start]
            if len(start_candidates) > 0:
                first_position = int(comparison_data.index.searchsorted(start_candidates[0], side="left"))
                period_start_summary = cls.calculate_daily_structural_summary(
                    comparison_data.iloc[:first_position + 1],
                    interval=interval
                )
        last_day_rows = cls.build_score_change_rows(
            current_summary,
            previous_summary
        )
        period_start_rows = cls.build_score_change_rows(
            current_summary,
            period_start_summary
        )
        return {
            "score_changes_last_day": last_day_rows,
            "score_changes_period_start": period_start_rows,
            "trend_direction": cls.calculate_score_direction(current_summary, previous_summary),
            "trend_period_direction": cls.calculate_score_direction(current_summary, period_start_summary)
        }

    @staticmethod
    def build_score_change_rows(
        current_summary: dict[str, Any],
        baseline_summary: dict[str, Any] | None
    ) -> list[dict[str, str]]:
        if not baseline_summary:
            return []
        score_specs = [
            ("Trend", "daily_trend_score_trend", 8),
            ("Momentum", "daily_trend_score_momentum", 3),
            ("Setup Quality", "daily_trend_score_quality", 3),
            ("Confirmation", "confirmation_score", "confirmation_max")
        ]
        rows: list[dict[str, str]] = []
        for label, score_key, max_source in score_specs:
            current_value = current_summary.get(score_key)
            baseline_value = baseline_summary.get(score_key)
            if current_value is None or baseline_value is None:
                continue
            current_score = int(current_value)
            baseline_score = int(baseline_value)
            if current_score == baseline_score:
                continue
            max_score = (
                current_summary.get(max_source)
                if isinstance(max_source, str)
                else max_source
            )
            if max_score is None:
                continue
            improved = current_score > baseline_score
            arrow = "▲" if improved else "▼"
            display_label = label
            rows.append({
                "label": f"{arrow} {display_label}",
                "value": f"{baseline_score}/{int(max_score)} → {current_score}/{int(max_score)}",
                "color": "#16a34a" if improved else "#dc2626"
            })
        return rows

    @staticmethod
    def add_daily_structural_indicators(data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        for span in (9, 12, 20, 50, 100, 200):
            data[f"DAILY_EMA{span}"] = data["Close"].ewm(span=span, adjust=False).mean()
        for window in (20, 50, 100, 200):
            data[f"DAILY_SMA{window}"] = data["Close"].rolling(window).mean()
        delta = data["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        data["DAILY_RSI14"] = 100 - (100 / (1 + rs))
        ema12 = data["Close"].ewm(span=12, adjust=False).mean()
        ema26 = data["Close"].ewm(span=26, adjust=False).mean()
        data["DAILY_MACD"] = ema12 - ema26
        data["DAILY_MACD_SIGNAL"] = data["DAILY_MACD"].ewm(span=9, adjust=False).mean()
        if "Volume" in data.columns:
            data["DAILY_VOLUME_SMA20"] = data["Volume"].rolling(20).mean()
            data["DAILY_RVOL20"] = data["Volume"] / data["DAILY_VOLUME_SMA20"]
        if {"High", "Low", "Close"}.issubset(data.columns):
            high_low = data["High"] - data["Low"]
            high_close = (data["High"] - data["Close"].shift()).abs()
            low_close = (data["Low"] - data["Close"].shift()).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            data["DAILY_ATR14"] = true_range.rolling(14).mean()
            data["DAILY_ATR_PCT"] = data["DAILY_ATR14"] / data["Close"]
        return data

    @classmethod
    def add_indicators(cls, data):
        data["EMA9"] = data["Close"].ewm(span=9, adjust=False).mean()
        data["EMA12"] = data["Close"].ewm(span=12, adjust=False).mean()
        data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
        data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()
        data["EMA100"] = data["Close"].ewm(span=100, adjust=False).mean()
        data["EMA200"] = data["Close"].ewm(span=200, adjust=False).mean()
        data["SMA20"] = data["Close"].rolling(20).mean()
        data["SMA50"] = data["Close"].rolling(50).mean()
        data["SMA100"] = data["Close"].rolling(100).mean()
        data["SMA200"] = data["Close"].rolling(200).mean()
        data = cls.calculate_volume_indicators(data)
        mid = data["Close"].rolling(20).mean()
        std = data["Close"].rolling(20).std()
        data["BB_UPPER"] = mid + 2 * std
        data["BB_LOWER"] = mid - 2 * std
        delta = data["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        data["RSI"] = 100 - (100 / (1 + rs))
        high_low = data["High"] - data["Low"]
        high_close = (data["High"] - data["Close"].shift()).abs()
        low_close = (data["Low"] - data["Close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data["ATR14"] = true_range.rolling(14).mean()
        data["ATR_PCT"] = data["ATR14"] / data["Close"]
        ema12 = data["Close"].ewm(span=12, adjust=False).mean()
        ema26 = data["Close"].ewm(span=26, adjust=False).mean()
        data["MACD"] = ema12 - ema26
        data["MACD_SIGNAL"] = data["MACD"].ewm(span=9, adjust=False).mean()
        return data
