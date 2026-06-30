"""Volume and relative-volume panel drawing."""

from typing import Any
import pandas as pd
from matplotlib.ticker import FuncFormatter

class VolumeChartMixin:
    def plot_volume_panel(
        self,
        volume_ax: Any,
        data: pd.DataFrame,
        _price_ax: Any,
        plot_x: pd.Index,
        compressed_x: bool,
        show_volume_sma20: bool = True,
        show_volume_ema50: bool = True,
        show_spike_shading: bool = False
    ) -> Any:
        bar_width = self.get_plot_bar_width(data, compressed_x)
        rising_volume = data["Close"] >= data["Close"].shift()
        rising_volume = rising_volume.fillna(True)
        bar_colors = rising_volume.map({True: "#16a34a", False: "#dc2626"})
        volume_ax.bar(plot_x, data["Volume"], label="Volume", width=bar_width, color=bar_colors.tolist(), alpha=0.55, edgecolor="none")
        if show_volume_sma20:
            volume_ax.plot(plot_x, data["VOLUME_SMA20"], label="Volume SMA 20", linewidth=2.2, color="#2563eb")
        if show_volume_ema50:
            volume_ax.plot(
                plot_x,
                data["VOLUME_EMA50"],
                label="Volume EMA 50",
                linewidth=1.5,
                color="#0891b2"
            )
        volume_ax.set_ylabel("Volume")
        volume_ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: self.format_compact_number(value)))
        volume_ax.grid(True, axis="y", alpha=0.22, linewidth=0.8)
        volume_ax.grid(True, axis="x", alpha=0.08, linewidth=0.6)
        volume_ax.margins(x=0.01)
        rvol_ax = volume_ax.twinx()
        rvol_ax.plot(
            plot_x,
            data["RVOL"],
            label="RVOL",
            linewidth=1.4,
            linestyle="--",
            color="#7c3aed",
            alpha=0.68
        )
        rvol_ax.tick_params(axis="y", colors="#7c3aed", labelsize=8)
        rvol_ax.axhline(1, linewidth=0.9, linestyle=":", color="#64748b", label="RVOL 1")
        rvol_ax.axhline(2, linewidth=0.9, linestyle=":", color="#f97316", label="RVOL 2")
        rvol_ax.set_ylabel("Relative Volume (RVOL)")
        high_rvol = data["RVOL"] > 2
        if high_rvol.any():
            event_data = data.loc[high_rvol]
            event_positions = plot_x[data.index.get_indexer(event_data.index)]
            rvol_ax.scatter(
                event_positions,
                event_data["RVOL"],
                label="RVOL > 2",
                color="#f97316",
                edgecolors="white",
                linewidths=0.6,
                s=34,
                zorder=5
            )
            if show_spike_shading:
                highlight_half_width = bar_width / 2
                for event_position in event_positions:
                    volume_ax.axvspan(
                        event_position - highlight_half_width,
                        event_position + highlight_half_width,
                        color="#f97316",
                        alpha=0.08,
                        linewidth=0
                    )
        spike_times = self.get_spike_times(data)
        self.draw_spike_lines(volume_ax, spike_times, data.index, compressed_x)
        latest_volume = self.latest_valid_value(data["Volume"])
        latest_sma20_volume = self.latest_valid_value(data["VOLUME_SMA20"])
        latest_rvol = self.latest_valid_value(data["RVOL"])
        volume_trend = self.calculate_volume_trend(data)
        rvol_text = f"{latest_rvol:.2f}x" if latest_rvol is not None else "n/a"
        volume_title = (
            f"Volume | Current {self.format_compact_number(latest_volume)}"
            f" | SMA20 {self.format_compact_number(latest_sma20_volume)}"
            f" | RVOL {rvol_text}"
            f" | Trend {volume_trend}"
        )
        volume_ax.set_title(volume_title, fontsize=10, loc="left")
        volume_values = data["Volume"].dropna()
        if not volume_values.empty:
            max_volume_time = volume_values.idxmax()
            max_volume = volume_values.loc[max_volume_time]
            max_volume_x = self.timestamp_to_plot_x(max_volume_time, data.index, compressed_x)
            self.annotate_point(volume_ax, max_volume_x, max_volume, f"Max Vol {self.format_compact_number(max_volume)}", "#2563eb")
        rvol_values = data["RVOL"].dropna()
        if not rvol_values.empty:
            max_rvol_time = rvol_values.idxmax()
            max_rvol = rvol_values.loc[max_rvol_time]
            max_rvol_x = self.timestamp_to_plot_x(max_rvol_time, data.index, compressed_x)
            self.annotate_point(rvol_ax, max_rvol_x, max_rvol, f"Max RVOL {max_rvol:.2f}x", "#f97316")
        handles, labels = volume_ax.get_legend_handles_labels()
        rvol_handles, rvol_labels = rvol_ax.get_legend_handles_labels()
        volume_ax.legend(handles + rvol_handles, labels + rvol_labels, loc="upper left", ncols=3, fontsize=8, framealpha=0.88)
        return rvol_ax

