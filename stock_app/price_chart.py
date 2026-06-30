"""Price panel overlays, candlesticks, earnings markers, and spike lines."""

from typing import Any
import pandas as pd
from matplotlib.patches import Patch

class PriceChartMixin:
    @staticmethod
    def annotate_point(ax, x_value, y_value, text, color):
        ax.annotate(
            text,
            xy=(x_value, y_value),
            xytext=(10, 18),
            textcoords="offset points",
            fontsize=8,
            color=color,
            arrowprops={
                "arrowstyle": "->",
                "color": color,
                "linewidth": 0.9
            },
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "white",
                "edgecolor": color,
                "alpha": 0.85
            }
        )

    @staticmethod
    def get_spike_times(data: pd.DataFrame) -> pd.Index:
        if "VOLUME_SPIKE" not in data.columns:
            return pd.Index([])
        return data.index[data["VOLUME_SPIKE"].fillna(False)]

    @classmethod
    def draw_spike_lines(cls, ax: Any, spike_times: pd.Index, data_index: pd.Index | None = None, compressed_x: bool = False) -> None:
        for spike_time in spike_times:
            x_value = cls.timestamp_to_plot_x(spike_time, data_index, compressed_x) if data_index is not None else spike_time
            if x_value is None:
                continue
            ax.axvline(
                x_value,
                color="#f97316",
                linewidth=0.75,
                linestyle=":",
                alpha=0.38,
                zorder=0
            )

    def get_selected_indicators(self) -> dict[str, bool]:
        return {
            "EMA9": self.show_ema9.get(),
            "EMA12": self.show_ema12.get(),
            "EMA20": self.show_ema20.get(),
            "EMA50": self.show_ema50.get(),
            "EMA100": self.show_ema100.get(),
            "EMA200": self.show_ema200.get(),
            "SMA20": self.show_sma20.get(),
            "SMA50": self.show_sma50.get(),
            "SMA100": self.show_sma100.get(),
            "SMA200": self.show_sma200.get(),
            "BOLLINGER": self.show_bollinger.get()
        }

    def plot_price_panel(
        self,
        ax: Any,
        data: pd.DataFrame,
        ticker: str,
        price_style: str,
        selected_indicators: dict[str, bool],
        spike_times: pd.Index,
        earnings_events: pd.DataFrame,
        plot_x: pd.Index,
        compressed_x: bool
    ) -> None:
        if price_style == "Candlesticks":
            self.plot_candlesticks(ax, data, plot_x, compressed_x)
        else:
            ax.plot(plot_x, data["Close"], label="Close", linewidth=1.6, color="#2563eb")
        indicator_specs = [
            ("EMA9", "EMA 9"),
            ("EMA12", "EMA 12"),
            ("EMA20", "EMA 20"),
            ("EMA50", "EMA 50"),
            ("EMA100", "EMA 100"),
            ("EMA200", "EMA 200"),
            ("SMA20", "SMA 20"),
            ("SMA50", "SMA 50"),
            ("SMA100", "SMA 100"),
            ("SMA200", "SMA 200")
        ]
        for column, label in indicator_specs:
            if selected_indicators.get(column):
                ax.plot(plot_x, data[column], label=label, linewidth=1)
        if selected_indicators.get("BOLLINGER"):
            ax.plot(plot_x, data["BB_UPPER"], label="Bollinger Upper", linewidth=0.9)
            ax.plot(plot_x, data["BB_LOWER"], label="Bollinger Lower", linewidth=0.9)
        self.draw_spike_lines(ax, spike_times, data.index, compressed_x)
        self.plot_earnings_markers(ax, data, earnings_events, compressed_x)
        ax.set_title(f"{ticker} Technical Chart")
        ax.set_ylabel("Price USD")
        ax.grid(True, axis="y", alpha=0.22, linewidth=0.8)
        ax.grid(True, axis="x", alpha=0.08, linewidth=0.6)
        handles, labels = ax.get_legend_handles_labels()
        if price_style == "Candlesticks":
            handles = [
                Patch(facecolor="#16a34a", edgecolor="#16a34a", label="Up Candle"),
                Patch(facecolor="#dc2626", edgecolor="#dc2626", label="Down Candle")
            ] + handles
            labels = ["Up Candle", "Down Candle"] + labels
        ax.legend(handles, labels, loc="upper left", fontsize=8, framealpha=0.88)

    @classmethod
    def plot_earnings_markers(cls, ax: Any, data: pd.DataFrame, earnings_events: pd.DataFrame, compressed_x: bool = False) -> None:
        if earnings_events.empty:
            return
        price_min = data["Low"].min() if "Low" in data.columns else data["Close"].min()
        price_max = data["High"].max() if "High" in data.columns else data["Close"].max()
        price_span = price_max - price_min
        marker_y = price_min + (price_span * 0.06 if price_span else 0)
        for _, event in earnings_events.iterrows():
            event_date = event["date"]
            event_x = cls.timestamp_to_plot_x(event_date, data.index, compressed_x)
            if event_x is None:
                continue
            label = event["label"]
            ax.axvline(event_x, color="#64748b", linestyle=":", linewidth=0.8, alpha=0.55, zorder=1)
            ax.text(
                event_x,
                marker_y,
                label,
                ha="center",
                va="center",
                fontsize=7.5,
                fontweight="bold",
                color="#334155",
                bbox={
                    "boxstyle": "round,pad=0.18",
                    "facecolor": "#f8fafc",
                    "edgecolor": "#94a3b8",
                    "alpha": 0.88
                },
                zorder=6
            )

    def plot_candlesticks(self, ax: Any, data: pd.DataFrame, plot_x: pd.Index, compressed_x: bool) -> None:
        bar_width = self.get_plot_bar_width(data, compressed_x) * 0.72
        up_color = "#16a34a"
        down_color = "#dc2626"
        rising = data["Close"] >= data["Open"]
        colors = rising.map({True: up_color, False: down_color})
        body_bottom = data[["Open", "Close"]].min(axis=1)
        body_height = (data["Close"] - data["Open"]).abs()
        min_body_height = max((data["High"].max() - data["Low"].min()) * 0.001, 1e-9)
        small_body = body_height < min_body_height
        body_bottom = body_bottom.mask(small_body, data["Close"] - (min_body_height / 2))
        body_height = body_height.mask(small_body, min_body_height)
        ax.vlines(plot_x, data["Low"], data["High"], color=colors.tolist(), linewidth=0.9, alpha=0.9, label="_nolegend_")
        ax.bar(
            plot_x,
            body_height,
            bottom=body_bottom,
            width=bar_width,
            color=colors.tolist(),
            edgecolor=colors.tolist(),
            linewidth=0.7,
            alpha=0.86,
            label="_nolegend_"
        )
