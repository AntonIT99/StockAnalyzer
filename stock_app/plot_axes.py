"""Matplotlib x-axis and compact formatting helpers."""

from typing import Any
import numpy as np
import pandas as pd
from matplotlib.ticker import FixedLocator
from matplotlib.ticker import FuncFormatter
from .config import COMPRESSED_AXIS_INTERVALS

class PlotAxisMixin:
    @staticmethod
    def uses_compressed_axis(interval: str) -> bool:
        return interval in COMPRESSED_AXIS_INTERVALS

    @staticmethod
    def get_plot_x(data: pd.DataFrame, compressed_x: bool) -> pd.Index:
        if compressed_x:
            return pd.RangeIndex(len(data))
        return data.index

    @classmethod
    def get_plot_bar_width(cls, data: pd.DataFrame, compressed_x: bool) -> float:
        if compressed_x:
            return 0.72
        return cls.get_bar_width(data.index)

    @classmethod
    def timestamp_to_plot_x(cls, timestamp: Any, index: pd.Index, compressed_x: bool) -> Any:
        if not compressed_x:
            return timestamp
        if index.empty:
            return None
        aligned_timestamp = cls.align_timestamp_to_index(timestamp, index)
        try:
            position = index.searchsorted(aligned_timestamp)
        except (TypeError, ValueError):
            return None
        if position <= 0:
            return 0
        if position >= len(index):
            return len(index) - 1
        before = index[position - 1]
        after = index[position]
        try:
            if abs(aligned_timestamp - before) <= abs(after - aligned_timestamp):
                return position - 1
        except (TypeError, ValueError):
            pass
        return position

    @classmethod
    def configure_x_axis(cls, ax: Any, data: pd.DataFrame, compressed_x: bool) -> None:
        if not compressed_x:
            return
        index = data.index
        ax.set_xlim(-0.5, max(len(index) - 0.5, 0.5))
        if len(index) > 0:
            tick_count = min(8, len(index))
            tick_positions = np.rint(np.linspace(0, len(index) - 1, tick_count)).astype(int)
            tick_positions = np.unique(np.concatenate(([0], tick_positions, [len(index) - 1])))
            ax.xaxis.set_major_locator(FixedLocator(tick_positions))
        has_intraday_times = any(
            pd.Timestamp(timestamp).hour or pd.Timestamp(timestamp).minute or pd.Timestamp(timestamp).second
            for timestamp in index
        )

        def format_compressed_tick(value: float, _position: int) -> str:
            tick_index = int(round(value))
            if tick_index < 0 or tick_index >= len(index):
                return ""
            timestamp = pd.Timestamp(index[tick_index])
            if timestamp.tzinfo is not None:
                timestamp = cls.to_host_naive_timestamp(timestamp)
            if not has_intraday_times:
                return timestamp.strftime("%Y-%m-%d")
            return timestamp.strftime("%m-%d %H:%M")
        ax.xaxis.set_major_formatter(FuncFormatter(format_compressed_tick))
        ax.tick_params(axis="x", labelsize=8)

    @staticmethod
    def format_compact_number(value):
        if pd.isna(value):
            return "n/a"
        abs_value = abs(value)
        if abs_value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        if abs_value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if abs_value >= 1_000:
            return f"{value / 1_000:.0f}K"
        return f"{value:.0f}"
