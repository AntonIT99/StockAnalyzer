"""Interactive chart cursor and hover readout behavior."""

import time
from typing import Any
import numpy as np
import pandas as pd
from matplotlib.dates import date2num
from matplotlib.lines import Line2D

class ChartCursorMixin:
    @staticmethod
    def plot_x_to_numeric(plot_x: pd.Index) -> np.ndarray:
        if isinstance(plot_x, pd.RangeIndex):
            return plot_x.to_numpy(dtype=float)
        try:
            return date2num(pd.to_datetime(plot_x).to_pydatetime())
        except (TypeError, ValueError):
            return np.asarray(plot_x, dtype=float)

    @staticmethod
    def find_nearest_sorted_index(x_numeric: np.ndarray, cursor_x: float) -> int | None:
        if x_numeric is None or len(x_numeric) == 0:
            return None
        try:
            cursor_x = float(cursor_x)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(cursor_x):
            return None
        position = int(np.searchsorted(x_numeric, cursor_x))
        if position <= 0:
            return 0
        if position >= len(x_numeric):
            return len(x_numeric) - 1
        left_index = position - 1
        right_index = position
        if abs(cursor_x - x_numeric[left_index]) <= abs(x_numeric[right_index] - cursor_x):
            return left_index
        return right_index

    @classmethod
    def format_cursor_timestamp(cls, value: Any) -> str:
        try:
            timestamp = pd.Timestamp(value)
        except (TypeError, ValueError):
            return str(value)
        if timestamp.tzinfo is not None:
            timestamp = cls.to_host_naive_timestamp(timestamp)
        if timestamp.hour or timestamp.minute or timestamp.second:
            return timestamp.strftime("%Y-%m-%d %H:%M")
        return timestamp.strftime("%Y-%m-%d")

    def format_cursor_value(self, column: str, value: Any) -> str:
        if value is None or pd.isna(value):
            return "N/A"
        if column in {"Volume", "VOLUME_SMA20", "VOLUME_EMA20", "VOLUME_EMA50"}:
            return self.format_compact_number(value)
        if column == "RVOL":
            return f"{value:.2f}x"
        return f"{value:.2f}"

    @staticmethod
    def make_cursor_series(label: str, column: str, color: str) -> dict[str, str]:
        return {
            "label": label,
            "column": column,
            "color": color
        }

    def register_cursor_axis(
        self,
        ax: Any,
        data: pd.DataFrame,
        plot_x: pd.Index,
        series: list[dict[str, str]]
    ) -> None:
        available_series = [
            item
            for item in series
            if item["column"] in data.columns
        ]
        if not available_series or data.empty:
            return
        x_numeric = self.plot_x_to_numeric(plot_x)
        if len(x_numeric) == 0:
            return
        vline = ax.axvline(
            x_numeric[0],
            color="#111827",
            linewidth=0.85,
            linestyle="--",
            alpha=0.58,
            zorder=20,
            visible=False
        )
        hline = Line2D(
            [0, 1],
            [np.nan, np.nan],
            color="#111827",
            linewidth=0.85,
            linestyle="--",
            alpha=0.46,
            zorder=20,
            transform=ax.get_yaxis_transform(),
            visible=False
        )
        ax.add_line(hline)
        markers = ax.scatter(
            [],
            [],
            s=28,
            edgecolors="white",
            linewidths=0.75,
            zorder=21,
            visible=False
        )
        annotation = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            fontsize=7.3,
            color="#111827",
            bbox={
                "boxstyle": "round,pad=0.28",
                "facecolor": "white",
                "edgecolor": "#94a3b8",
                "alpha": 0.94
            },
            zorder=22,
            visible=False
        )
        x_label = ax.text(
            x_numeric[0],
            -0.035,
            "",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=7,
            color="#111827",
            clip_on=False,
            bbox={
                "boxstyle": "round,pad=0.22",
                "facecolor": "white",
                "edgecolor": "#94a3b8",
                "alpha": 0.94
            },
            zorder=22,
            visible=False
        )
        y_label = ax.text(
            1.004,
            0,
            "",
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=7,
            color="#111827",
            clip_on=False,
            bbox={
                "boxstyle": "round,pad=0.22",
                "facecolor": "white",
                "edgecolor": "#94a3b8",
                "alpha": 0.94
            },
            zorder=22,
            visible=False
        )
        cursor_artists = [vline, hline, markers, annotation, x_label, y_label]
        for artist in cursor_artists:
            try:
                artist.set_in_layout(False)
            except AttributeError:
                pass
        self._cursor_contexts[ax] = {
            "ax": ax,
            "data": data,
            "plot_x": plot_x,
            "x_numeric": x_numeric,
            "series": available_series,
            "artists": cursor_artists,
            "vline": vline,
            "hline": hline,
            "markers": markers,
            "annotation": annotation,
            "x_label": x_label,
            "y_label": y_label
        }

    @staticmethod
    def set_artist_visible(artist: Any, visible: bool) -> bool:
        if artist.get_visible() == visible:
            return False
        artist.set_visible(visible)
        return True

    def hide_cursor_context(self, context: dict[str, Any] | None) -> bool:
        if context is None:
            return False
        changed = False
        for artist in context["artists"]:
            if self.set_artist_visible(artist, False):
                changed = True
        return changed

    def hide_chart_cursor(self, _event: Any | None = None) -> None:
        changed = False
        for context in self._cursor_contexts.values():
            if self.hide_cursor_context(context):
                changed = True
        if changed:
            self.canvas.draw_idle()
        self._cursor_active_ax = None
        self._last_cursor_key = None

    def on_chart_hover(self, event: Any) -> None:
        context = self._cursor_contexts.get(event.inaxes)
        if context is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        x_numeric = context["x_numeric"]
        point_index = self.find_nearest_sorted_index(x_numeric, event.xdata)
        if point_index is None:
            return
        point_index = max(0, min(point_index, len(context["data"]) - 1))
        cursor_key = (event.inaxes, point_index)
        if cursor_key == self._last_cursor_key:
            return
        now = time.perf_counter()
        if self._cursor_active_ax is event.inaxes and now - self._last_hover_time < self._hover_min_interval:
            return
        row = context["data"].iloc[point_index]
        snapped_x = context["x_numeric"][point_index]
        timestamp = context["data"].index[point_index]
        values = []
        for item in context["series"]:
            value = row.get(item["column"])
            if value is None or pd.isna(value):
                continue
            values.append((item, value))
        if not values:
            return
        nearest_item, nearest_y = min(values, key=lambda item_value: abs(item_value[1] - event.ydata))
        previous_context = self._cursor_contexts.get(self._cursor_active_ax)
        changed = False
        if self._cursor_active_ax is not None and self._cursor_active_ax is not event.inaxes:
            changed = self.hide_cursor_context(previous_context) or changed
            self._last_cursor_key = None
        new_vline_x = [snapped_x, snapped_x]
        if list(context["vline"].get_xdata()) != new_vline_x:
            context["vline"].set_xdata(new_vline_x)
            changed = True
        new_hline_y = [nearest_y, nearest_y]
        if list(context["hline"].get_ydata()) != new_hline_y:
            context["hline"].set_ydata(new_hline_y)
            changed = True
        marker_offsets = np.asarray([[snapped_x, value] for _item, value in values], dtype=float)
        current_offsets = context["markers"].get_offsets()
        if current_offsets.shape != marker_offsets.shape or not np.array_equal(current_offsets, marker_offsets):
            context["markers"].set_offsets(marker_offsets)
            context["markers"].set_facecolors([item["color"] for item, _value in values])
            context["markers"].set_edgecolors(["white"] * len(values))
            changed = True
        x_text = self.format_cursor_timestamp(timestamp)
        tooltip_lines = [x_text]
        tooltip_lines.extend(
            f"{item['label']}: {self.format_cursor_value(item['column'], value)}"
            for item, value in values
        )
        annotation_xy = (snapped_x, nearest_y)
        if context["annotation"].xy != annotation_xy:
            context["annotation"].xy = annotation_xy
            changed = True
        tooltip_text = "\n".join(tooltip_lines)
        if context["annotation"].get_text() != tooltip_text:
            context["annotation"].set_text(tooltip_text)
            changed = True
        x_label_position = (snapped_x, -0.035)
        if context["x_label"].get_position() != x_label_position:
            context["x_label"].set_position(x_label_position)
            changed = True
        if context["x_label"].get_text() != x_text:
            context["x_label"].set_text(x_text)
            changed = True
        y_label_position = (1.004, nearest_y)
        if context["y_label"].get_position() != y_label_position:
            context["y_label"].set_position(y_label_position)
            changed = True
        y_text = self.format_cursor_value(nearest_item["column"], nearest_y)
        if context["y_label"].get_text() != y_text:
            context["y_label"].set_text(y_text)
            changed = True
        for artist in context["artists"]:
            if self.set_artist_visible(artist, True):
                changed = True
        self._cursor_active_ax = event.inaxes
        self._last_cursor_key = cursor_key
        self._last_hover_time = now
        if changed:
            self.canvas.draw_idle()
