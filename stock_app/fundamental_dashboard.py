"""Fundamental metrics dashboard drawing."""

from typing import Any
from matplotlib.patches import FancyBboxPatch

class FundamentalDashboardMixin:
    def draw_fundamental_dashboard(self, ax: Any, metrics: dict[str, dict[str, Any]], card_bottom: float = 0.03, card_height: float = 0.58) -> None:
        ax.set_axis_off()
        card_left = 0.04
        card_width = 0.92
        card_right = card_left + card_width
        card_top = card_bottom + card_height
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
        ax.text(
            card_left + 0.018,
            card_top - 0.028,
            "Fundamentals",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.3,
            fontweight="bold",
            color="#111827",
            zorder=7
        )

        def status_color(status: str) -> str:
            if status == "good":
                return "#16a34a"
            if status == "bad":
                return "#dc2626"
            return "#64748b"

        def status_label(name: str, status: str, _value: Any) -> str:
            if name in {"trailing_pe", "forward_pe"}:
                if status == "good":
                    return "cheap"
                if status == "bad":
                    return "expensive"
                return "reasonable"
            if name == "peg_ratio":
                if status == "good":
                    return "attractive"
                if status == "bad":
                    return "expensive"
                return "fair"
            if name == "debt_equity":
                if status == "good":
                    return "low"
                if status == "bad":
                    return "high"
                return "moderate"
            return ""
        sections = ["Valuation", "Growth", "Cash Flow", "Quality", "Balance Sheet", "Shareholder View"]
        row_y = card_top - 0.075
        row_step = 0.019
        title_rule_gap = 0.017
        after_rule_gap = 0.008
        section_gap = 0.012
        if not metrics:
            ax.text(
                card_left + 0.018,
                row_y,
                "No fundamental data available",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.5,
                color="#64748b",
                zorder=7
            )
            return
        for section in sections:
            section_metrics = [
                (name, metric)
                for name, metric in metrics.items()
                if metric.get("section") == section
            ]
            if not section_metrics:
                continue
            ax.text(
                card_left + 0.018,
                row_y,
                section,
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=7.7,
                fontweight="bold",
                color="#111827",
                zorder=7
            )
            ax.plot(
                [card_left + 0.018, card_right - 0.018],
                [row_y - title_rule_gap, row_y - title_rule_gap],
                transform=ax.transAxes,
                color="#e5e7eb",
                linewidth=0.6,
                zorder=6
            )
            row_y -= title_rule_gap + after_rule_gap
            for metric_name, metric in section_metrics:
                if row_y < card_bottom + 0.014:
                    return
                formatted_value = self.format_fundamental_value(metric.get("value"), metric.get("type", ""))
                status = metric.get("status", "neutral") if formatted_value != "N/A" else "neutral"
                interpretation = status_label(metric_name, status, metric.get("value"))
                value_text = formatted_value if not interpretation else f"{formatted_value}  {interpretation}"
                history_label = metric.get("history_label")
                if metric.get("type") == "history_percent" and history_label and formatted_value != "N/A":
                    value_text = f"{formatted_value}  {history_label}"
                color = status_color(status)
                ax.text(
                    card_left + 0.018,
                    row_y,
                    metric.get("label", metric_name),
                    transform=ax.transAxes,
                    ha="left",
                    va="top",
                    fontsize=6.15,
                    color="#374151",
                    zorder=7
                )
                ax.text(
                    card_right - 0.018,
                    row_y,
                    value_text,
                    transform=ax.transAxes,
                    ha="right",
                    va="top",
                    fontsize=6.15,
                    fontweight="bold" if interpretation else "normal",
                    color=color,
                    zorder=7
                )
                row_y -= row_step
            row_y -= section_gap
