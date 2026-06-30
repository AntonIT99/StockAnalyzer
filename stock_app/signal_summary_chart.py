"""Signal summary dashboard drawing."""

from typing import Any
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from .config import CONFIRMATION_SCORE_MAX, EXTENDED_BULLISH_SCORE_MAX

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
            if normalized in {"above", "above signal", "above 0", "rising", "bullish", "strong bullish", "bullish confirmed", "strong bullish confirmed", "golden cross", "golden state", "cheap", "strong", "confirmed", "excellent", "good", "stable", "attractive", "ok", "healthy"}:
                return "#16a34a"
            if normalized in {"partial", "moderate", "fair"}:
                return "#f97316"
            if normalized in {"below", "below signal", "below 0", "falling", "bearish", "strong bearish", "strongly bearish", "weak / bearish", "death cross", "death state", "expensive", "weak", "none", "poor", "risky", "extended", "outside range"}:
                return "#dc2626"
            if normalized in {"mixed", "neutral", "n/a", "unknown", "watchlist"}:
                return "#64748b"
            return "#0ea5e9"

        def confirmation_score_color(value: int) -> str:
            if value is None:
                return "#64748b"
            if value >= 3:
                return "#16a34a"
            if value <= 1:
                return "#dc2626"
            return "#64748b"

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

        def format_ema50_trend() -> str:
            ema50_change = self.format_summary_percent(summary.get("daily_ema50_change_20"))
            if ema50_change == "N/A":
                return summary.get("daily_ema50_trend", "N/A")
            return f"{summary.get('daily_ema50_trend', 'N/A')} {ema50_change}"

        def format_rsi14() -> str:
            rsi = summary.get("daily_rsi14")
            return "N/A" if rsi is None or pd.isna(rsi) else f"{rsi:.1f}"

        def format_extension(state_key: str, distance_key: str) -> str:
            state = summary.get(state_key, "N/A")
            distance = self.format_summary_percent(summary.get(distance_key))
            if distance == "N/A":
                return state
            return distance
        trend_score = summary.get("daily_trend_score")
        trend_label = summary.get("daily_trend", type(self).classify_trend_score(trend_score))
        confirmation_score = summary.get("confirmation_score")
        confirmation_max = summary.get("confirmation_max", CONFIRMATION_SCORE_MAX)
        extended_total_score = summary.get("extended_total_score")
        extended_max_score = summary.get("extended_max_score", EXTENDED_BULLISH_SCORE_MAX)
        extended_rating = summary.get("extended_rating", "N/A")
        verdict_text = extended_rating if extended_rating != "N/A" else trend_label
        extended_score_text = "N/A" if extended_total_score is None else f"{int(extended_total_score)}/{extended_max_score}"
        rvol20 = summary.get("daily_rvol20")
        rvol20_text = "N/A" if rvol20 is None or pd.isna(rvol20) else f"{rvol20:.2f}x"

        def score_color(passed: bool | None) -> str:
            if passed is None:
                return "#64748b"
            return "#16a34a" if passed else "#dc2626"

        def status_symbol(passed: bool | None) -> str:
            if passed is None:
                return "—"
            return "✓" if passed else "✗"

        def bool_score_text(passed: bool | None, text: str) -> str:
            if passed is None:
                return f"N/A {text}"
            return f"{1 if passed else 0}/1 {text}"

        def compact_count_score_text(passed_values: list[bool | None], max_score: int) -> str:
            valid_values = [value for value in passed_values if value is not None]
            if not valid_values:
                return "N/A"
            passed_count = sum(1 for value in valid_values if value)
            return f"{passed_count}/{max_score}"

        def count_score_color(passed_values: list[bool | None], max_score: int) -> str:
            valid_values = [value for value in passed_values if value is not None]
            if not valid_values:
                return "#64748b"
            passed_count = sum(1 for value in valid_values if value)
            return status_color(score_label(passed_count, max_score))

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
            if normalized_title == "trend":
                if ratio >= 0.75:
                    return "Bullish"
                if ratio >= 0.50:
                    return "Neutral"
                return "Bearish"
            if normalized_title == "momentum":
                if value >= max_score:
                    return "Strong"
                if value >= max(2, int(max_score * 0.50)):
                    return "Moderate"
                return "Weak"
            if normalized_title == "setup quality":
                if value >= max_score:
                    return "Excellent"
                if value >= max_score - 1:
                    return "Good"
                if value > 0:
                    return "Fair"
                return "Poor"
            if normalized_title == "confirmation":
                if value >= max_score:
                    return "Confirmed"
                if value >= max_score - 1:
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
        ema20_above_ema50 = status_pass("daily_ema20_vs_ema50")
        ema50_above_ema100 = status_pass("daily_ema50_vs_ema100")
        ema100_above_ema200 = status_pass("daily_ema100_vs_ema200")
        sma50_above_sma200 = status_pass("daily_sma50_vs_sma200")
        ema50_rising = status_pass("daily_ema50_trend", "Rising")
        rsi_above_50 = None
        if type(self).is_valid_number(summary.get("daily_rsi14")):
            rsi_above_50 = summary.get("daily_rsi14") > 50
        macd_above_signal = status_pass("daily_macd_vs_signal", "Above Signal")
        macd_above_zero = status_pass("daily_macd_zero", "Above 0")
        volume_above_sma20 = status_pass("volume_vs_sma20")
        rvol_confirmed = None
        if type(self).is_valid_number(rvol20) and price_above_ema20 is not None:
            rvol_confirmed = rvol20 > 1.1 and price_above_ema20
        ema_stack_values = [ema20_above_ema50, ema50_above_ema100, ema100_above_ema200]
        ema_stack_score = compact_count_score_text(ema_stack_values, 3)
        price_position_values = [price_above_ema20, price_above_sma50, price_above_sma200]
        price_position_score = compact_count_score_text(price_position_values, 3)
        long_term_trend_values = [sma50_above_sma200, ema50_rising]
        long_term_trend_score = compact_count_score_text(long_term_trend_values, 2)
        key_reasons = []

        def add_key_reason(reason: str) -> None:
            if reason and reason not in key_reasons:
                key_reasons.append(reason)
        if summary.get("daily_ema_stack") == "Bearish":
            add_key_reason("Major bearish trend confirmed")
        elif summary.get("daily_ema_stack") == "Bullish":
            add_key_reason("Major bullish trend confirmed")
        if price_above_ema20 is False and price_above_sma200 is False:
            add_key_reason("Price below EMA20 and SMA200")
        elif price_above_ema20 is True and price_above_sma200 is True:
            add_key_reason("Price above EMA20 and SMA200")
        elif price_above_ema20 is False:
            add_key_reason("Price below EMA20")
        elif price_above_sma200 is False:
            add_key_reason("Price below long-term average")
        elif price_above_ema20 is True:
            add_key_reason("Price above EMA20")
        elif price_above_sma200 is True:
            add_key_reason("Price above long-term average")
        if rsi_above_50 is False and (macd_above_signal is False or macd_above_zero is False):
            add_key_reason("Momentum remains weak")
        elif rsi_above_50 is True and macd_above_signal is True:
            add_key_reason("Momentum supports trend")
        if macd_above_signal is False:
            add_key_reason("MACD still bearish")
        elif macd_above_signal is True:
            add_key_reason("MACD supports upside")
        if rsi_above_50 is False:
            add_key_reason("RSI remains below 50")
        elif rsi_above_50 is True:
            add_key_reason("RSI holds above 50")
        if sma50_above_sma200 is False:
            add_key_reason("Long-term cross remains bearish")
        elif sma50_above_sma200 is True:
            add_key_reason("Long-term cross remains bullish")
        if price_above_sma50 is False:
            add_key_reason("Price below SMA50")
        elif price_above_sma50 is True:
            add_key_reason("Price above SMA50")
        if volume_above_sma20 is False:
            add_key_reason("Volume below 20-day average")
        elif volume_above_sma20 is True:
            add_key_reason("Volume above 20-day average")
        key_reasons = [reason for reason in key_reasons if reason][:6]

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
            indent: int = 0
        ) -> dict[str, Any]:
            return {
                "kind": "metric",
                "label": label,
                "value": value,
                "color": color,
                "bold_value": bold_value,
                "indent": indent
            }

        def subgroup_header(label: str, value: str | None = None, color: str | None = None) -> dict[str, Any]:
            return {"kind": "subgroup", "label": label, "value": value, "color": color}
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
                score_header("Trend", "daily_trend_score_trend", 8),
                [
                    subgroup_header("Price Position", price_position_score, count_score_color(price_position_values, 3)),
                    metric_row("Price vs EMA20", format_signed_percent(summary.get("distance_daily_ema20")), distance_color(summary.get("distance_daily_ema20")), True, 1),
                    metric_row("Price vs SMA50", format_signed_percent(summary.get("distance_daily_sma50")), distance_color(summary.get("distance_daily_sma50")), True, 1),
                    metric_row("Price vs SMA200", format_signed_percent(summary.get("distance_daily_sma200")), distance_color(summary.get("distance_daily_sma200")), True, 1),
                    subgroup_header("EMA Structure", ema_stack_score, count_score_color(ema_stack_values, 3)),
                    metric_row("EMA20 > EMA50", status_symbol(ema20_above_ema50), score_color(ema20_above_ema50), False, 1),
                    metric_row("EMA50 > EMA100", status_symbol(ema50_above_ema100), score_color(ema50_above_ema100), False, 1),
                    metric_row("EMA100 > EMA200", status_symbol(ema100_above_ema200), score_color(ema100_above_ema200), False, 1),
                    subgroup_header("Long-Term Trend", long_term_trend_score, count_score_color(long_term_trend_values, 2)),
                    metric_row("Daily Cross (SMA50 > SMA200)", summary.get("daily_cross", "N/A"), score_color(sma50_above_sma200), True, 1),
                    metric_row("EMA50 Trend", format_ema50_trend(), status_color(summary.get("daily_ema50_trend", "N/A")), False, 1)
                ]
            ),
            (
                score_header("Momentum", "daily_trend_score_momentum", 3),
                [
                    metric_row("RSI14 > 50", format_rsi14(), score_color(rsi_above_50)),
                    metric_row("MACD vs Signal", summary.get("daily_macd_vs_signal", "N/A"), score_color(macd_above_signal)),
                    metric_row("MACD vs 0", summary.get("daily_macd_zero", "N/A"), score_color(macd_above_zero))
                ]
            ),
            (
                score_header("Setup Quality", "daily_trend_score_quality", 3),
                [
                    metric_row("Volume vs SMA20", format_signed_percent(summary.get("distance_volume_sma20")), distance_color(summary.get("distance_volume_sma20")), True),
                    metric_row("EMA20 Ext <=8%", format_extension("daily_ema20_extension_state", "daily_ema20_extension"), status_color(summary.get("daily_ema20_extension_state", "N/A"))),
                    metric_row("SMA200 Ext <=20%", format_extension("daily_sma200_extension_state", "daily_sma200_extension"), status_color(summary.get("daily_sma200_extension_state", "N/A")))
                ]
            ),
            (
                score_header("Confirmation", "confirmation_score", confirmation_max, confirmation=True),
                [
                    metric_row("RVOL20>1.1 + EMA20", status_symbol(rvol_confirmed), score_color(rvol_confirmed), True),
                    metric_row("RVOL20", rvol20_text, rvol_color(rvol20)),
                    metric_row("Volume vs SMA20", format_signed_percent(summary.get("distance_volume_sma20")), distance_color(summary.get("distance_volume_sma20")), True),
                    metric_row("ATR% Range", f"{status_symbol(status_pass('daily_atr_pct_state', 'Healthy'))} {summary.get('daily_atr_pct_state', 'N/A')}", status_color(summary.get("daily_atr_pct_state", "N/A")))
                ]
            ),
            (
                "Diagnostics",
                [
                    metric_row("Volume Trend", summary.get("volume_trend", "Neutral"), status_color(summary.get("volume_trend", "Neutral")), True),
                    metric_row("Relative Volume", format_rvol_diagnostic(current_rvol), rvol_color(current_rvol)),
                    metric_row("ATR14", format_atr_diagnostic(atr14), status_color(summary.get("daily_atr_pct_state", "N/A")))
                ]
            ),
            (
                "Market Context",
                [
                    metric_row("From Daily 52W High", self.format_summary_percent(summary.get("distance_52w_high")), from_52w_high_color(summary.get("distance_52w_high"))),
                    metric_row("From Daily 52W Low", self.format_summary_percent(summary.get("distance_52w_low")), from_52w_low_color(summary.get("distance_52w_low"))),
                    metric_row("Valuation", summary.get("valuation", "Unknown"), status_color(summary.get("valuation", "Unknown"))),
                    metric_row("Business", summary.get("business_health", "Unknown"), status_color(summary.get("business_health", "Unknown"))),
                    metric_row("Investment View", summary.get("investment_view", "Watchlist"), status_color(summary.get("investment_view", "Watchlist")))
                ]
            )
        ]
        card_left = 0.03
        card_width = 0.94
        card_right = card_left + card_width
        card_top = card_bottom + card_height
        verdict_color = status_color(verdict_text)
        score_change_groups = [
            ("Since Last Day", summary.get("score_changes_last_day", [])),
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
            "signal_font_size": 12.4,
            "header_metric_font_size": 7.3,
            "section_font_size": 8.0,
            "subgroup_font_size": 6.4,
            "row_font_size": 6.7,
            "title_weight": "bold",
            "signal_weight": "bold",
            "section_weight": "bold",
            "subgroup_weight": "normal",
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
                "height": 1.0
            }
        blocks: list[dict[str, Any]] = [
            {"type": "title", "label": "Signal Summary", "height": 1.62},
            {"type": "signal", "label": verdict_text, "color": verdict_color, "height": 1.66},
            {"type": "spacer", "height": 0.18},
            header_metric_block("Score", extended_score_text, layout["left_x"], layout["header_metric_value_x"], verdict_color),
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
            blocks.append({"type": "change_header", "label": change_title, "height": 0.92})
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
                if row["kind"] == "subgroup":
                    blocks.append({
                        "type": "subgroup_header",
                        "label": row["label"],
                        "value": row.get("value"),
                        "color": row.get("color"),
                        "height": 1.02
                    })
                else:
                    blocks.append({
                        "type": "metric_row",
                        "label": row["label"],
                        "value": row["value"],
                        "color": row.get("color"),
                        "bold": row.get("bold_value", False),
                        "indent": row.get("indent", 0),
                        "height": 1.0
                    })
            blocks.append({"type": "spacer", "height": 0.44})
        available_height = card_height - layout["top_pad"] - layout["bottom_pad"]
        required_units = sum(block["height"] for block in blocks)
        base_gap = min(0.0165, available_height / max(required_units, 1))
        if base_gap < 0.0125:
            base_gap = max(0.0112, available_height / max(required_units, 1))
            font_scale = max(0.88, min(1.0, base_gap / 0.0125))
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
            label_style = style_map["metric_label"]
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
