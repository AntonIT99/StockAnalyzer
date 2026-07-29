"""Signal summary dashboard drawing."""

from typing import Any
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from .config import CONFIRMATION_SCORE_MAX, EXTENDED_BULLISH_SCORE_MAX, MOMENTUM_SCORE_MAX, SETUP_QUALITY_SCORE_MAX, TECHNICAL_SCORE_WEIGHTS, TREND_STRUCTURE_SCORE_MAX

class SignalSummaryChartMixin:
    def add_signal_summary_box(
        self,
        ax: Any,
        summary: dict[str, Any],
        card_bottom: float = 0.50,
        card_height: float = 0.46
    ) -> None:
        ax.set_axis_off()
        current_price = summary.get("current_price")
        current_rvol = summary.get("current_rvol")
        atr14 = summary.get("atr14")
        rvol_text = f"{current_rvol:.2f}x" if current_rvol is not None and not pd.isna(current_rvol) else "n/a"
        atr_text = f"{atr14:.2f}" if atr14 is not None and not pd.isna(atr14) else "n/a"

        def format_price(value: float | None) -> str:
            if value is None or pd.isna(value):
                return "n/a"
            return f"{value:.2f}"

        def status_color(value: str) -> str:
            normalized = str(value).lower()
            if normalized in {"above", "above signal", "above 0", "rising", "bullish", "strong bullish", "strongly bullish", "bullish confirmed", "strong bullish confirmed", "confirmed uptrend", "golden cross", "golden state", "cheap", "strong", "confirmed", "excellent", "good", "attractive", "ok", "healthy", "improving"}:
                return "#16a34a"
            if normalized in {"partial", "moderate", "fair", "slightly bearish", "neutral / mixed", "mixed", "neutral / transition", "mixed / transition", "transition", "early recovery", "weak recovery", "recovery attempt", "reversal attempt", "improving, not confirmed", "bearish, improving", "mixed bearish", "pullback", "bullish pullback", "bearish pullback", "bullish, losing momentum", "bullish but weakening", "stable", "cross neutral"}:
                return "#f97316"
            if normalized in {"below", "below signal", "below 0", "falling", "bearish", "strong bearish", "strongly bearish", "confirmed downtrend", "weak / bearish", "death cross", "death state", "deteriorating", "expensive", "weak", "none", "poor", "risky", "extended", "outside range"}:
                return "#dc2626"
            if normalized in {"mixed", "neutral", "n/a", "unknown", "watchlist"}:
                return "#64748b"
            return "#0ea5e9"

        def distance_color(value: float | None, positive_is_good: bool = True) -> str:
            if value is None or pd.isna(value):
                return "#64748b"
            if abs(value) < 0.005:
                return "#64748b"
            is_good = value > 0 if positive_is_good else value < 0
            return "#16a34a" if is_good else "#dc2626"

        def from_52w_high_color(value: float | None) -> str:
            if value is None or pd.isna(value):
                return "#64748b"
            if value > -0.10:
                return "#16a34a"
            if value >= -0.25:
                return "#f97316"
            return "#dc2626"

        def from_52w_low_color(value: float | None) -> str:
            if value is None or pd.isna(value):
                return "#64748b"
            if value > 0.30:
                return "#16a34a"
            if value >= 0.10:
                return "#f97316"
            return "#f97316"

        def rvol_color(value: float | None) -> str:
            if value is None or pd.isna(value):
                return "#64748b"
            if value >= 2:
                return "#f97316"
            if value >= 1:
                return "#16a34a"
            return "#dc2626"

        def format_signed_percent(value: float | None) -> str:
            return self.format_summary_percent(value)

        def format_rsi14() -> str:
            rsi = summary.get("daily_rsi14")
            return "N/A" if rsi is None or pd.isna(rsi) else f"{rsi:.1f}"

        def format_extension(state_key: str, distance_key: str) -> str:
            state = summary.get(state_key, "N/A")
            distance = self.format_summary_percent(summary.get(distance_key))
            if distance == "N/A":
                return state
            return distance

        def format_atr_extension() -> str:
            extension = summary.get("atr_extension")
            if extension is None or pd.isna(extension):
                return "N/A"
            return f"{extension:+.1f} ATR ({summary.get('atr_extension_state', 'N/A')})"

        def atr_extension_color() -> str:
            return {
                "Normal": "#16a34a",
                "Moderately Extended": "#f97316",
                "Extended": "#ea580c",
                "Extremely Extended": "#dc2626",
            }.get(summary.get("atr_extension_state"), "#64748b")

        def risk_status(value: bool | None) -> tuple[str, str]:
            if value is None:
                return "—", "#64748b"
            return ("Yes", "#dc2626") if value else ("No", "#16a34a")
        trend_score = summary.get("daily_trend_score")
        trend_label = summary.get("daily_trend", type(self).classify_trend_score(trend_score))
        confirmation_score = summary.get("confirmation_score")
        confirmation_max = summary.get("confirmation_max", CONFIRMATION_SCORE_MAX)
        momentum_max = summary.get("daily_trend_score_momentum_max", MOMENTUM_SCORE_MAX)
        setup_max = summary.get("daily_trend_score_quality_max", SETUP_QUALITY_SCORE_MAX)
        extended_total_score = summary.get("extended_total_score")
        extended_max_score = summary.get("extended_max_score", EXTENDED_BULLISH_SCORE_MAX)
        weighted_score = summary.get("weighted_technical_score")
        verdict_text = summary.get("overall_description", summary.get("weighted_technical_rating", "N/A"))
        if verdict_text == "N/A":
            verdict_text = trend_label
        extended_score_text = "N/A" if weighted_score is None else f"{int(weighted_score + 0.5)}/100"
        rvol20 = summary.get("daily_rvol20")
        rvol20_text = "N/A" if rvol20 is None or pd.isna(rvol20) else f"{rvol20:.2f}x"
        trend_phase = summary.get("trend_phase", "N/A")
        trend_direction = summary.get("trend_direction", "Stable")
        verdict_colors = {
            "Strongly Bullish": "#16a34a",
            "Bullish": "#65a30d",
            "Neutral / Mixed": "#64748b",
            "Bearish": "#f97316",
            "Strongly Bearish": "#dc2626",
            "Bullish but Extended": "#f97316",
            "Bullish Trend — High Pullback Risk": "#dc2626",
            "Bullish with Elevated Risk": "#f97316",
        }

        def score_color(passed: bool | None) -> str:
            if passed is None:
                return "#64748b"
            return "#16a34a" if passed else "#dc2626"

        def status_symbol(passed: bool | None) -> str:
            if passed is None:
                return "—"
            return "✓" if passed else "✗"

        def score_label(value: int | None, max_score: int, confirmation: bool = False) -> str:
            if value is None:
                return "N/A"
            if confirmation:
                if value >= 3:
                    return "Strong"
                if value == 2:
                    return "Mixed"
                if value == 1:
                    return "Weak"
                return "Bearish"
            ratio = value / max_score if max_score else 0
            if ratio >= 0.75:
                return "Bullish"
            if ratio >= 0.50:
                return "Mixed"
            if value > 0:
                return "Weak"
            return "Bearish"

        def section_score_label(title: str, value: int | None, max_score: int) -> str:
            if value is None:
                return "N/A"
            normalized_title = title.lower()
            ratio = value / max_score if max_score else 0
            if normalized_title in {"trend", "trend structure"}:
                if value >= 13:
                    return "Strongly Bullish"
                if value >= 9:
                    return "Bullish"
                if value >= 6:
                    return "Neutral / Mixed"
                if value >= 4:
                    return "Slightly Bearish"
                return "Bearish"
            if normalized_title == "momentum":
                if ratio >= 0.80:
                    return "Strong"
                if ratio >= 0.50:
                    return "Moderate"
                return "Weak"
            if normalized_title == "setup quality":
                if ratio >= 0.80:
                    return "Excellent"
                if ratio >= 0.60:
                    return "Good"
                if value > 0:
                    return "Fair"
                return "Poor"
            if normalized_title == "confirmation":
                if ratio >= 0.80:
                    return "Confirmed"
                if ratio >= 0.50:
                    return "Partial"
                if value > 0:
                    return "Weak"
                return "None"
            return score_label(value, max_score)

        def score_header(title: str, key: str, max_score: int, confirmation: bool = False) -> dict[str, str]:
            value = summary.get(key)
            if value is None:
                return {"title": title, "score": "N/A", "color": "#64748b"}
            label = section_score_label(title, int(value), max_score)
            color = status_color(label)
            return {"title": title, "score": f"{int(value)}/{max_score} {label}", "color": color}

        def trend_layer_score_text(score_key: str, label_key: str) -> str:
            value = summary.get(score_key)
            label = summary.get(label_key, "N/A")
            if value is None:
                return "N/A"
            return f"{int(value)}/5 • {label}"

        def trend_layer_color(label_key: str) -> str:
            return status_color(summary.get(label_key, "N/A"))

        def trend_layer_hierarchy_color(label_key: str) -> str:
            normalized = str(summary.get(label_key, "N/A")).lower()
            if normalized in {"strongly bullish", "bullish"}:
                return "#16a34a"
            if normalized in {"mixed", "neutral", "neutral / mixed", "slightly bearish"}:
                return "#f97316"
            if normalized in {"bearish", "strongly bearish"}:
                return "#dc2626"
            return "#64748b"

        def hierarchy_text(value: str) -> str:
            text = str(value or "Not enough data")
            if text == "Not enough data":
                return text
            parts = [part.strip() for part in text.replace("›", ">").split(">")]
            formatted_parts = [
                "[Price]" if part == "Price" else part
                for part in parts
                if part
            ]
            return " › ".join(formatted_parts) if formatted_parts else "Not enough data"

        def trend_state_color(value: str) -> str:
            text = str(value)
            if "Death Cross" in text or "\u2198" in text:
                return "#dc2626"
            if "Golden Cross" in text or "\u2197" in text:
                return "#16a34a"
            if "N/A" in text or "Not enough data" in text or "Neutral" in text or "\u2192" in text:
                return "#64748b"
            return status_color(text)

        def layer_title(label: str, horizon_key: str) -> str:
            horizon = summary.get(horizon_key, "")
            return f"{label} ({horizon})" if horizon else label

        def phase_direction_text(phase: str, direction: str) -> str:
            arrows = {
                "Improving": "\u2191",
                "Deteriorating": "\u2193",
                "Stable": "\u2192"
            }
            return f"{phase} {arrows.get(direction, '\u2192')}"

        def valid_distance_pass(key: str) -> bool | None:
            value = summary.get(key)
            if value is None or pd.isna(value):
                return None
            return value > 0

        def status_pass(key: str, passing_value: str = "Above") -> bool | None:
            value = summary.get(key, "N/A")
            if str(value).lower() == "n/a":
                return None
            return str(value).lower() == passing_value.lower()
        price_above_ema20 = valid_distance_pass("distance_daily_ema20")
        price_above_sma50 = valid_distance_pass("distance_daily_sma50")
        price_above_sma200 = valid_distance_pass("distance_daily_sma200")
        sma50_above_sma200 = status_pass("daily_sma50_vs_sma200")
        rsi_above_50 = None
        if type(self).is_valid_number(summary.get("daily_rsi14")):
            rsi_above_50 = summary.get("daily_rsi14") > 50
        macd_above_signal = status_pass("daily_macd_vs_signal", "Above Signal")
        macd_above_zero = status_pass("daily_macd_zero", "Above 0")
        volume_above_sma20 = status_pass("volume_vs_sma20")
        rvol_confirmed = None
        if type(self).is_valid_number(rvol20) and price_above_ema20 is not None:
            rvol_confirmed = rvol20 > 1.1 and price_above_ema20
        short_term_score_value = summary.get("short_term_trend_score")
        medium_term_score_value = summary.get("medium_term_trend_score")
        long_term_score_value = summary.get("long_term_trend_score")
        short_term_bullish = type(self).trend_layer_is_bullish(short_term_score_value)
        short_term_bearish = type(self).trend_layer_is_bearish(short_term_score_value)
        short_term_mixed = type(self).trend_layer_is_mixed(short_term_score_value)
        medium_term_bullish = type(self).trend_layer_is_bullish(medium_term_score_value)
        medium_term_bearish = type(self).trend_layer_is_bearish(medium_term_score_value)
        medium_term_mixed = type(self).trend_layer_is_mixed(medium_term_score_value)
        long_term_bullish = type(self).trend_layer_is_bullish(long_term_score_value)
        long_term_bearish = type(self).trend_layer_is_bearish(long_term_score_value)
        all_trend_layers_bullish = short_term_bullish and medium_term_bullish and long_term_bullish
        all_trend_layers_bearish = short_term_bearish and medium_term_bearish and long_term_bearish
        broader_trend_bullish = medium_term_bullish and long_term_bullish
        broader_trend_bearish = medium_term_bearish and long_term_bearish
        momentum_score = summary.get("daily_trend_score_momentum")
        setup_score = summary.get("daily_trend_score_quality")
        key_reason_candidates: list[dict[str, Any]] = []

        def add_reason(text: str, priority: int, category: str, polarity: str = "mixed") -> None:
            if text:
                key_reason_candidates.append({
                    "text": text,
                    "priority": priority,
                    "category": category,
                    "polarity": polarity
                })

        if all_trend_layers_bearish:
            add_reason("All trend layers bearish", 100, "trend_structure", "bearish")
            add_reason("Slow trend structurally bearish", 84, "trend_conflict", "bearish")
        elif all_trend_layers_bullish:
            add_reason("Trend layers aligned bullish", 100, "trend_structure", "bullish")
        elif short_term_bearish and long_term_bullish:
            add_reason("Fast pullback inside broader strength", 100, "trend_structure", "mixed")
            add_reason("Slow trend still supportive", 88, "trend_conflict", "bullish")
            if medium_term_bearish:
                add_reason("Intermediate trend has weakened", 74, "trend_conflict", "bearish")
        elif short_term_bullish and medium_term_bullish and long_term_bearish:
            add_reason("Fast and intermediate trends improving", 100, "trend_structure", "mixed")
            add_reason("Slow trend still blocks confirmation", 92, "trend_conflict", "bearish")
        elif short_term_bullish and long_term_bearish:
            add_reason("Early recovery attempt", 100, "trend_structure", "mixed")
            add_reason("Broader trend remains bearish", 90, "trend_conflict", "bearish")
        elif (short_term_mixed or short_term_bullish) and broader_trend_bearish:
            add_reason("Fast trend stabilizing", 96, "trend_structure", "mixed")
            add_reason("Broader trend remains bearish", 90, "trend_conflict", "bearish")
        elif short_term_bearish and broader_trend_bullish:
            add_reason("Fast trend pullback inside broader strength", 98, "trend_structure", "mixed")
            add_reason("Broader structure still supportive", 86, "trend_conflict", "bullish")
        elif long_term_bearish:
            add_reason("Slow trend still blocks confirmation", 84, "trend_structure", "bearish")
        elif long_term_bullish:
            add_reason("Slow trend still supportive", 80, "trend_structure", "bullish")
        elif medium_term_mixed:
            add_reason("Trend layers remain in transition", 76, "trend_structure", "mixed")

        if trend_direction == "Improving":
            if broader_trend_bearish and not all_trend_layers_bearish:
                add_reason("Short-term improvement within bearish structure", 78, "comparison", "mixed")
            else:
                add_reason("Trend structure improving", 64, "comparison", "bullish")
        elif trend_direction == "Deteriorating":
            add_reason("Trend structure deteriorating", 76, "comparison", "bearish")

        if momentum_score is not None:
            momentum_score_int = int(momentum_score)
            momentum_ratio = momentum_score_int / momentum_max if momentum_max else 0
            if momentum_ratio >= 0.80:
                if long_term_bearish or trend_phase in {"Early Recovery", "Recovery Attempt"}:
                    add_reason("Momentum supports rebound", 84, "momentum", "bullish")
                elif all_trend_layers_bullish:
                    add_reason("Momentum confirms upside", 84, "momentum", "bullish")
                else:
                    add_reason("Momentum remains strong", 80, "momentum", "bullish")
            elif momentum_ratio >= 0.50:
                if macd_above_signal is True and macd_above_zero is False:
                    add_reason("MACD turned up below zero", 82, "momentum", "mixed")
                elif trend_direction == "Improving":
                    add_reason("Momentum is improving", 78, "momentum", "bullish")
                else:
                    add_reason("Momentum constructive, not confirmed", 76, "momentum", "mixed")
            elif momentum_score_int > 0:
                if macd_above_signal is True and macd_above_zero is False:
                    add_reason("MACD up, momentum still weak", 82, "momentum", "mixed")
                elif all_trend_layers_bearish:
                    add_reason("Momentum remains weak", 82, "momentum", "bearish")
                else:
                    add_reason("Momentum not fully confirmed", 80, "momentum", "mixed")
            else:
                if short_term_bearish and long_term_bullish:
                    add_reason("Momentum has turned weak", 82, "momentum", "bearish")
                elif all_trend_layers_bearish:
                    add_reason("Momentum is clearly bearish", 82, "momentum", "bearish")
                else:
                    add_reason("Momentum does not support setup", 80, "momentum", "bearish")

        confirmation_score_int = int(confirmation_score) if confirmation_score is not None else None
        setup_score_int = int(setup_score) if setup_score is not None else None
        confirmation_ratio = (
            confirmation_score_int / confirmation_max
            if confirmation_score_int is not None and confirmation_max
            else None
        )
        setup_ratio = setup_score_int / setup_max if setup_score_int is not None and setup_max else None
        if setup_score_int is not None and confirmation_score_int is not None:
            if setup_ratio >= 0.80 and confirmation_ratio < 0.50:
                add_reason("Setup strong, confirmation weak", 74, "setup_confirmation", "mixed")
            elif setup_ratio >= 0.50 and confirmation_ratio < 0.50:
                text = "Setup acceptable, confirmation missing" if confirmation_score_int == 0 else "Setup acceptable, confirmation weak"
                add_reason(text, 74, "setup_confirmation", "mixed")

        if setup_score_int is not None:
            if setup_ratio >= 0.80 and (confirmation_ratio is None or confirmation_ratio >= 0.50):
                add_reason("Setup quality is strong", 68, "setup", "bullish")
            elif setup_ratio >= 0.50 and confirmation_score_int is None:
                add_reason("Setup is acceptable", 62, "setup", "mixed")
            elif setup_score_int > 0:
                add_reason("Setup quality is marginal", 58, "setup", "mixed")
            elif setup_score_int == 0:
                add_reason("Setup quality remains poor", 58, "setup", "bearish")

        if confirmation_score_int is not None:
            if confirmation_ratio >= 0.80:
                add_reason("Move has strong confirmation", 70, "confirmation", "bullish")
            elif confirmation_ratio >= 0.50:
                add_reason("Confirmation partly supports move", 68, "confirmation", "mixed")
            elif confirmation_score_int > 0 and setup_score_int is None:
                add_reason("Confirmation remains limited", 66, "confirmation", "bearish")
            elif confirmation_score_int == 0 and setup_score_int is None:
                add_reason("Confirmation is missing", 68, "confirmation", "bearish")

        daily_cross = summary.get("daily_cross", "N/A")
        if daily_cross in {"Death Cross", "Death State"}:
            add_reason("Death cross remains active", 72 if all_trend_layers_bearish else 62, "cross", "bearish")
        elif daily_cross in {"Golden Cross", "Golden State"}:
            add_reason("Golden cross remains active", 64 if long_term_bullish else 58, "cross", "bullish")

        if price_above_ema20 is True and price_above_sma200 is False:
            add_reason("Price reclaimed EMA20, below slow averages", 64, "price", "mixed")
        elif price_above_ema20 is False and price_above_sma200 is False:
            add_reason("Price below EMA20 and slow averages", 64, "price", "bearish")
        elif price_above_ema20 is True and price_above_sma200 is True:
            add_reason("Price holds above key averages", 56, "price", "bullish")
        elif price_above_sma200 is False:
            add_reason("Price remains below slow averages", 62, "price", "bearish")
        elif price_above_ema20 is False:
            add_reason("Price remains below EMA20", 58, "price", "bearish")

        for row in summary.get("score_changes_last_day", []):
            label = row.get("label", "")
            if "Momentum" in label and label.startswith("▲"):
                add_reason("Momentum improving", 56, "comparison", "bullish")
            elif "Momentum" in label and label.startswith("▼"):
                add_reason("Momentum faded", 58, "comparison", "bearish")
            elif "Confirmation" in label and label.startswith("▼"):
                add_reason("Confirmation faded", 58, "comparison", "bearish")

        def select_key_reasons(candidates: list[dict[str, Any]]) -> list[str]:
            selected: list[str] = []
            selected_categories: dict[str, int] = {}
            seen_text: set[str] = set()
            category_limits = {
                "trend_structure": 2,
                "trend_conflict": 2,
                "momentum": 1,
                "setup_confirmation": 1,
                "setup": 1,
                "confirmation": 1,
                "cross": 1,
                "price": 1,
                "comparison": 1
            }
            for candidate in sorted(candidates, key=lambda item: item["priority"], reverse=True):
                text = candidate["text"]
                normalized_text = " ".join(text.lower().replace(",", "").split())
                category = candidate["category"]
                if normalized_text in seen_text:
                    continue
                if selected_categories.get(category, 0) >= category_limits.get(category, 1):
                    continue
                if "confirmation" in normalized_text and any(
                    "confirmation" in existing.lower()
                    for existing in selected
                    if category != "cross"
                ):
                    continue
                selected.append(text)
                seen_text.add(normalized_text)
                selected_categories[category] = selected_categories.get(category, 0) + 1
                if len(selected) >= 6:
                    break
            return selected

        key_reasons = select_key_reasons(key_reason_candidates)

        def format_rvol_diagnostic(value: float | None) -> str:
            if value is None or pd.isna(value):
                return "N/A"
            if value >= 2:
                label = "High"
            elif value >= 1:
                label = "Normal"
            else:
                label = "Low"
            return f"{value:.2f}x ({label})"

        def format_atr_diagnostic(value: float | None) -> str:
            if value is None or pd.isna(value):
                return "N/A"
            state = summary.get("daily_atr_pct_state", "N/A")
            if state == "N/A":
                return f"{value:.2f}"
            return f"{value:.2f} ({state})"

        def metric_row(
            label: str,
            value: str,
            color: str = "#111827",
            bold_value: bool = False,
            indent: int = 0,
            height: float = 1.0,
            label_color: str | None = None
        ) -> dict[str, Any]:
            return {
                "kind": "metric",
                "label": label,
                "value": value,
                "color": color,
                "bold_value": bold_value,
                "indent": indent,
                "height": height,
                "label_color": label_color
            }

        def subgroup_header(
            label: str,
            value: str | None = None,
            color: str | None = None,
            height: float = 1.02
        ) -> dict[str, Any]:
            return {"kind": "subgroup", "label": label, "value": value, "color": color, "height": height}

        def row_spacer(height: float = 0.18) -> dict[str, Any]:
            return {"kind": "spacer", "height": height}
        trend_layer_header_height = 1.22
        trend_detail_height = 1.04
        sections = [
            (
                "Period",
                [
                    metric_row("End/Current Price", format_price(summary.get("period_end_price", current_price))),
                    metric_row("Start Price", format_price(summary.get("period_start_price"))),
                    metric_row("Period Change", self.format_summary_percent(summary.get("period_change")), distance_color(summary.get("period_change")), True),
                    metric_row("Average Price", format_price(summary.get("period_average_price"))),
                    metric_row("End vs Average", self.format_summary_percent(summary.get("period_end_vs_average")), distance_color(summary.get("period_end_vs_average")), True)
                ]
            ),
            (
                score_header("Trend Structure", "daily_trend_score_trend", TREND_STRUCTURE_SCORE_MAX),
                [
                    subgroup_header(layer_title("Fast", "fast_trend_horizon"), trend_layer_score_text("short_term_trend_score", "short_term_trend_label"), trend_layer_color("short_term_trend_label"), trend_layer_header_height),
                    metric_row(hierarchy_text(summary.get("fast_trend_hierarchy", "Not enough data")), "", trend_layer_hierarchy_color("short_term_trend_label"), False, 1, trend_detail_height, trend_layer_hierarchy_color("short_term_trend_label")),
                    metric_row(summary.get("fast_trend_state", "EMA20 N/A"), "", trend_state_color(summary.get("fast_trend_state", "EMA20 N/A")), False, 1, trend_detail_height, trend_state_color(summary.get("fast_trend_state", "EMA20 N/A"))),
                    row_spacer(),
                    subgroup_header(layer_title("Intermediate", "intermediate_trend_horizon"), trend_layer_score_text("medium_term_trend_score", "medium_term_trend_label"), trend_layer_color("medium_term_trend_label"), trend_layer_header_height),
                    metric_row(hierarchy_text(summary.get("intermediate_trend_hierarchy", "Not enough data")), "", trend_layer_hierarchy_color("medium_term_trend_label"), False, 1, trend_detail_height, trend_layer_hierarchy_color("medium_term_trend_label")),
                    metric_row(summary.get("intermediate_trend_state", "EMA50 N/A"), "", trend_state_color(summary.get("intermediate_trend_state", "EMA50 N/A")), False, 1, trend_detail_height, trend_state_color(summary.get("intermediate_trend_state", "EMA50 N/A"))),
                    row_spacer(),
                    subgroup_header(layer_title("Slow", "slow_trend_horizon"), trend_layer_score_text("long_term_trend_score", "long_term_trend_label"), trend_layer_color("long_term_trend_label"), trend_layer_header_height),
                    metric_row(hierarchy_text(summary.get("slow_trend_hierarchy", "Not enough data")), "", trend_layer_hierarchy_color("long_term_trend_label"), False, 1, trend_detail_height, trend_layer_hierarchy_color("long_term_trend_label")),
                    metric_row(summary.get("slow_trend_cross_state", "Cross Neutral"), "", trend_state_color(summary.get("slow_trend_cross_state", "Cross Neutral")), False, 1, trend_detail_height, trend_state_color(summary.get("slow_trend_cross_state", "Cross Neutral"))),
                    metric_row(summary.get("slow_trend_sma200_state", "SMA200 N/A"), "", trend_state_color(summary.get("slow_trend_sma200_state", "SMA200 N/A")), False, 1, trend_detail_height, trend_state_color(summary.get("slow_trend_sma200_state", "SMA200 N/A"))),
                    row_spacer(0.24),
                    subgroup_header("Phase", phase_direction_text(trend_phase, trend_direction), status_color(trend_phase), 1.12)
                ]
            ),
            (
                score_header("Momentum", "daily_trend_score_momentum", momentum_max),
                [
                    metric_row("RSI14 > 50", format_rsi14(), score_color(rsi_above_50)),
                    metric_row("RSI Direction", summary.get("rsi_direction", "N/A"), status_color(summary.get("rsi_direction", "N/A"))),
                    metric_row("MACD vs Signal", summary.get("daily_macd_vs_signal", "N/A"), score_color(macd_above_signal)),
                    metric_row("MACD vs 0", summary.get("daily_macd_zero", "N/A"), score_color(macd_above_zero)),
                    metric_row("MACD Histogram", summary.get("macd_histogram_direction", "N/A"), status_color(summary.get("macd_histogram_direction", "N/A"))),
                    metric_row(
                        "Bearish Divergence",
                        *risk_status(summary.get("rsi_bearish_divergence") or summary.get("macd_bearish_divergence"))
                    )
                ]
            ),
            (
                score_header("Setup Quality", "daily_trend_score_quality", setup_max),
                [
                    metric_row("Volume vs SMA20", format_signed_percent(summary.get("distance_volume_sma20")), distance_color(summary.get("distance_volume_sma20")), True),
                    metric_row("EMA20 Ext <=8%", format_extension("daily_ema20_extension_state", "daily_ema20_extension"), status_color(summary.get("daily_ema20_extension_state", "N/A"))),
                    metric_row("SMA200 Ext <=20%", format_extension("daily_sma200_extension_state", "daily_sma200_extension"), status_color(summary.get("daily_sma200_extension_state", "N/A"))),
                    metric_row("ATR Extension", format_atr_extension(), atr_extension_color()),
                    metric_row("Bollinger Failure", *risk_status(summary.get("bollinger_breakout_failure")))
                ]
            ),
            (
                score_header("Confirmation", "confirmation_score", confirmation_max, confirmation=True),
                [
                    metric_row("RVOL Confirmation", status_symbol(rvol_confirmed), score_color(rvol_confirmed), True),
                    metric_row("RVOL20", rvol20_text, rvol_color(rvol20)),
                    metric_row("Low-Volume New High", *risk_status(summary.get("low_volume_new_high"))),
                    metric_row("Rejection Candle", *risk_status(summary.get("spike_rejection_candle"))),
                    metric_row("Volume vs SMA20", format_signed_percent(summary.get("distance_volume_sma20")), distance_color(summary.get("distance_volume_sma20")), True),
                    metric_row("ATR% Range", f"{status_symbol(status_pass('daily_atr_pct_state', 'Healthy'))} {summary.get('daily_atr_pct_state', 'N/A')}", status_color(summary.get("daily_atr_pct_state", "N/A")))
                ]
            )
        ]
        card_left = 0.03
        card_width = 0.94
        card_right = card_left + card_width
        card_top = card_bottom + card_height
        verdict_color = verdict_colors.get(verdict_text, status_color(verdict_text))
        previous_change_title = f"Since {summary.get('score_changes_previous_title', 'Previous Bar')}"
        score_change_groups = [
            (previous_change_title, summary.get("score_changes_last_day", [])),
            ("Since Period Start", summary.get("score_changes_period_start", []))
        ]
        layout = {
            "left_x": card_left + 0.016,
            "right_x": card_right - 0.016,
            "header_metric_value_x": card_left + (card_width * 0.44),
            "indent_x": 0.018,
            "top_pad": 0.022,
            "bottom_pad": 0.016,
            "header_box_pad": 0.008,
            "section_gap": 0.42,
            "subgroup_gap": 0.24,
            "row_gap": 1.0,
            "header_gap": 0.56,
            "title_font_size": 10.6,
            "signal_font_size": 9.4 if len(verdict_text) > 25 else 12.4,
            "header_metric_font_size": 7.3,
            "section_font_size": 7.4,
            "subgroup_font_size": 5.7,
            "row_font_size": 6.7,
            "title_weight": "bold",
            "signal_weight": "bold",
            "section_weight": "bold",
            "subgroup_weight": "bold",
            "metric_weight": "normal",
            "header_metric_value_weight": "bold",
            "label_color": "#374151",
            "title_color": "#111827",
            "subgroup_color": "#4b5563",
            "muted_color": "#64748b",
            "divider_color": "#e5e7eb",
            "card_fill": "#f8fafc"
        }
        style_map = {
            "title": {"fontsize": layout["title_font_size"], "fontweight": layout["title_weight"], "color": layout["title_color"]},
            "signal": {"fontsize": layout["signal_font_size"], "fontweight": layout["signal_weight"], "color": verdict_color},
            "header_metric_label": {"fontsize": layout["header_metric_font_size"], "fontweight": layout["metric_weight"], "color": layout["label_color"]},
            "header_metric_value": {"fontsize": layout["header_metric_font_size"], "fontweight": layout["header_metric_value_weight"], "color": layout["title_color"]},
            "section_header": {"fontsize": layout["section_font_size"], "fontweight": layout["section_weight"], "color": layout["title_color"]},
            "subgroup_header": {"fontsize": layout["subgroup_font_size"], "fontweight": layout["subgroup_weight"], "color": layout["subgroup_color"]},
            "metric_label": {"fontsize": layout["row_font_size"], "fontweight": layout["metric_weight"], "color": layout["label_color"]},
            "metric_value": {"fontsize": layout["row_font_size"], "fontweight": layout["metric_weight"], "color": layout["title_color"]},
            "muted_value": {"fontsize": layout["row_font_size"], "fontweight": layout["metric_weight"], "color": layout["muted_color"]}
        }

        def header_metric_block(
            label: str,
            value: str,
            label_x: float,
            value_x: float,
            color: str | None = None
        ) -> dict[str, Any]:
            return {
                "type": "header_metric",
                "label": label,
                "value": value,
                "label_x": layout["left_x"],
                "value_x": layout["header_metric_value_x"],
                "color": color,
                "height": 1.28
            }
        blocks: list[dict[str, Any]] = [
            {"type": "title", "label": "Signal Summary", "height": 1.62},
            {"type": "signal", "label": verdict_text, "color": verdict_color, "height": 1.66},
            {"type": "spacer", "height": 0.18},
            header_metric_block("Score", extended_score_text, layout["left_x"], layout["header_metric_value_x"], verdict_color),
            {
                "type": "weighted_summary",
                "label": (
                    f"{TECHNICAL_SCORE_WEIGHTS['trend']:.0%} Trend Structure,  "
                    f"{TECHNICAL_SCORE_WEIGHTS['momentum']:.0%} Momentum"
                ),
                "height": 1.12,
            },
            {
                "type": "weighted_summary",
                "label": (
                    f"{TECHNICAL_SCORE_WEIGHTS['setup']:.0%} Setup Quality,  "
                    f"{TECHNICAL_SCORE_WEIGHTS['confirmation']:.0%} Confirmation"
                ),
                "height": 1.12,
            },
            {"type": "divider", "height": 0.44},
            {"type": "key_reason_header", "label": "Key Reasons", "height": 1.12}
        ]
        blocks.extend(
            {"type": "key_reason", "label": reason, "height": 0.98}
            for reason in key_reasons
        )
        blocks.append({"type": "divider", "height": 0.44})
        has_score_changes = False
        for change_title, change_rows in score_change_groups:
            if not change_rows:
                continue
            if has_score_changes:
                blocks.append({"type": "divider", "height": 0.44})
            has_score_changes = True
            blocks.append({"type": "change_header", "label": change_title, "height": 1.08})
            blocks.extend(
                {
                    "type": "change_row",
                    "label": row["label"],
                    "value": row["value"],
                    "color": row["color"],
                    "height": 0.92
                }
                for row in change_rows
            )
        if has_score_changes:
            blocks.append({"type": "divider", "height": 0.44})
        for section_index, (section, section_rows) in enumerate(sections):
            if isinstance(section, dict):
                section_block = {
                    "type": "section_header",
                    "label": section["title"],
                    "value": section["score"],
                    "color": section["color"],
                    "height": 1.18,
                    "divider": section_index > 0
                }
            else:
                section_block = {"type": "section_header", "label": section, "height": 1.18, "divider": section_index > 0}
            blocks.append(section_block)
            for row in section_rows:
                if row["kind"] == "spacer":
                    blocks.append({"type": "spacer", "height": row.get("height", 0.18)})
                    continue
                if row["kind"] == "subgroup":
                    blocks.append({
                        "type": "subgroup_header",
                        "label": row["label"],
                        "value": row.get("value"),
                        "color": row.get("color"),
                        "height": row.get("height", 1.02)
                    })
                else:
                    blocks.append({
                        "type": "metric_row",
                        "label": row["label"],
                        "value": row["value"],
                        "color": row.get("color"),
                        "label_color": row.get("label_color"),
                        "bold": row.get("bold_value", False),
                        "indent": row.get("indent", 0),
                        "height": row.get("height", 1.0)
                    })
            blocks.append({"type": "spacer", "height": 0.44})
        available_height = card_height - layout["top_pad"] - layout["bottom_pad"]
        required_units = sum(block["height"] for block in blocks)
        base_gap = min(0.0165, available_height / max(required_units, 1))
        if base_gap < 0.0125:
            base_gap = available_height / max(required_units, 1)
            font_scale = max(0.72, min(1.0, base_gap / 0.0145))
            for style in style_map.values():
                style["fontsize"] *= font_scale
        layout["row_gap"] = base_gap
        layout["section_gap"] = base_gap * layout["section_gap"]
        layout["subgroup_gap"] = base_gap * layout["subgroup_gap"]
        layout["header_gap"] = base_gap * layout["header_gap"]
        y = card_top - layout["top_pad"]
        for block in blocks:
            block["y"] = y
            y -= block["height"] * base_gap
            block["next_y"] = y
        if y < card_bottom + layout["bottom_pad"] - 1e-6:
            print(
                "Signal Summary layout warning: required content exceeds available card height "
                f"by {(card_bottom + layout['bottom_pad'] - y):.3f} axes units"
            )
        card = FancyBboxPatch(
            (card_left, card_bottom),
            card_width,
            card_height,
            boxstyle="round,pad=0.012",
            transform=ax.transAxes,
            facecolor="white",
            edgecolor="#d1d5db",
            linewidth=0.9,
            alpha=0.94,
            zorder=6
        )
        ax.add_patch(card)
        text_artists: list[Any] = []

        def add_text(**kwargs: Any) -> Any:
            artist = ax.text(transform=ax.transAxes, zorder=7, **kwargs)
            text_artists.append(artist)
            return artist

        def draw_header_metric(ax: Any, block: dict[str, Any]) -> float:
            label_style = style_map["section_header"]
            value_style = style_map["section_header"].copy()
            value_style["color"] = block.get("color") or value_style["color"]
            add_text(
                x=block["label_x"],
                y=block["y"],
                s=block["label"],
                ha="left",
                va="top",
                **label_style
            )
            add_text(
                x=block["value_x"],
                y=block["y"],
                s=block["value"],
                ha="right",
                va="top",
                **value_style
            )
            return block["next_y"]

        def draw_section_header(ax: Any, block: dict[str, Any]) -> float:
            if block.get("divider"):
                ax.plot(
                    [layout["left_x"], layout["right_x"]],
                    [block["y"] + base_gap * 0.26, block["y"] + base_gap * 0.26],
                    transform=ax.transAxes,
                    color=layout["divider_color"],
                    linewidth=0.65,
                    zorder=6
                )
            add_text(x=layout["left_x"], y=block["y"], s=block["label"], ha="left", va="top", **style_map["section_header"])
            if block.get("value"):
                value_style = style_map["section_header"].copy()
                value_style["color"] = block.get("color") or value_style["color"]
                add_text(x=layout["right_x"], y=block["y"], s=block["value"], ha="right", va="top", **value_style)
            return block["next_y"]

        def draw_divider(ax: Any, block: dict[str, Any]) -> float:
            line_y = (block["y"] + block["next_y"]) / 2
            ax.plot(
                [layout["left_x"], layout["right_x"]],
                [line_y, line_y],
                transform=ax.transAxes,
                color=layout["divider_color"],
                linewidth=0.65,
                zorder=6
            )
            return block["next_y"]

        def draw_subgroup_header(ax: Any, block: dict[str, Any]) -> float:
            add_text(x=layout["left_x"], y=block["y"], s=block["label"], ha="left", va="top", **style_map["subgroup_header"])
            if block.get("value"):
                value_style = style_map["subgroup_header"].copy()
                value_style["color"] = block.get("color") or value_style["color"]
                add_text(x=layout["right_x"], y=block["y"], s=block["value"], ha="right", va="top", **value_style)
            return block["next_y"]

        def draw_metric_row(
            ax: Any,
            block: dict[str, Any]
        ) -> float:
            label_x = layout["left_x"] + (block.get("indent", 0) * layout["indent_x"])
            label_style = style_map["metric_label"].copy()
            label_style["color"] = block.get("label_color") or label_style["color"]
            value_style = style_map["metric_value"].copy()
            value_style["color"] = block.get("color") or value_style["color"]
            value_text = str(block["value"]).upper() if block["label"] == "Volume Trend" else str(block["value"])
            add_text(x=label_x, y=block["y"], s=block["label"], ha="left", va="top", **label_style)
            add_text(x=layout["right_x"], y=block["y"], s=value_text, ha="right", va="top", **value_style)
            return block["next_y"]
        for block in blocks:
            block_type = block["type"]
            if block_type == "spacer":
                _next_y = block["next_y"]
                continue
            if block_type == "divider":
                _next_y = draw_divider(ax, block)
                continue
            if block_type == "title":
                add_text(x=layout["left_x"], y=block["y"], s=block["label"], ha="left", va="top", **style_map["title"])
                _next_y = block["next_y"]
            elif block_type == "signal":
                signal_style = style_map["signal"].copy()
                signal_style["color"] = block.get("color") or signal_style["color"]
                add_text(x=layout["right_x"], y=block["y"], s=block["label"], ha="right", va="top", **signal_style)
                _next_y = block["next_y"]
            elif block_type == "header_metric":
                _next_y = draw_header_metric(ax, block)
            elif block_type == "weighted_summary":
                add_text(x=layout["left_x"], y=block["y"], s=block["label"], ha="left", va="top", **style_map["metric_label"])
                _next_y = block["next_y"]
            elif block_type == "key_reason_header":
                add_text(x=layout["left_x"], y=block["y"], s=block["label"], ha="left", va="top", **style_map["section_header"])
                _next_y = block["next_y"]
            elif block_type == "key_reason":
                add_text(x=layout["left_x"], y=block["y"], s=f"- {block['label']}", ha="left", va="top", **style_map["metric_label"])
                _next_y = block["next_y"]
            elif block_type == "change_header":
                add_text(x=layout["left_x"], y=block["y"], s=block["label"], ha="left", va="top", **style_map["section_header"])
                _next_y = block["next_y"]
            elif block_type == "change_row":
                _next_y = draw_metric_row(ax, block)
            elif block_type == "section_header":
                _next_y = draw_section_header(ax, block)
            elif block_type == "subgroup_header":
                _next_y = draw_subgroup_header(ax, block)
            elif block_type == "metric_row":
                _next_y = draw_metric_row(ax, block)

        def warn_on_text_overlap() -> None:
            try:
                ax.figure.canvas.draw()
                renderer = ax.figure.canvas.get_renderer()
                boxes = []
                for artist in text_artists:
                    bbox = artist.get_window_extent(renderer=renderer).expanded(1.0, 1.04)
                    if bbox.width > 0 and bbox.height > 0:
                        boxes.append((artist, bbox))
                for index, (artist_a, bbox_a) in enumerate(boxes):
                    for artist_b, bbox_b in boxes[index + 1:]:
                        if bbox_a.overlaps(bbox_b):
                            print(
                                "Signal Summary layout warning: overlapping text "
                                f"'{artist_a.get_text()}' and '{artist_b.get_text()}'"
                            )
                            return
            except Exception as exc:
                print(f"Signal Summary layout warning: overlap check failed: {exc}")
        warn_on_text_overlap()
