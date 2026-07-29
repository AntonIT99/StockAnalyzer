"""Detailed pullback-risk dashboard drawing."""

from typing import Any

from matplotlib.patches import FancyBboxPatch

from .config import PullbackRiskConfig


class RiskDashboardMixin:
    def draw_risk_dashboard(
        self,
        ax: Any,
        summary: dict[str, Any],
        card_bottom: float = 0.03,
        card_height: float = 0.94,
        include_context: bool = False,
    ) -> None:
        ax.set_axis_off()
        card_left = 0.03
        card_width = 0.94
        card_right = card_left + card_width
        card_top = card_bottom + card_height
        left = card_left + 0.022
        context_divider = card_left + card_width * 0.64 if include_context else card_right
        right = context_divider - 0.022
        risk_score = summary.get("pullback_risk_score")
        risk_label = summary.get("pullback_risk_label", "N/A")
        categories = summary.get("pullback_risk_categories", {})
        raw_categories = summary.get("pullback_risk_raw_categories", {})
        details = summary.get("pullback_risk_details", {})
        reasons = summary.get("pullback_risk_reasons", [])[:3]
        risk_color = {
            "Low": "#16a34a",
            "Moderate": "#f97316",
            "Elevated": "#ea580c",
            "High": "#dc2626",
        }.get(risk_label, "#64748b")
        assessment = summary.get("overall_description", "N/A")
        assessment_color = (
            "#16a34a"
            if assessment in {"Strongly Bullish", "Confirmed Uptrend"}
            else "#dc2626"
            if assessment in {"Bearish", "Strongly Bearish", "Confirmed Downtrend"}
            else "#f97316"
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
            alpha=0.96,
            zorder=6,
        )
        ax.add_patch(card)

        def add_text(x: float, y: float, text: str, **style: Any) -> None:
            ax.text(
                x,
                y,
                text,
                transform=ax.transAxes,
                ha=style.pop("ha", "left"),
                va="top",
                zorder=7,
                **style,
            )

        y = card_top - 0.025
        add_text(
            left,
            y,
            "Extended Summary" if include_context else "Risk Assessment",
            fontsize=11.8,
            fontweight="bold",
            color="#111827",
        )
        if include_context:
            y -= 0.024
            add_text(right, y, assessment, ha="right", fontsize=12.6, fontweight="bold", color=assessment_color)
            y -= 0.032
        else:
            y -= 0.032
        score_text = "N/A" if risk_score is None else f"{int(risk_score + 0.5)}/100"
        add_text(left, y, "Pullback Risk", fontsize=8.4, fontweight="bold", color="#374151")
        add_text(right, y, score_text, ha="right", fontsize=9.2, fontweight="bold", color=risk_color)
        y -= 0.026
        add_text(left, y, "Risk Level", fontsize=7.5, color="#374151")
        add_text(right, y, risk_label, ha="right", fontsize=8.0, fontweight="bold", color=risk_color)
        y -= 0.029

        if reasons:
            add_text(left, y, "Key Risks", fontsize=8.5, fontweight="bold", color="#111827")
            y -= 0.021
            for reason in reasons:
                add_text(left + 0.008, y, f"- {reason}", fontsize=7.0, color="#b45309")
                y -= 0.021
            y -= 0.003

        category_labels = {
            "price_extension": "Price Extension",
            "momentum_exhaustion": "Momentum Exhaustion",
            "participation_risk": "Participation Risk",
            "reversal_signals": "Reversal Signals",
        }
        for category_key, category_label in category_labels.items():
            if y < card_bottom + 0.04:
                break
            maximum = PullbackRiskConfig.CATEGORY_MAX[category_key]
            awarded = categories.get(category_key, 0)
            raw = raw_categories.get(category_key, awarded)
            ax.plot(
                [left, right],
                [y + 0.008, y + 0.008],
                transform=ax.transAxes,
                color="#e5e7eb",
                linewidth=0.6,
                zorder=6,
            )
            add_text(left, y, category_label, fontsize=8.5, fontweight="bold", color="#111827")
            category_score = f"{awarded}/{maximum}"
            if raw > maximum:
                category_score += f" (raw {raw}, capped)"
            add_text(right, y, category_score, ha="right", fontsize=7.8, fontweight="bold", color=risk_color if awarded else "#64748b")
            y -= 0.022

            for metric in details.get(category_key, []):
                if y < card_bottom + 0.025:
                    break
                metric_points = metric.get("points", 0)
                metric_color = "#dc2626" if metric_points else "#64748b"
                add_text(left + 0.008, y, metric.get("metric", "Metric"), fontsize=7.0, color="#374151")
                add_text(
                    right,
                    y,
                    f"+{metric_points}",
                    ha="right",
                    fontsize=7.1,
                    fontweight="bold",
                    color=metric_color,
                )
                y -= 0.014
                add_text(left + 0.016, y, metric.get("observed", "Unavailable"), fontsize=6.35, color=metric_color)
                y -= 0.013
                add_text(left + 0.016, y, metric.get("rule", ""), fontsize=5.8, color="#64748b")
                y -= 0.015
            y -= 0.002

        if not include_context:
            return

        ax.plot(
            [context_divider, context_divider],
            [card_bottom + 0.02, card_top - 0.075],
            transform=ax.transAxes,
            color="#e5e7eb",
            linewidth=0.7,
            zorder=6,
        )
        context_left = context_divider + 0.020
        context_right = card_right - 0.020
        context_y = card_top - 0.075

        def context_section(title: str, rows: list[tuple[str, str, str]]) -> None:
            nonlocal context_y
            add_text(context_left, context_y, title, fontsize=9.0, fontweight="bold", color="#111827")
            ax.plot(
                [context_left, context_right],
                [context_y - 0.018, context_y - 0.018],
                transform=ax.transAxes,
                color="#e5e7eb",
                linewidth=0.6,
                zorder=6,
            )
            context_y -= 0.030
            for label, value, color in rows:
                add_text(context_left, context_y, label, fontsize=6.45, color="#475569")
                add_text(context_right, context_y, value, ha="right", fontsize=6.8, fontweight="bold", color=color)
                context_y -= 0.026
            context_y -= 0.014

        current_rvol = summary.get("current_rvol")
        atr14 = summary.get("atr14")
        rvol_text = "N/A" if current_rvol is None else f"{current_rvol:.2f}x"
        atr_text = "N/A" if atr14 is None else f"{atr14:.2f}"
        volume_trend = summary.get("volume_trend", "Neutral")
        diagnostic_color = {
            "Rising": "#16a34a",
            "Falling": "#dc2626",
        }.get(volume_trend, "#64748b")
        context_section(
            "Diagnostics",
            [
                ("Volume Trend", volume_trend, diagnostic_color),
                ("Relative Volume", rvol_text, "#16a34a" if current_rvol is not None and current_rvol >= 1 else "#f97316"),
                ("ATR14", atr_text, "#334155"),
            ],
        )

        high_distance = summary.get("distance_52w_high")
        low_distance = summary.get("distance_52w_low")
        context_section(
            "Market Context",
            [
                ("From Daily 52W High", self.format_summary_percent(high_distance), "#334155"),
                ("From Daily 52W Low", self.format_summary_percent(low_distance), "#334155"),
                ("Valuation", str(summary.get("valuation", "Unknown")), "#334155"),
                ("Business", str(summary.get("business_health", "Unknown")), "#334155"),
                ("Investment View", str(summary.get("investment_view", "Watchlist")), "#334155"),
            ],
        )
