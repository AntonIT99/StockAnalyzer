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
    def is_valid_number(value: Any) -> bool:
        return value is not None and not pd.isna(value)

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
    def calculate_cross(data: pd.DataFrame) -> str:
        if not {"SMA50", "SMA200"}.issubset(data.columns):
            return "N/A"
        cross_data = data[["SMA50", "SMA200"]].dropna()
        if cross_data.empty:
            return "N/A"
        current = cross_data.iloc[-1]
        if current["SMA50"] > current["SMA200"]:
            state = "Golden State"
        elif current["SMA50"] < current["SMA200"]:
            state = "Death State"
        else:
            state = "None"
        if len(cross_data) >= 2:
            previous = cross_data.iloc[-2]
            if previous["SMA50"] <= previous["SMA200"] and current["SMA50"] > current["SMA200"]:
                return "Golden Cross"
            if previous["SMA50"] >= previous["SMA200"] and current["SMA50"] < current["SMA200"]:
                return "Death Cross"
        return state

    @staticmethod
    def calculate_daily_cross(data: pd.DataFrame) -> str:
        if not {"DAILY_SMA50", "DAILY_SMA200"}.issubset(data.columns):
            return "N/A"
        cross_data = data[["DAILY_SMA50", "DAILY_SMA200"]].dropna()
        if cross_data.empty:
            return "N/A"
        current = cross_data.iloc[-1]
        if current["DAILY_SMA50"] > current["DAILY_SMA200"]:
            state = "Golden State"
        elif current["DAILY_SMA50"] < current["DAILY_SMA200"]:
            state = "Death State"
        else:
            state = "None"
        if len(cross_data) >= 2:
            previous = cross_data.iloc[-2]
            if previous["DAILY_SMA50"] <= previous["DAILY_SMA200"] and current["DAILY_SMA50"] > current["DAILY_SMA200"]:
                return "Golden Cross"
            if previous["DAILY_SMA50"] >= previous["DAILY_SMA200"] and current["DAILY_SMA50"] < current["DAILY_SMA200"]:
                return "Death Cross"
        return state

    @staticmethod
    def classify_bullish_structure_score(score: int | None, trend_score: int | None = None) -> str:
        if score is None:
            return "N/A"
        if score >= 12:
            return "Strong Bullish"
        if score >= 9:
            return "Bullish"
        if score >= 6:
            return "Mixed"
        if trend_score is not None and trend_score <= 1:
            return "Strongly Bearish"
        return "Bearish"

    @classmethod
    def classify_trend_score(cls, score: int | None) -> str:
        return cls.classify_bullish_structure_score(score)

    @staticmethod
    def classify_extended_bullish_score(score: int | None, trend_score: int | None = None) -> str:
        if score is None:
            return "N/A"
        if score >= 15:
            return "Strong Bullish Confirmed"
        if score >= 12:
            return "Bullish Confirmed"
        if score >= 8:
            return "Mixed"
        if trend_score is not None and trend_score <= 1:
            return "Strongly Bearish"
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
            "momentum_score": None,
            "quality_score": None,
            "confirmation_score": None,
            "confirmation_max": CONFIRMATION_SCORE_MAX,
            "extended_total_score": None,
            "extended_max_score": EXTENDED_BULLISH_SCORE_MAX,
            "extended_rating": "N/A",
            "current_price": None,
            "ema20": None,
            "ema50": None,
            "ema100": None,
            "ema200": None,
            "sma50": None,
            "sma200": None,
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
        current_price = cls.latest_valid_value(data.get("Close", pd.Series(dtype=float)))
        ema20 = cls.latest_valid_value(data.get("DAILY_EMA20", pd.Series(dtype=float)))
        ema50 = cls.latest_valid_value(data.get("DAILY_EMA50", pd.Series(dtype=float)))
        ema100 = cls.latest_valid_value(data.get("DAILY_EMA100", pd.Series(dtype=float)))
        ema200 = cls.latest_valid_value(data.get("DAILY_EMA200", pd.Series(dtype=float)))
        sma50 = cls.latest_valid_value(data.get("DAILY_SMA50", pd.Series(dtype=float)))
        sma200 = cls.latest_valid_value(data.get("DAILY_SMA200", pd.Series(dtype=float)))
        ema50_20_bars_ago = None
        ema50_values = data.get("DAILY_EMA50", pd.Series(dtype=float)).dropna()
        if len(ema50_values) >= 21:
            ema50_20_bars_ago = ema50_values.iloc[-21]
        rsi14 = cls.latest_valid_value(data.get("DAILY_RSI14", pd.Series(dtype=float)))
        macd = cls.latest_valid_value(data.get("DAILY_MACD", pd.Series(dtype=float)))
        macd_signal = cls.latest_valid_value(data.get("DAILY_MACD_SIGNAL", pd.Series(dtype=float)))
        volume = cls.latest_valid_value(data.get("Volume", pd.Series(dtype=float)))
        volume_sma20 = cls.latest_valid_value(data.get("DAILY_VOLUME_SMA20", pd.Series(dtype=float)))
        rvol20 = cls.latest_valid_value(data.get("DAILY_RVOL20", pd.Series(dtype=float)))
        atr14 = cls.latest_valid_value(data.get("DAILY_ATR14", pd.Series(dtype=float)))
        atr_pct = cls.latest_valid_value(data.get("DAILY_ATR_PCT", pd.Series(dtype=float)))
        required_values = [
            current_price,
            ema20,
            ema50,
            ema100,
            ema200,
            sma50,
            sma200,
            ema50_20_bars_ago,
            rsi14,
            macd,
            macd_signal,
            volume,
            volume_sma20
        ]
        if not all(cls.is_valid_number(value) for value in required_values):
            return empty_score
        trend_checks = [
            current_price > ema20,
            current_price > sma50,
            current_price > sma200,
            ema20 > ema50,
            ema50 > ema100,
            ema100 > ema200,
            sma50 > sma200,
            ema50 > ema50_20_bars_ago
        ]
        momentum_checks = [
            rsi14 > 50,
            macd > macd_signal,
            macd > 0
        ]
        quality_checks = [
            volume > volume_sma20,
            current_price <= ema20 * 1.08,
            current_price <= sma200 * 1.20
        ]
        trend_score = int(sum(trend_checks))
        momentum_score = int(sum(momentum_checks))
        quality_score = int(sum(quality_checks))
        score = trend_score + momentum_score + quality_score
        confirmation_values = [rvol20, atr_pct]
        if all(cls.is_valid_number(value) for value in confirmation_values):
            confirmation_checks = [
                rvol20 > 1.1 and current_price > ema20,
                volume > volume_sma20,
                ATR_PCT_HEALTHY_MIN <= atr_pct <= ATR_PCT_HEALTHY_MAX
            ]
            confirmation_score = int(sum(confirmation_checks))
            extended_total_score = score + confirmation_score
            extended_rating = cls.classify_extended_bullish_score(extended_total_score, trend_score=trend_score)
        else:
            confirmation_score = None
            extended_total_score = None
            extended_rating = "N/A"
        return {
            "score": score,
            "max_score": BULLISH_STRUCTURE_SCORE_MAX,
            "rating": cls.classify_bullish_structure_score(score, trend_score=trend_score),
            "trend_score": trend_score,
            "momentum_score": momentum_score,
            "quality_score": quality_score,
            "confirmation_score": confirmation_score,
            "confirmation_max": CONFIRMATION_SCORE_MAX,
            "extended_total_score": extended_total_score,
            "extended_max_score": EXTENDED_BULLISH_SCORE_MAX,
            "extended_rating": extended_rating,
            "current_price": current_price,
            "ema20": ema20,
            "ema50": ema50,
            "ema100": ema100,
            "ema200": ema200,
            "sma50": sma50,
            "sma200": sma200,
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
        as_of: pd.Timestamp | None = None
    ) -> dict[str, Any]:
        empty_summary = {
            "daily_trend_score": None,
            "daily_trend_score_max": BULLISH_STRUCTURE_SCORE_MAX,
            "daily_trend_score_trend": None,
            "daily_trend_score_momentum": None,
            "daily_trend_score_quality": None,
            "confirmation_score": None,
            "confirmation_max": CONFIRMATION_SCORE_MAX,
            "extended_total_score": None,
            "extended_max_score": EXTENDED_BULLISH_SCORE_MAX,
            "extended_rating": "N/A",
            "distance_daily_ema20": None,
            "daily_ema_stack": "N/A",
            "daily_ema20_vs_ema50": "N/A",
            "daily_ema50_vs_ema100": "N/A",
            "daily_ema100_vs_ema200": "N/A",
            "daily_sma50_vs_sma200": "N/A",
            "daily_ema50_change_20": None,
            "daily_ema50_trend": "N/A",
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
        ema20 = structure_score["ema20"]
        ema50 = structure_score["ema50"]
        ema100 = structure_score["ema100"]
        ema200 = structure_score["ema200"]
        sma50 = cls.latest_valid_value(data.get("DAILY_SMA50", pd.Series(dtype=float)))
        sma200 = cls.latest_valid_value(data.get("DAILY_SMA200", pd.Series(dtype=float)))
        ema50_20_bars_ago = structure_score["ema50_20_bars_ago"]
        rsi14 = structure_score["rsi14"]
        macd = structure_score["macd"]
        macd_signal = structure_score["macd_signal"]
        volume = structure_score["volume"]
        volume_sma20 = structure_score["volume_sma20"]
        rvol20 = structure_score["rvol20"]
        atr_pct = structure_score["atr_pct"]
        high_52w, low_52w = cls.calculate_52w_levels(data)
        trend_score = structure_score["score"]
        if trend_score is None:
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
        ema20_above_ema50 = cls.is_valid_number(ema20) and cls.is_valid_number(ema50) and ema20 > ema50
        ema50_above_ema100 = cls.is_valid_number(ema50) and cls.is_valid_number(ema100) and ema50 > ema100
        ema100_above_ema200 = cls.is_valid_number(ema100) and cls.is_valid_number(ema200) and ema100 > ema200
        sma50_above_sma200 = cls.is_valid_number(sma50) and cls.is_valid_number(sma200) and sma50 > sma200
        ema50_rising = (
            cls.is_valid_number(ema50)
            and cls.is_valid_number(ema50_20_bars_ago)
            and ema50 > ema50_20_bars_ago
        )
        macd_above_signal = cls.is_valid_number(macd) and cls.is_valid_number(macd_signal) and macd > macd_signal
        macd_above_zero = cls.is_valid_number(macd) and macd > 0
        volume_above_sma20 = cls.is_valid_number(volume) and cls.is_valid_number(volume_sma20) and volume > volume_sma20
        ema20_extension = cls.percentage_distance(current_price, ema20)
        sma200_extension = cls.percentage_distance(current_price, sma200)
        return {
            "daily_trend_score": trend_score,
            "daily_trend_score_max": structure_score["max_score"],
            "daily_trend_score_trend": structure_score["trend_score"],
            "daily_trend_score_momentum": structure_score["momentum_score"],
            "daily_trend_score_quality": structure_score["quality_score"],
            "confirmation_score": structure_score["confirmation_score"],
            "confirmation_max": structure_score["confirmation_max"],
            "extended_total_score": structure_score["extended_total_score"],
            "extended_max_score": structure_score["extended_max_score"],
            "extended_rating": structure_score["extended_rating"],
            "distance_daily_ema20": cls.percentage_distance(current_price, ema20),
            "daily_ema_stack": ema_stack,
            "daily_ema20_vs_ema50": "Above" if ema20_above_ema50 else "Below",
            "daily_ema50_vs_ema100": "Above" if ema50_above_ema100 else "Below",
            "daily_ema100_vs_ema200": "Above" if ema100_above_ema200 else "Below",
            "daily_sma50_vs_sma200": "Above" if sma50_above_sma200 else "Below",
            "daily_ema50_change_20": cls.percentage_distance(ema50, ema50_20_bars_ago),
            "daily_ema50_trend": "Rising" if ema50_rising else "Falling",
            "daily_rsi14": rsi14,
            "daily_macd": macd,
            "daily_macd_signal": macd_signal,
            "daily_macd_vs_signal": "Above Signal" if macd_above_signal else "Below Signal",
            "daily_macd_zero": "Above 0" if macd_above_zero else "Below 0",
            "daily_rvol20": rvol20,
            "daily_atr_pct": atr_pct,
            "daily_atr_pct_state": "Healthy" if cls.is_valid_number(atr_pct) and ATR_PCT_HEALTHY_MIN <= atr_pct <= ATR_PCT_HEALTHY_MAX else "Outside Range",
            "distance_volume_sma20": cls.percentage_distance(volume, volume_sma20),
            "volume_vs_sma20": "Above" if volume_above_sma20 else "Below",
            "daily_ema20_extension": ema20_extension,
            "daily_ema20_extension_state": "OK" if cls.is_valid_number(ema20_extension) and ema20_extension <= 0.08 else "Extended",
            "daily_sma200_extension": sma200_extension,
            "daily_sma200_extension_state": "OK" if cls.is_valid_number(sma200_extension) and sma200_extension <= 0.20 else "Extended",
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
        period_start_as_of: pd.Timestamp | None = None
    ) -> dict[str, Any]:
        if fundamentals is None and isinstance(daily_data, dict):
            fundamentals = daily_data
            daily_data = None
        current_price = cls.latest_valid_value(data["Close"])
        current_rvol = cls.latest_valid_value(data.get("RVOL", pd.Series(dtype=float)))
        current_atr = cls.latest_valid_value(data.get("ATR14", pd.Series(dtype=float)))
        volume_trend = cls.calculate_volume_trend(data)
        period_price_summary = cls.calculate_period_price_summary(data)
        daily_summary = cls.calculate_daily_structural_summary(
            daily_data,
            as_of=daily_summary_as_of
        )
        score_changes = cls.calculate_signal_score_changes(
            daily_data,
            daily_summary,
            daily_summary_as_of=daily_summary_as_of,
            period_start_as_of=period_start_as_of
        )
        fundamentals = fundamentals or {}
        valuation = fundamentals.get("valuation_view", {}).get("value", "Unknown")
        business_health = fundamentals.get("business_health", {}).get("value", "Unknown")
        daily_trend = daily_summary["daily_trend"]
        investment_view = cls.calculate_investment_view(business_health, valuation, daily_trend)
        return {
            "current_price": current_price,
            **period_price_summary,
            **daily_summary,
            "trend_score": daily_summary["daily_trend_score"],
            "overall_trend": daily_trend,
            "cross": daily_summary["daily_cross"],
            "price_vs_sma50": daily_summary["price_vs_daily_sma50"],
            "price_vs_sma200": daily_summary["price_vs_daily_sma200"],
            "distance_sma50": daily_summary["distance_daily_sma50"],
            "distance_sma200": daily_summary["distance_daily_sma200"],
            "current_rvol": current_rvol,
            "atr14": current_atr,
            "volume_trend": volume_trend,
            "valuation": valuation,
            "business_health": business_health,
            "investment_view": investment_view,
            "price_vs_ema20": "n/a",
            **score_changes
        }

    @classmethod
    def calculate_signal_score_changes(
        cls,
        daily_data: pd.DataFrame | None,
        current_summary: dict[str, Any],
        daily_summary_as_of: pd.Timestamp | None = None,
        period_start_as_of: pd.Timestamp | None = None
    ) -> dict[str, list[dict[str, str]]]:
        empty_changes: dict[str, list[dict[str, str]]] = {
            "score_changes_last_day": [],
            "score_changes_period_start": []
        }
        if daily_data is None or daily_data.empty:
            return empty_changes
        comparison_data = daily_data
        if daily_summary_as_of is not None:
            as_of = cls.align_timestamp_to_index(daily_summary_as_of, comparison_data.index)
            comparison_data = comparison_data.loc[comparison_data.index < as_of]
        if comparison_data.empty:
            return empty_changes
        current_bar_date = comparison_data.index[-1]
        previous_summary = (
            cls.calculate_daily_structural_summary(daily_data, as_of=current_bar_date)
            if len(comparison_data) >= 2
            else None
        )
        period_start_summary = None
        if period_start_as_of is not None:
            period_start = cls.align_timestamp_to_index(
                pd.Timestamp(period_start_as_of).normalize(),
                comparison_data.index
            )
            start_candidates = comparison_data.index[comparison_data.index >= period_start]
            if len(start_candidates) > 0:
                period_start_summary = cls.calculate_daily_structural_summary(
                    daily_data,
                    as_of=start_candidates[0] + pd.Timedelta(days=1)
                )
        return {
            "score_changes_last_day": cls.build_score_change_rows(
                current_summary,
                previous_summary
            ),
            "score_changes_period_start": cls.build_score_change_rows(
                current_summary,
                period_start_summary
            )
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
        for span in (20, 50, 100, 200):
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
