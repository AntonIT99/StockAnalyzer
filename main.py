import argparse
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any

import yfinance as yf
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import date2num
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.ticker import FixedLocator, FuncFormatter

from stock_cache import build_cache_key, get_cache_path, load_cached_data, save_cached_data
from stock_config import (
    ATR_PCT_HEALTHY_MAX,
    ATR_PCT_HEALTHY_MIN,
    BULLISH_STRUCTURE_SCORE_MAX,
    COMPRESSED_AXIS_INTERVALS,
    CONFIRMATION_SCORE_MAX,
    CUSTOM_PERIOD,
    DAILY_SIGNAL_PERIOD,
    DOWNLOAD_INTERVALS,
    EXTENDED_BULLISH_SCORE_MAX,
    INDICATOR_SETTINGS,
    INTERVAL_DURATIONS,
    INTERVAL_MAX_LOOKBACKS,
    INTERVAL_OPTIONS,
    INTRADAY_INTERVALS,
    MAX_MOVING_AVERAGE_WINDOW,
    PERIOD_DURATIONS,
    PERIOD_OPTIONS,
    RESAMPLE_RULES,
    SETTINGS_PATH
)
from stock_ohlcv import drop_incomplete_price_rows, flatten_yfinance_columns, get_bar_width, resample_ohlcv
from stock_time import (
    get_host_timezone,
    host_now,
    host_today,
    normalize_index_to_host_timezone,
    to_host_naive_timestamp
)


# noinspection PyTypeChecker,PyPandasTruthValueIsAmbiguousInspection,PyShadowingNamesInspection,PyUnusedLocalInspection,PyUnresolvedReferencesInspection,PyUnboundLocalVariableInspection,PyBroadExceptionInspection
class StockApp:
    get_host_timezone = staticmethod(get_host_timezone)
    host_now = staticmethod(host_now)
    host_today = staticmethod(host_today)
    to_host_naive_timestamp = staticmethod(to_host_naive_timestamp)
    normalize_index_to_host_timezone = staticmethod(normalize_index_to_host_timezone)
    flatten_yfinance_columns = staticmethod(flatten_yfinance_columns)
    build_cache_key = staticmethod(build_cache_key)
    get_cache_path = staticmethod(get_cache_path)
    load_cached_data = staticmethod(load_cached_data)
    save_cached_data = staticmethod(save_cached_data)
    drop_incomplete_price_rows = staticmethod(drop_incomplete_price_rows)
    resample_ohlcv = staticmethod(resample_ohlcv)
    get_bar_width = staticmethod(get_bar_width)

    def __init__(self, root, initial_ticker=""):
        settings = self.load_settings()

        self.root = root
        self.root.title("Stock Technical Chart")
        self.root.geometry("1600x900")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        ticker = initial_ticker or settings.get("ticker", "")
        period = settings.get("period", "6mo")
        if period == "5d":
            period = "1wk"
        if period == "15d":
            period = "2wk"
        if period not in PERIOD_OPTIONS:
            period = "6mo"

        today = self.host_today()
        default_custom_start = (today - pd.DateOffset(months=6)).strftime("%Y-%m-%d")
        default_custom_end = today.strftime("%Y-%m-%d")

        self.ticker_var = tk.StringVar(value=ticker)
        self.period_var = tk.StringVar(value=period)
        self.custom_start_var = tk.StringVar(value=settings.get("custom_start", default_custom_start))
        self.custom_end_var = tk.StringVar(value=settings.get("custom_end", default_custom_end))
        self.interval_var = tk.StringVar(value=settings.get("interval", "1d"))
        allowed_intervals = self.get_allowed_intervals_for_current_period()
        if self.interval_var.get() not in allowed_intervals:
            self.interval_var.set(allowed_intervals[0])
        self.price_style_var = tk.StringVar(value=settings.get("price_style", "Line"))
        if self.price_style_var.get() not in {"Line", "Candlesticks"}:
            self.price_style_var.set("Line")

        indicator_settings = settings.get("indicators", {})
        self.show_ema9 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema9", False)))
        self.show_ema12 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema12", False)))
        self.show_ema20 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema20", False)))
        self.show_ema50 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema50", False)))
        self.show_ema100 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema100", False)))
        self.show_ema200 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema200", False)))
        self.show_sma20 = tk.BooleanVar(value=bool(indicator_settings.get("show_sma20", False)))
        self.show_sma50 = tk.BooleanVar(value=bool(indicator_settings.get("show_sma50", False)))
        self.show_sma100 = tk.BooleanVar(value=bool(indicator_settings.get("show_sma100", False)))
        self.show_sma200 = tk.BooleanVar(value=bool(indicator_settings.get("show_sma200", False)))
        self.show_bollinger = tk.BooleanVar(value=bool(indicator_settings.get("show_bollinger", False)))
        self.show_rsi = tk.BooleanVar(value=bool(indicator_settings.get("show_rsi", False)))
        self.show_macd = tk.BooleanVar(value=bool(indicator_settings.get("show_macd", False)))
        self.show_volume = tk.BooleanVar(value=bool(indicator_settings.get("show_volume", False)))
        self.show_volume_sma20 = tk.BooleanVar(value=bool(indicator_settings.get("show_volume_sma20", True)))
        self.show_volume_ema50 = tk.BooleanVar(value=bool(indicator_settings.get("show_volume_ema50", True)))
        self.show_atr = tk.BooleanVar(value=bool(indicator_settings.get("show_atr", False)))
        self.show_earnings = tk.BooleanVar(value=bool(indicator_settings.get("show_earnings", False)))
        self.show_fundamentals = tk.BooleanVar(value=bool(indicator_settings.get("show_fundamentals", False)))
        self.show_debug_fundamentals = tk.BooleanVar(value=bool(indicator_settings.get("show_debug_fundamentals", False)))
        self._fundamentals_cache: dict[str, dict[str, Any]] = {}
        self._cursor_contexts: dict[Any, dict[str, Any]] = {}
        self._cursor_active_ax: Any | None = None
        self._last_cursor_key: tuple[Any, int] | None = None
        self._last_hover_time = 0.0
        self._hover_min_interval = 1 / 40

        self._build_ui()
        self.canvas.mpl_connect("motion_notify_event", self.on_chart_hover)
        self.canvas.mpl_connect("figure_leave_event", self.hide_chart_cursor)
        if ticker:
            self.update_chart()

    @staticmethod
    def load_settings():
        if not SETTINGS_PATH.exists():
            return {}

        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
        except Exception:
            return {}

        if not isinstance(settings, dict):
            return {}

        return settings

    def save_settings(self):
        settings = {
            "ticker": self.ticker_var.get().strip().upper(),
            "period": self.period_var.get(),
            "custom_start": self.custom_start_var.get().strip(),
            "custom_end": self.custom_end_var.get().strip(),
            "interval": self.interval_var.get(),
            "price_style": self.price_style_var.get(),
            "indicators": {
                indicator: getattr(self, indicator).get()
                for indicator in INDICATOR_SETTINGS
            }
        }

        try:
            with SETTINGS_PATH.open("w", encoding="utf-8") as settings_file:
                json.dump(settings, settings_file, indent=2)
                settings_file.write("\n")
        except Exception:
            pass

    def on_close(self):
        self.save_settings()
        self.root.destroy()

    def _build_ui(self):
        controls = ttk.Frame(self.root)
        controls.pack(side="top", fill="x", padx=10, pady=8)

        top_controls = ttk.Frame(controls)
        top_controls.pack(side="top", fill="x")

        indicator_controls = ttk.Frame(controls)
        indicator_controls.pack(side="top", fill="x", pady=(6, 0))

        ttk.Label(top_controls, text="Ticker:").pack(side="left")
        ticker_entry = ttk.Entry(top_controls, textvariable=self.ticker_var, width=10)
        ticker_entry.pack(side="left", padx=5)
        ticker_entry.bind("<Return>", lambda _event: self.update_chart())
        ticker_entry.bind("<FocusOut>", lambda _event: self.save_settings())

        ttk.Label(top_controls, text="Period:").pack(side="left")
        period_combobox = ttk.Combobox(
            top_controls,
            textvariable=self.period_var,
            values=PERIOD_OPTIONS,
            width=8,
            state="readonly"
        )
        period_combobox.pack(side="left", padx=5)
        period_combobox.bind("<<ComboboxSelected>>", lambda _event: self.on_period_changed())

        self.custom_range_frame = ttk.Frame(top_controls)
        ttk.Label(self.custom_range_frame, text="Start:").pack(side="left")
        custom_start_entry = ttk.Entry(self.custom_range_frame, textvariable=self.custom_start_var, width=11)
        custom_start_entry.pack(side="left", padx=(4, 8))
        custom_start_entry.bind("<Return>", lambda _event: self.on_custom_range_changed())
        custom_start_entry.bind("<FocusOut>", lambda _event: self.on_custom_range_changed())
        ttk.Label(self.custom_range_frame, text="End:").pack(side="left")
        custom_end_entry = ttk.Entry(self.custom_range_frame, textvariable=self.custom_end_var, width=11)
        custom_end_entry.pack(side="left", padx=(4, 0))
        custom_end_entry.bind("<Return>", lambda _event: self.on_custom_range_changed())
        custom_end_entry.bind("<FocusOut>", lambda _event: self.on_custom_range_changed())

        self.interval_label = ttk.Label(top_controls, text="Interval:")
        self.interval_label.pack(side="left", padx=(15, 0))
        self.interval_combobox = ttk.Combobox(
            top_controls,
            textvariable=self.interval_var,
            width=8,
            state="readonly"
        )
        self.interval_combobox.pack(side="left", padx=5)
        self.toggle_custom_date_controls()
        self.update_interval_options()
        self.interval_combobox.bind("<<ComboboxSelected>>", lambda _event: self.save_settings())

        ttk.Label(top_controls, text="Style:").pack(side="left", padx=(15, 0))
        price_style_combobox = ttk.Combobox(
            top_controls,
            textvariable=self.price_style_var,
            values=["Line", "Candlesticks"],
            width=12,
            state="readonly"
        )
        price_style_combobox.pack(side="left", padx=5)
        price_style_combobox.bind("<<ComboboxSelected>>", lambda _event: self.save_settings())

        ttk.Button(top_controls, text="Update", command=lambda: self.update_chart(refresh_fundamentals=True)).pack(side="left", padx=15)

        ttk.Checkbutton(indicator_controls, text="EMA 9", variable=self.show_ema9, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 12", variable=self.show_ema12, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 20", variable=self.show_ema20, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 50", variable=self.show_ema50, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 100", variable=self.show_ema100, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 200", variable=self.show_ema200, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="SMA 20", variable=self.show_sma20, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="SMA 50", variable=self.show_sma50, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="SMA 100", variable=self.show_sma100, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="SMA 200", variable=self.show_sma200, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Bollinger", variable=self.show_bollinger, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="RSI", variable=self.show_rsi, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="MACD", variable=self.show_macd, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Volume", variable=self.show_volume, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Vol SMA20", variable=self.show_volume_sma20, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Vol EMA50", variable=self.show_volume_ema50, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="ATR 14", variable=self.show_atr, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Earnings", variable=self.show_earnings, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Fundamentals", variable=self.show_fundamentals, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Debug Fundamentals", variable=self.show_debug_fundamentals, command=self.save_settings).pack(side="left", padx=8)

        self.figure = Figure(figsize=(11, 7), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_period_changed(self):
        self.toggle_custom_date_controls()
        self.update_interval_options(persist=True)

    def on_custom_range_changed(self):
        self.update_interval_options(persist=True)

    def toggle_custom_date_controls(self):
        if self.period_var.get() == CUSTOM_PERIOD:
            if not self.custom_range_frame.winfo_ismapped():
                self.custom_range_frame.pack(side="left", padx=(4, 0), before=self.interval_label)
        else:
            self.custom_range_frame.pack_forget()

    def update_interval_options(self, persist=False):
        allowed_intervals = self.get_allowed_intervals_for_current_period()
        self.interval_combobox["values"] = allowed_intervals

        if self.interval_var.get() not in allowed_intervals:
            self.interval_var.set(allowed_intervals[0])

        if persist:
            self.save_settings()

    def get_allowed_intervals_for_current_period(self):
        allowed_intervals = self.get_allowed_intervals(
            self.get_interval_rule_period(),
            self.get_interval_rule_period_duration()
        )
        if self.period_var.get() != CUSTOM_PERIOD:
            return allowed_intervals

        try:
            visible_start, _visible_end = self.get_custom_visible_window()
        except ValueError:
            return allowed_intervals

        return [
            interval
            for interval in allowed_intervals
            if self.is_interval_within_yfinance_lookback(interval, visible_start)
        ]

    @staticmethod
    def get_allowed_intervals(period, period_duration=None):
        if period_duration is None:
            period_duration = PERIOD_DURATIONS.get(period)
        return [
            interval
            for interval in INTERVAL_OPTIONS
            if StockApp.is_interval_allowed_for_period(interval, period_duration)
        ]

    @staticmethod
    def is_interval_allowed_for_period(interval, period_duration):
        max_lookback = INTERVAL_MAX_LOOKBACKS[interval]

        if period_duration is None:
            return max_lookback is None

        if INTERVAL_DURATIONS[interval] >= period_duration:
            return False

        return max_lookback is None or period_duration < max_lookback

    @staticmethod
    def is_interval_within_yfinance_lookback(interval, visible_start):
        max_lookback = INTERVAL_MAX_LOOKBACKS[interval]
        if max_lookback is None:
            return True

        oldest_allowed_start = StockApp.host_now() - max_lookback
        return visible_start >= oldest_allowed_start

    def get_interval_rule_period(self):
        if self.period_var.get() != CUSTOM_PERIOD:
            return self.period_var.get()

        custom_duration = self.get_custom_period_duration(default_period="6mo")
        return self.get_smallest_covering_standard_period(custom_duration)

    def get_interval_rule_period_duration(self):
        return PERIOD_DURATIONS.get(self.get_interval_rule_period())

    @staticmethod
    def get_smallest_covering_standard_period(period_duration):
        for period in PERIOD_OPTIONS:
            standard_duration = PERIOD_DURATIONS.get(period)
            if standard_duration is not None and period_duration <= standard_duration:
                return period
        return "max"

    def download_data(self):
        ticker = self.get_ticker()
        visible_start, visible_end = self.get_visible_window()
        interval = self.interval_var.get()
        download_interval = self.get_download_interval(interval)
        interval_rule_period = self.get_interval_rule_period()
        interval_rule_duration = PERIOD_DURATIONS.get(interval_rule_period)

        download_kwargs = {
            "interval": download_interval,
            "auto_adjust": True,
            "progress": False
        }

        if visible_start is None:
            self.validate_period_interval(visible_start, interval, interval_rule_period, interval_rule_duration)
            download_kwargs["period"] = self.period_var.get()
        elif self.period_var.get() == CUSTOM_PERIOD:
            self.validate_period_interval(visible_start, interval, interval_rule_period, interval_rule_duration)
            download_kwargs["start"] = self.get_download_start(visible_start, interval)
            download_kwargs["end"] = visible_end
        else:
            self.validate_period_interval(visible_start, interval, interval_rule_period, interval_rule_duration)
            intraday_period = self.get_intraday_download_period(interval, interval_rule_period)
            if intraday_period is None:
                download_kwargs["start"] = self.get_download_start(visible_start, interval)
                download_kwargs["end"] = self.host_today() + pd.Timedelta(days=1)
            else:
                download_kwargs["period"] = intraday_period

        cache_period = self.get_cache_period_key(visible_start, visible_end)
        cache_key = self.build_cache_key(ticker, cache_period, interval, download_interval)
        data = self.load_cached_data(cache_key, interval)

        if data is None:
            data = yf.download(
                ticker,
                **download_kwargs
            )

            if data is None or data.empty:
                raise ValueError("No data received. Check the ticker, period, or interval.")

            data = self.flatten_yfinance_columns(data)

            self.save_cached_data(cache_key, data)

        data = self.flatten_yfinance_columns(data)
        if data is None or data.empty:
            raise ValueError("No data received. Check the ticker, period, or interval.")
        data = self.normalize_index_to_host_timezone(data, preserve_dates=interval not in INTRADAY_INTERVALS)
        if interval == "1d":
            data = self.append_missing_daily_bars_from_intraday(ticker, data)

        if interval in RESAMPLE_RULES:
            data = self.resample_ohlcv(data, RESAMPLE_RULES[interval])

        return self.drop_incomplete_price_rows(data), visible_start, visible_end

    def append_missing_daily_bars_from_intraday(self, ticker: str, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return data

        intraday_data = self.download_recent_intraday_for_daily_fallback(ticker)
        if intraday_data.empty:
            return data

        intraday_daily = self.resample_ohlcv(intraday_data, "D")
        if intraday_daily.empty:
            return data

        intraday_daily.index = intraday_daily.index.normalize()
        latest_daily_date = pd.Timestamp(data.index.max()).normalize()
        recent_intraday_daily = intraday_daily.loc[intraday_daily.index >= latest_daily_date]
        if recent_intraday_daily.empty:
            return data

        combined = data.copy()
        columns = list(dict.fromkeys([*combined.columns, *recent_intraday_daily.columns]))
        combined = combined.reindex(columns=columns)

        ohlcv_columns = [
            column
            for column in ("Open", "High", "Low", "Close", "Volume")
            if column in recent_intraday_daily
        ]
        if not ohlcv_columns:
            return data

        for date, row in recent_intraday_daily.iterrows():
            if date not in combined.index:
                combined.loc[date, ohlcv_columns] = row[ohlcv_columns]
                continue

            for column in ohlcv_columns:
                value = row[column]
                if value is not None and not pd.isna(value):
                    combined.loc[date, column] = value

        return combined.sort_index()

    def download_recent_intraday_for_daily_fallback(self, ticker: str) -> pd.DataFrame:
        cache_key = self.build_cache_key(ticker, "daily-latest-fallback-v2:10d", "daily-latest-fallback", "1h")
        data = self.load_cached_data(cache_key, "1h")

        if data is None:
            try:
                data = yf.download(
                    ticker,
                    period="10d",
                    interval="1h",
                    auto_adjust=True,
                    progress=False
                )
            except Exception:
                return pd.DataFrame()

            data = self.flatten_yfinance_columns(data)
            if data is None or data.empty:
                return pd.DataFrame()

            self.save_cached_data(cache_key, data)

        data = self.flatten_yfinance_columns(data)
        if data is None or data.empty:
            return pd.DataFrame()

        return self.normalize_index_to_host_timezone(data, preserve_dates=False)

    def download_daily_signal_data(self, ticker: str, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
        download_kwargs = {
            "interval": "1d",
            "auto_adjust": True,
            "progress": False
        }
        if as_of is None:
            cache_period = DAILY_SIGNAL_PERIOD
            download_kwargs["period"] = DAILY_SIGNAL_PERIOD
        else:
            as_of = self.to_host_naive_timestamp(as_of).normalize()
            start = as_of - pd.DateOffset(years=2)
            cache_period = f"daily-structural:{start.strftime('%Y-%m-%d')}:{as_of.strftime('%Y-%m-%d')}"
            download_kwargs["start"] = start
            download_kwargs["end"] = as_of

        cache_key = self.build_cache_key(ticker, cache_period, "daily-structural", "1d")
        data = self.load_cached_data(cache_key, "1d")

        if data is None:
            try:
                data = yf.download(
                    ticker,
                    **download_kwargs
                )
            except Exception:
                return pd.DataFrame()

            data = self.flatten_yfinance_columns(data)
            if data is None or data.empty:
                return pd.DataFrame()

            self.save_cached_data(cache_key, data)

        data = self.flatten_yfinance_columns(data)
        if data is None or data.empty or "Close" not in data:
            return pd.DataFrame()
        data = self.normalize_index_to_host_timezone(data, preserve_dates=True)

        return self.add_daily_structural_indicators(data.dropna())

    def get_ticker(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            raise ValueError("Enter a ticker symbol.")

        self.ticker_var.set(ticker)
        return ticker

    def get_visible_start(self):
        period = self.period_var.get()
        end = self.host_now()

        period_offsets = {
            "1h": pd.DateOffset(hours=1),
            "1d": pd.DateOffset(days=1),
            "1wk": pd.DateOffset(weeks=1),
            "2wk": pd.DateOffset(weeks=2),
            "1mo": pd.DateOffset(months=1),
            "3mo": pd.DateOffset(months=3),
            "6mo": pd.DateOffset(months=6),
            "1y": pd.DateOffset(years=1),
            "2y": pd.DateOffset(years=2),
            "3y": pd.DateOffset(years=3),
            "4y": pd.DateOffset(years=4),
            "5y": pd.DateOffset(years=5),
            "10y": pd.DateOffset(years=10)
        }

        offset = period_offsets.get(period)
        if offset is None:
            return None

        return end - offset

    def get_visible_window(self):
        if self.period_var.get() == CUSTOM_PERIOD:
            return self.get_custom_visible_window()

        return self.get_visible_start(), None

    def get_custom_visible_window(self):
        start = self.parse_date_entry(self.custom_start_var.get(), "start date")
        end = self.parse_date_entry(self.custom_end_var.get(), "end date")
        visible_end = end + pd.Timedelta(days=1)

        if visible_end <= start:
            raise ValueError("Custom end date must be on or after the start date.")

        if start > self.host_today():
            raise ValueError("Custom start date cannot be in the future.")

        return start, visible_end

    def get_custom_period_duration(self, default_period=None):
        try:
            start, end = self.get_custom_visible_window()
            return end - start
        except ValueError:
            if default_period is None:
                raise
            return PERIOD_DURATIONS[default_period]

    @staticmethod
    def parse_date_entry(value, label):
        text = str(value).strip()
        if not text:
            raise ValueError(f"Enter a custom {label} in YYYY-MM-DD format.")

        try:
            parsed = pd.Timestamp(text)
        except Exception as exc:
            raise ValueError(f"Enter a valid custom {label} in YYYY-MM-DD format.") from exc

        if pd.isna(parsed):
            raise ValueError(f"Enter a valid custom {label} in YYYY-MM-DD format.")

        if parsed.tzinfo is not None:
            parsed = StockApp.to_host_naive_timestamp(parsed)

        return parsed.normalize()

    def get_cache_period_key(self, visible_start, visible_end):
        if self.period_var.get() != CUSTOM_PERIOD:
            return self.period_var.get()

        return (
            f"{CUSTOM_PERIOD}:"
            f"{visible_start.strftime('%Y-%m-%d')}:"
            f"{(visible_end - pd.Timedelta(days=1)).strftime('%Y-%m-%d')}"
        )

    @staticmethod
    def get_download_interval(interval):
        try:
            return DOWNLOAD_INTERVALS[interval]
        except KeyError as exc:
            raise ValueError(f"Unsupported interval: {interval}") from exc

    @staticmethod
    def get_intraday_download_period(interval, period):
        if interval not in INTRADAY_INTERVALS:
            return None

        if interval == "1m":
            return "7d"

        if interval == "2m":
            return "60d"

        if interval in {"5m", "15m", "30m"}:
            return "60d"

        if interval == "1h":
            warmup_periods = {
                "1h": "3mo",
                "1d": "3mo",
                "1wk": "3mo",
                "2wk": "3mo",
                "1mo": "3mo",
                "3mo": "6mo",
                "6mo": "1y",
                "1y": "2y",
                "2y": "2y"
            }
            return warmup_periods.get(period, period)

        if period in {"1h", "1d", "1wk", "2wk", "1mo"}:
            return "1mo"

        return period

    def validate_period_interval(self, visible_start, interval, interval_rule_period=None, interval_rule_duration=None):
        interval_rule_period = interval_rule_period or self.get_interval_rule_period()
        interval_rule_duration = (
            PERIOD_DURATIONS.get(interval_rule_period)
            if interval_rule_duration is None
            else interval_rule_duration
        )
        if interval not in self.get_allowed_intervals(interval_rule_period, interval_rule_duration):
            raise ValueError(f"Use an interval less than or equal to the selected period: {interval_rule_period}.")

        max_lookback = INTERVAL_MAX_LOOKBACKS[interval]
        if max_lookback is None:
            if visible_start is not None and visible_start > self.host_today():
                raise ValueError("Use a minute or hourly interval with the 1h period.")
            return

        if visible_start is None:
            raise ValueError("Yahoo Finance intraday data has a limited lookback window. Use a shorter period with intraday intervals.")

        oldest_allowed_start = self.host_now() - max_lookback
        if visible_start < oldest_allowed_start:
            raise ValueError(f"Yahoo Finance {interval} data is limited to roughly the last {max_lookback.days} days. Select a shorter period.")

    @staticmethod
    def get_download_start(visible_start, interval):
        if interval in INTRADAY_INTERVALS:
            return visible_start

        if interval == "1wk":
            return visible_start - pd.DateOffset(weeks=MAX_MOVING_AVERAGE_WINDOW + 20)

        if interval == "1mo":
            return visible_start - pd.DateOffset(months=MAX_MOVING_AVERAGE_WINDOW + 5)

        if interval == "3mo":
            return visible_start - pd.DateOffset(months=(MAX_MOVING_AVERAGE_WINDOW * 3) + 15)

        if interval == "6mo":
            return visible_start - pd.DateOffset(months=(MAX_MOVING_AVERAGE_WINDOW * 6) + 30)

        if interval == "1y":
            return visible_start - pd.DateOffset(years=MAX_MOVING_AVERAGE_WINDOW + 20)

        return visible_start - pd.DateOffset(days=MAX_MOVING_AVERAGE_WINDOW * 2)

    @staticmethod
    def align_timestamp_to_index(timestamp, index):
        index_tz = getattr(index, "tz", None)
        aligned_timestamp = pd.Timestamp(timestamp)

        if index_tz is None:
            if aligned_timestamp.tzinfo is not None:
                return StockApp.to_host_naive_timestamp(aligned_timestamp)
            return aligned_timestamp

        if aligned_timestamp.tzinfo is None:
            return aligned_timestamp.tz_localize(StockApp.get_host_timezone()).tz_convert(index_tz)

        return aligned_timestamp.tz_convert(index_tz)

    @staticmethod
    def get_earnings_events(ticker: str) -> pd.DataFrame:
        try:
            ticker_data = yf.Ticker(ticker)
            earnings_dates = ticker_data.earnings_dates
        except Exception as exc:
            print(f"Warning: failed to fetch earnings dates for {ticker}: {exc}. Install missing parser dependencies with: py -m pip install -r requirements.txt")
            earnings_dates = None

        events = []
        if isinstance(earnings_dates, pd.DataFrame) and not earnings_dates.empty:
            for event_time, row in earnings_dates.iterrows():
                event_time = pd.Timestamp(event_time)
                surprise = None
                if "Surprise(%)" in row and not pd.isna(row["Surprise(%)"]):
                    surprise = row["Surprise(%)"]
                elif "Surprise %" in row and not pd.isna(row["Surprise %"]):
                    surprise = row["Surprise %"]

                events.append({
                    "date": event_time,
                    "surprise": surprise
                })

        if not events:
            try:
                calendar = ticker_data.calendar
            except Exception as exc:
                print(f"Warning: failed to fetch earnings calendar for {ticker}: {exc}")
                calendar = None

            if calendar is not None:
                if isinstance(calendar, dict):
                    earnings_date = calendar.get("Earnings Date") or calendar.get("EarningsDate")
                elif isinstance(calendar, pd.DataFrame) and "Earnings Date" in calendar.index:
                    earnings_date = calendar.loc["Earnings Date"].dropna()
                elif isinstance(calendar, pd.Series):
                    earnings_date = calendar.get("Earnings Date") or calendar.get("EarningsDate")
                else:
                    earnings_date = None

                if earnings_date is not None:
                    if isinstance(earnings_date, (list, tuple, pd.Series, pd.Index)):
                        earnings_date = earnings_date[0] if len(earnings_date) else None
                    if earnings_date is not None and not pd.isna(earnings_date):
                        events.append({
                            "date": pd.Timestamp(earnings_date),
                            "surprise": None
                        })

        return pd.DataFrame(events, columns=["date", "surprise"])

    @staticmethod
    def filter_visible_earnings(earnings: pd.DataFrame, index: pd.Index) -> pd.DataFrame:
        if earnings.empty or index.empty:
            return pd.DataFrame(columns=["date", "surprise", "label"])

        start = index[0]
        end = index[-1]
        visible_events = []

        for _, event in earnings.iterrows():
            event_date = StockApp.align_timestamp_to_index(event["date"], index)
            if start <= event_date <= end:
                surprise = event.get("surprise")
                if surprise is None or pd.isna(surprise):
                    label = "E"
                elif surprise > 0:
                    label = "E+"
                elif surprise < 0:
                    label = "E-"
                else:
                    label = "E"

                visible_events.append({
                    "date": event_date,
                    "surprise": surprise,
                    "label": label
                })

        return pd.DataFrame(visible_events, columns=["date", "surprise", "label"])

    @staticmethod
    def uses_compressed_axis(interval: str) -> bool:
        return interval in COMPRESSED_AXIS_INTERVALS

    @staticmethod
    def get_plot_x(data: pd.DataFrame, compressed_x: bool) -> pd.Index:
        if compressed_x:
            return pd.RangeIndex(len(data))
        return data.index

    @staticmethod
    def get_plot_bar_width(data: pd.DataFrame, compressed_x: bool) -> float:
        if compressed_x:
            return 0.72
        return StockApp.get_bar_width(data.index)

    @staticmethod
    def timestamp_to_plot_x(timestamp: Any, index: pd.Index, compressed_x: bool) -> Any:
        if not compressed_x:
            return timestamp
        if index.empty:
            return None

        aligned_timestamp = StockApp.align_timestamp_to_index(timestamp, index)
        try:
            position = index.searchsorted(aligned_timestamp)
        except Exception:
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
        except Exception:
            pass
        return position

    @staticmethod
    def configure_x_axis(ax: Any, data: pd.DataFrame, compressed_x: bool) -> None:
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
                timestamp = StockApp.to_host_naive_timestamp(timestamp)
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

    @staticmethod
    def fetch_fundamentals(ticker: str) -> dict[str, Any]:
        ticker_data = yf.Ticker(ticker)
        raw: dict[str, Any] = {}

        for name, attribute in (
            ("info", "info"),
            ("fast_info", "fast_info"),
            ("income_stmt", "income_stmt"),
            ("quarterly_income_stmt", "quarterly_income_stmt"),
            ("balance_sheet", "balance_sheet"),
            ("quarterly_balance_sheet", "quarterly_balance_sheet"),
            ("cashflow", "cashflow"),
            ("quarterly_cashflow", "quarterly_cashflow")
        ):
            try:
                value = getattr(ticker_data, attribute)
                if name == "fast_info":
                    try:
                        value = dict(value)
                    except Exception:
                        value = {}
                raw[name] = value
            except Exception as exc:
                print(f"Warning: failed to fetch {name} for {ticker}: {exc}")
                raw[name] = pd.DataFrame() if "stmt" in name or "sheet" in name or "cashflow" in name else {}

        try:
            raw["history_5y"] = ticker_data.history(period="5y", interval="1mo", auto_adjust=True)
        except Exception as exc:
            print(f"Warning: failed to fetch history_5y for {ticker}: {exc}")
            raw["history_5y"] = pd.DataFrame()

        return raw

    def get_fundamentals(self, ticker: str, refresh: bool = False, debug: bool = False) -> dict[str, Any]:
        if refresh or ticker not in self._fundamentals_cache:
            try:
                raw = self.fetch_fundamentals(ticker)
                self._fundamentals_cache[ticker] = self.calculate_fundamental_metrics(raw, debug=debug)
            except Exception as exc:
                print(f"Warning: failed to calculate fundamentals for {ticker}: {exc}")
                self._fundamentals_cache[ticker] = {}

        return self._fundamentals_cache.get(ticker, {})

    @staticmethod
    def first_available(mapping: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = mapping.get(key)
            if not StockApp.is_missing_value(value):
                return value
        return None

    @staticmethod
    def is_missing_value(value: Any) -> bool:
        if value is None:
            return True
        try:
            return bool(pd.isna(value))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def statement_value(statement: Any, row_names: list[str], column_offset: int = 0) -> float | None:
        if not isinstance(statement, pd.DataFrame) or statement.empty:
            return None

        for row_name in row_names:
            if row_name not in statement.index or len(statement.columns) <= column_offset:
                continue

            value = statement.loc[row_name].iloc[column_offset]
            if value is not None and not pd.isna(value):
                return float(value)

        return None

    @staticmethod
    def statement_growth(statement: Any, row_names: list[str], compare_offset: int) -> float | None:
        latest = StockApp.statement_value(statement, row_names, 0)
        previous = StockApp.statement_value(statement, row_names, compare_offset)
        if latest is None or previous is None or previous == 0:
            return None

        return (latest - previous) / abs(previous)

    @staticmethod
    def statement_growth_details(
        statement: Any,
        row_names: list[str],
        compare_offset: int,
        source_statement: str,
        method: str
    ) -> tuple[float | None, dict[str, Any]]:
        if not isinstance(statement, pd.DataFrame) or statement.empty:
            return None, {"method": method, "source": source_statement, "reason": "statement unavailable"}

        for row_name in row_names:
            row = StockApp.statement_row(statement, row_name)
            if row is None or len(row) <= compare_offset:
                continue

            current = row.iloc[0]
            comparison = row.iloc[compare_offset]
            if StockApp.is_missing_value(current) or StockApp.is_missing_value(comparison) or comparison == 0:
                continue

            growth = (float(current) - float(comparison)) / abs(float(comparison))
            details = {
                "method": method,
                "source": source_statement,
                "row": row_name,
                "current_value": float(current),
                "comparison_value": float(comparison),
                "current_dates": [StockApp.format_statement_date(row.index[0])],
                "comparison_dates": [StockApp.format_statement_date(row.index[compare_offset])],
                "growth": growth
            }
            return growth, details

        return None, {"method": method, "source": source_statement, "reason": "row unavailable"}

    @staticmethod
    def statement_row(statement: Any, row_name: str) -> pd.Series | None:
        if not isinstance(statement, pd.DataFrame) or statement.empty or row_name not in statement.index:
            return None

        row = statement.loc[row_name]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        row = row.dropna()
        if row.empty:
            return None

        try:
            row.index = pd.to_datetime(row.index)
            row = row.sort_index(ascending=False)
        except Exception:
            pass

        return row

    @staticmethod
    def calculate_eps_growth_yoy(quarterly_income: Any, annual_income: Any, debug: bool = False) -> tuple[float | None, str | None, dict[str, Any]]:
        diluted_eps = StockApp.statement_row(quarterly_income, "Diluted EPS")
        basic_eps = StockApp.statement_row(quarterly_income, "Basic EPS")
        net_income = StockApp.statement_row(quarterly_income, "Net Income")
        annual_diluted_eps = StockApp.statement_row(annual_income, "Diluted EPS")

        if debug:
            print("EPS Growth YoY debug:")
            print("  source preference:")
            print("    1. quarterly_income_stmt Diluted EPS TTM vs previous TTM")
            print("    2. quarterly_income_stmt latest Diluted EPS quarter vs same quarter previous year")
            print("    3. income_stmt annual Diluted EPS YoY")
            print("  basic EPS used: no")
            print("  net income used: no")

            if basic_eps is not None:
                print(f"  Basic EPS available but ignored: {StockApp.format_debug_series(basic_eps)}")
            if net_income is not None:
                print(f"  Net Income available but ignored: {StockApp.format_debug_series(net_income)}")
            if diluted_eps is not None:
                print(f"  Diluted EPS raw quarterly values: {StockApp.format_debug_series(diluted_eps)}")
            else:
                print("  Diluted EPS unavailable in quarterly_income_stmt")
            if annual_diluted_eps is not None:
                print(f"  Diluted EPS raw annual values: {StockApp.format_debug_series(annual_diluted_eps)}")
            else:
                print("  Diluted EPS unavailable in income_stmt")

        result = StockApp.calculate_eps_growth_from_series(
            diluted_eps,
            current_count=4,
            comparison_start=4,
            comparison_count=4,
            method="TTM YoY",
            source_statement="quarterly_income_stmt",
            debug=debug
        )
        if result[0] is not None:
            return result

        result = StockApp.calculate_eps_growth_from_series(
            diluted_eps,
            current_count=1,
            comparison_start=4,
            comparison_count=1,
            method="Quarter YoY",
            source_statement="quarterly_income_stmt",
            debug=debug
        )
        if result[0] is not None:
            return result

        result = StockApp.calculate_eps_growth_from_series(
            annual_diluted_eps,
            current_count=1,
            comparison_start=1,
            comparison_count=1,
            method="Annual YoY",
            source_statement="income_stmt",
            debug=debug
        )
        if result[0] is not None:
            return result

        if debug:
            print("  method used: N/A")
            print("  current_eps: N/A")
            print("  comparison_eps: N/A")
            print("  calculated growth: N/A")
        return None, None, {"method": None, "source": None, "reason": "Diluted EPS unavailable"}

    @staticmethod
    def calculate_eps_growth_from_series(
        eps_values: pd.Series | None,
        current_count: int,
        comparison_start: int,
        comparison_count: int,
        method: str,
        source_statement: str,
        debug: bool = False
    ) -> tuple[float | None, str | None, dict[str, Any]]:
        required_values = comparison_start + comparison_count
        if eps_values is None or len(eps_values) < required_values:
            found_values = 0 if eps_values is None else len(eps_values)
            if debug:
                print(f"  {method} skipped: need {required_values} diluted EPS values, found {found_values}")
            return None, None, {"method": method, "source": source_statement, "reason": f"need {required_values}, found {found_values}"}

        current_periods = eps_values.iloc[:current_count]
        comparison_periods = eps_values.iloc[comparison_start:comparison_start + comparison_count]
        current_eps = float(current_periods.sum())
        comparison_eps = float(comparison_periods.sum())
        current_dates = [StockApp.format_statement_date(date) for date in current_periods.index]
        comparison_dates = [StockApp.format_statement_date(date) for date in comparison_periods.index]

        if comparison_eps == 0:
            if debug:
                print(f"  {method} skipped: comparison_eps is zero")
            return None, None, {"method": method, "source": source_statement, "reason": "comparison EPS is zero"}

        growth = (current_eps - comparison_eps) / abs(comparison_eps)
        details = {
            "method": method,
            "source": source_statement,
            "row": "Diluted EPS",
            "current_value": current_eps,
            "comparison_value": comparison_eps,
            "current_dates": current_dates,
            "comparison_dates": comparison_dates,
            "growth": growth
        }
        if debug:
            print(f"  method used: {method}")
            print(f"  current_eps: {current_eps}")
            print(f"  comparison_eps: {comparison_eps}")
            print(f"  current dates: {current_dates}")
            print(f"  comparison dates: {comparison_dates}")
            print(f"  source statement: {source_statement}")
            print("  source row: Diluted EPS")
            print(f"  calculated growth: {growth * 100:.2f}%")
        return growth, method, details

    @staticmethod
    def format_statement_date(value: Any) -> str:
        try:
            return pd.Timestamp(value).strftime("%Y-%m-%d")
        except Exception:
            return str(value)

    @staticmethod
    def format_debug_series(series: pd.Series) -> str:
        values = []
        for date, value in series.items():
            try:
                formatted_value = f"{float(value):.4g}"
            except Exception:
                formatted_value = str(value)
            values.append(f"{StockApp.format_statement_date(date)}={formatted_value}")
        return ", ".join(values)

    @staticmethod
    def calculate_free_cash_flow(cashflow: Any, column_offset: int = 0) -> float | None:
        operating_cash_flow = StockApp.statement_value(
            cashflow,
            ["Operating Cash Flow", "Total Cash From Operating Activities"],
            column_offset
        )
        capital_expenditure = StockApp.statement_value(
            cashflow,
            ["Capital Expenditure", "Capital Expenditures", "CapitalExpenditures"],
            column_offset
        )
        if operating_cash_flow is None or capital_expenditure is None:
            return None

        if capital_expenditure < 0:
            return operating_cash_flow + capital_expenditure

        return operating_cash_flow - capital_expenditure

    @staticmethod
    def calculate_fcf_growth_yoy(cashflow: Any) -> tuple[float | None, dict[str, Any]]:
        latest = StockApp.calculate_free_cash_flow(cashflow, 0)
        previous = StockApp.calculate_free_cash_flow(cashflow, 1)
        if latest is None or previous is None or previous == 0:
            return None, {"method": "Annual YoY", "source": "cashflow", "reason": "insufficient FCF values"}

        growth = (latest - previous) / abs(previous)
        details = {
            "method": "Annual YoY",
            "source": "cashflow",
            "row": "Operating Cash Flow - Capital Expenditures",
            "current_value": latest,
            "comparison_value": previous,
            "growth": growth
        }
        return growth, details

    @staticmethod
    def calculate_fcf_trend(cashflow: Any) -> tuple[str, float | None]:
        latest = StockApp.calculate_free_cash_flow(cashflow, 0)
        previous = StockApp.calculate_free_cash_flow(cashflow, 1)
        if latest is None or previous is None or previous == 0:
            return "Neutral", None

        relative_gap = abs(latest - previous) / abs(previous)
        if relative_gap < 0.05:
            return "Neutral", (latest - previous) / abs(previous)

        change = (latest - previous) / abs(previous)
        return ("Rising" if latest > previous else "Falling"), change

    @staticmethod
    def format_trend_with_change(direction: str, change: float | None) -> str:
        if change is None:
            return direction
        return f"{direction} ({change * 100:+.1f}%)"

    @staticmethod
    def calculate_pe_history(price_history: Any, annual_income: Any) -> dict[str, float | None]:
        result = {"pe_3y_avg": None, "pe_5y_avg": None}
        eps = StockApp.statement_row(annual_income, "Diluted EPS")
        if eps is None or not isinstance(price_history, pd.DataFrame) or price_history.empty or "Close" not in price_history:
            return result

        pe_values = []
        history = price_history.copy()
        try:
            history = StockApp.normalize_index_to_host_timezone(history, preserve_dates=True)
        except Exception:
            return result

        for date, eps_value in eps.items():
            if StockApp.is_missing_value(eps_value) or float(eps_value) == 0:
                continue
            statement_date = pd.Timestamp(date)
            if statement_date.tzinfo is not None:
                statement_date = StockApp.to_host_naive_timestamp(statement_date)
            historical_prices = history.loc[history.index <= statement_date]
            if historical_prices.empty:
                continue
            price = historical_prices["Close"].dropna().iloc[-1]
            pe_values.append((statement_date, float(price) / float(eps_value)))

        if not pe_values:
            return result

        pe_values = sorted(pe_values, key=lambda item: item[0], reverse=True)
        three_year_values = [value for _date, value in pe_values[:3]]
        five_year_values = [value for _date, value in pe_values[:5]]
        if len(three_year_values) >= 3:
            result["pe_3y_avg"] = sum(three_year_values) / len(three_year_values)
        if len(five_year_values) >= 5:
            result["pe_5y_avg"] = sum(five_year_values) / len(five_year_values)
        return result

    @staticmethod
    def valuation_history_label(current: float | None, historical_average: float | None) -> tuple[float | None, str | None]:
        if current is None or historical_average is None or historical_average == 0:
            return None, None
        difference = (float(current) - float(historical_average)) / abs(float(historical_average))
        if difference < -0.25:
            label = "below history"
        elif difference > 0.25:
            label = "above history"
        else:
            label = "near history"
        return difference, label

    @staticmethod
    def calculate_shareholder_view(metrics: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        revenue_growth = metrics["revenue_growth_yoy"]["value"]
        eps_growth = metrics["eps_growth_yoy"]["value"]
        operating_margin = metrics["operating_margin"]["value"]
        roe = metrics["return_on_equity"]["value"]
        forward_pe = metrics["forward_pe"]["value"]
        peg = metrics["peg_ratio"]["value"]
        debt_equity = metrics["debt_equity"]["value"]

        if any(StockApp.is_missing_value(value) for value in (revenue_growth, eps_growth, operating_margin, roe)):
            business_health = "Unknown"
        elif revenue_growth < 0 or eps_growth < 0:
            business_health = "Weak"
        elif revenue_growth > 0.05 and eps_growth > 0.05 and operating_margin > 0.10 and roe > 0.10:
            business_health = "Strong"
        elif sum(value > 0 for value in (revenue_growth, eps_growth, operating_margin, roe)) >= 3:
            business_health = "Stable"
        else:
            business_health = "Weak"

        if StockApp.is_missing_value(forward_pe) or StockApp.is_missing_value(peg):
            valuation = "Unknown"
        elif forward_pe < 12 and peg < 1.5:
            valuation = "Cheap"
        elif forward_pe < 20 and peg < 2:
            valuation = "Fair"
        elif forward_pe > 25 or peg > 2.5:
            valuation = "Expensive"
        else:
            valuation = "Fair"

        if StockApp.is_missing_value(debt_equity):
            balance_sheet = "Unknown"
        elif debt_equity < 0.5:
            balance_sheet = "Strong"
        elif debt_equity < 1.5:
            balance_sheet = "Moderate"
        else:
            balance_sheet = "Risky"

        if "Unknown" in {business_health, valuation, balance_sheet}:
            overall = "Unknown"
        elif business_health == "Strong" and valuation in {"Cheap", "Fair"} and balance_sheet in {"Strong", "Moderate"}:
            overall = "Attractive"
        elif business_health == "Weak" or valuation == "Expensive" or balance_sheet == "Risky":
            overall = "Risky"
        else:
            overall = "Watchlist"

        return {
            "business_health": {"label": "Business Health", "value": business_health, "type": "text", "section": "Shareholder View"},
            "valuation_view": {"label": "Valuation", "value": valuation, "type": "text", "section": "Shareholder View"},
            "balance_sheet_view": {"label": "Balance Sheet", "value": balance_sheet, "type": "text", "section": "Shareholder View"},
            "overall_fundamental_view": {"label": "Overall View", "value": overall, "type": "text", "section": "Shareholder View"}
        }

    @staticmethod
    def calculate_fundamental_metrics(raw: dict[str, Any], debug: bool = False) -> dict[str, dict[str, Any]]:
        info = raw.get("info") if isinstance(raw.get("info"), dict) else {}
        fast_info = raw.get("fast_info") if isinstance(raw.get("fast_info"), dict) else {}
        income = raw.get("income_stmt")
        quarterly_income = raw.get("quarterly_income_stmt")
        balance_sheet = raw.get("balance_sheet")
        quarterly_balance_sheet = raw.get("quarterly_balance_sheet")
        cashflow = raw.get("cashflow")
        quarterly_cashflow = raw.get("quarterly_cashflow")
        price_history = raw.get("history_5y")

        total_debt = StockApp.first_available(info, "totalDebt")
        cash = StockApp.first_available(info, "totalCash")
        total_equity = StockApp.statement_value(balance_sheet, ["Stockholders Equity", "Total Stockholder Equity"])
        if total_debt is None:
            total_debt = StockApp.statement_value(balance_sheet, ["Total Debt", "Net Debt"])
        if cash is None:
            cash = StockApp.statement_value(balance_sheet, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        if total_debt is None:
            total_debt = StockApp.statement_value(quarterly_balance_sheet, ["Total Debt", "Net Debt"])
        if cash is None:
            cash = StockApp.statement_value(quarterly_balance_sheet, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        if total_equity is None:
            total_equity = StockApp.statement_value(quarterly_balance_sheet, ["Stockholders Equity", "Total Stockholder Equity"])

        net_debt = None
        if total_debt is not None and cash is not None:
            net_debt = float(total_debt) - float(cash)

        debt_to_equity = None
        if total_debt is not None and total_equity not in (None, 0):
            debt_to_equity = float(total_debt) / float(total_equity)
        else:
            raw_debt_to_equity = StockApp.first_available(info, "debtToEquity")
            if raw_debt_to_equity is not None:
                debt_to_equity = float(raw_debt_to_equity) / 100 if raw_debt_to_equity > 10 else float(raw_debt_to_equity)

        revenue_growth, revenue_growth_details = StockApp.statement_growth_details(income, ["Total Revenue"], 1, "income_stmt", "Annual YoY")
        if revenue_growth is None:
            revenue_growth, revenue_growth_details = StockApp.statement_growth_details(quarterly_income, ["Total Revenue"], 4, "quarterly_income_stmt", "Quarter YoY")
        if revenue_growth is None:
            revenue_growth = StockApp.first_available(info, "revenueGrowth")
            revenue_growth_details = {"method": "info.revenueGrowth", "source": "info", "current_value": revenue_growth}

        eps_growth, eps_growth_method, eps_growth_details = StockApp.calculate_eps_growth_yoy(quarterly_income, income, debug=debug)

        free_cash_flow = StockApp.calculate_free_cash_flow(cashflow)
        if free_cash_flow is None:
            free_cash_flow = StockApp.calculate_free_cash_flow(quarterly_cashflow)
        fcf_growth, fcf_growth_details = StockApp.calculate_fcf_growth_yoy(cashflow)
        if fcf_growth is None:
            fcf_growth, fcf_growth_details = StockApp.calculate_fcf_growth_yoy(quarterly_cashflow)
            if fcf_growth_details.get("source") == "cashflow":
                fcf_growth_details["source"] = "quarterly_cashflow"
        fcf_trend, fcf_trend_change = StockApp.calculate_fcf_trend(cashflow)
        if fcf_trend == "Neutral" and fcf_trend_change is None:
            fcf_trend, fcf_trend_change = StockApp.calculate_fcf_trend(quarterly_cashflow)
        fcf_trend_text = StockApp.format_trend_with_change(fcf_trend, fcf_trend_change)

        operating_income = StockApp.statement_value(income, ["Operating Income", "OperatingIncome"])
        total_revenue = StockApp.statement_value(income, ["Total Revenue"])
        operating_margin = None
        if operating_income is not None and total_revenue not in (None, 0):
            operating_margin = operating_income / total_revenue
        else:
            operating_margin = StockApp.first_available(info, "operatingMargins")
        operating_margin_details = {
            "method": "Operating Income / Total Revenue" if operating_income is not None and total_revenue not in (None, 0) else "info.operatingMargins",
            "source": "income_stmt" if operating_income is not None and total_revenue not in (None, 0) else "info",
            "current_value": operating_margin,
            "comparison_value": None
        }

        current_pe = StockApp.first_available(info, "trailingPE")
        pe_history = StockApp.calculate_pe_history(price_history, income)
        pe_3y_diff, pe_3y_label = StockApp.valuation_history_label(current_pe, pe_history["pe_3y_avg"])
        pe_5y_diff, pe_5y_label = StockApp.valuation_history_label(current_pe, pe_history["pe_5y_avg"])

        metrics = {
            "market_cap": {"label": "Market Cap", "value": StockApp.first_available(info, "marketCap") or fast_info.get("market_cap"), "type": "money", "section": "Valuation"},
            "enterprise_value": {"label": "Enterprise Value", "value": StockApp.first_available(info, "enterpriseValue"), "type": "money", "section": "Valuation"},
            "trailing_pe": {"label": "Trailing P/E", "value": current_pe, "type": "multiple", "section": "Valuation"},
            "forward_pe": {"label": "Forward P/E", "value": StockApp.first_available(info, "forwardPE"), "type": "multiple", "section": "Valuation"},
            "peg_ratio": {"label": "PEG Ratio", "value": StockApp.first_available(info, "pegRatio", "trailingPegRatio"), "type": "multiple", "section": "Valuation"},
            "price_sales": {"label": "Price/Sales", "value": StockApp.first_available(info, "priceToSalesTrailing12Months"), "type": "multiple", "section": "Valuation"},
            "price_book": {"label": "Price/Book", "value": StockApp.first_available(info, "priceToBook"), "type": "multiple", "section": "Valuation"},
            "ev_revenue": {"label": "EV/Revenue", "value": StockApp.first_available(info, "enterpriseToRevenue"), "type": "multiple", "section": "Valuation"},
            "ev_ebitda": {"label": "EV/EBITDA", "value": StockApp.first_available(info, "enterpriseToEbitda"), "type": "multiple", "section": "Valuation"},
            "pe_vs_3y_avg": {"label": "P/E vs 3Y Avg", "value": pe_3y_diff, "type": "history_percent", "section": "Valuation", "history_label": pe_3y_label},
            "pe_vs_5y_avg": {"label": "P/E vs 5Y Avg", "value": pe_5y_diff, "type": "history_percent", "section": "Valuation", "history_label": pe_5y_label},
            "ev_ebitda_vs_3y_avg": {"label": "EV/EBITDA vs 3Y Avg", "value": None, "type": "history_percent", "section": "Valuation", "history_label": None},
            "price_sales_vs_3y_avg": {"label": "P/S vs 3Y Avg", "value": None, "type": "history_percent", "section": "Valuation", "history_label": None},
            "revenue_growth_yoy": {"label": "Revenue Growth YoY", "value": revenue_growth, "type": "percent", "section": "Growth", "debug": revenue_growth_details},
            "eps_growth_yoy": {"label": "EPS Growth YoY", "value": eps_growth, "type": "percent", "section": "Growth", "debug": eps_growth_details},
            "eps_growth_method": {"label": "EPS Growth Method", "value": eps_growth_method, "type": "text", "section": "Growth"},
            "free_cash_flow": {"label": "Free Cash Flow", "value": free_cash_flow, "type": "money", "section": "Cash Flow"},
            "fcf_growth_yoy": {"label": "FCF Growth YoY", "value": fcf_growth, "type": "percent", "section": "Cash Flow", "debug": fcf_growth_details},
            "fcf_trend": {"label": "FCF Trend", "value": fcf_trend_text, "type": "text", "section": "Cash Flow"},
            "operating_margin": {"label": "Operating Margin", "value": operating_margin, "type": "percent", "section": "Quality", "debug": operating_margin_details},
            "profit_margin": {"label": "Profit Margin", "value": StockApp.first_available(info, "profitMargins"), "type": "percent", "section": "Quality"},
            "return_on_equity": {"label": "Return on Equity", "value": StockApp.first_available(info, "returnOnEquity"), "type": "percent", "section": "Quality"},
            "return_on_assets": {"label": "Return on Assets", "value": StockApp.first_available(info, "returnOnAssets"), "type": "percent", "section": "Quality"},
            "total_debt": {"label": "Total Debt", "value": total_debt, "type": "money", "section": "Balance Sheet"},
            "cash": {"label": "Cash", "value": cash, "type": "money", "section": "Balance Sheet"},
            "net_debt": {"label": "Net Debt", "value": net_debt, "type": "money", "section": "Balance Sheet"},
            "debt_equity": {"label": "Debt/Equity", "value": debt_to_equity, "type": "multiple", "section": "Balance Sheet", "debug": {"method": "Total Debt / Total Equity", "source": "balance_sheet", "current_value": total_debt, "comparison_value": total_equity}},
            "current_ratio": {"label": "Current Ratio", "value": StockApp.first_available(info, "currentRatio"), "type": "multiple", "section": "Balance Sheet"}
        }

        metrics.update(StockApp.calculate_shareholder_view(metrics))

        for metric_name, metric in metrics.items():
            metric["status"] = StockApp.classify_fundamental_metric(metric_name, metric.get("value"))

        return metrics

    @staticmethod
    def format_fundamental_value(value: Any, metric_type: str) -> str:
        if StockApp.is_missing_value(value):
            return "N/A"
        if metric_type == "text":
            return str(value)
        if metric_type == "money":
            return StockApp.format_compact_number(float(value))
        if metric_type == "percent":
            return f"{float(value) * 100:.1f}%"
        if metric_type == "history_percent":
            return f"{float(value) * 100:+.0f}%"
        if metric_type == "multiple":
            return f"{float(value):.1f}x"
        return str(value)

    @staticmethod
    def classify_fundamental_metric(name: str, value: Any) -> str:
        if StockApp.is_missing_value(value):
            return "neutral"

        if name in {"trailing_pe", "forward_pe"}:
            value = float(value)
            if value < 10:
                return "good"
            if value <= 20:
                return "neutral"
            if value > 25:
                return "bad"
            return "neutral"

        if name == "peg_ratio":
            value = float(value)
            if value < 1:
                return "good"
            if value <= 2:
                return "neutral"
            return "bad"

        if name == "debt_equity":
            value = float(value)
            if value < 0.5:
                return "good"
            if value <= 1.5:
                return "neutral"
            return "bad"

        if name == "fcf_trend":
            normalized = str(value).lower()
            if normalized.startswith("rising"):
                return "good"
            if normalized.startswith("falling"):
                return "bad"
            return "neutral"

        if name in {"pe_vs_3y_avg", "pe_vs_5y_avg", "ev_ebitda_vs_3y_avg", "price_sales_vs_3y_avg"}:
            if StockApp.is_missing_value(value):
                return "neutral"
            if value < -0.25:
                return "good"
            if value > 0.25:
                return "bad"
            return "neutral"

        if name in {"business_health", "balance_sheet_view"}:
            normalized = str(value).lower()
            if normalized in {"strong", "stable", "moderate"}:
                return "good" if normalized == "strong" else "neutral"
            if normalized in {"weak", "risky"}:
                return "bad"
            return "neutral"

        if name == "valuation_view":
            normalized = str(value).lower()
            if normalized == "cheap":
                return "good"
            if normalized == "expensive":
                return "bad"
            return "neutral"

        if name == "overall_fundamental_view":
            normalized = str(value).lower()
            if normalized == "attractive":
                return "good"
            if normalized == "risky":
                return "bad"
            return "neutral"

        return "neutral"

    @staticmethod
    def print_fundamentals_debug(metrics: dict[str, dict[str, Any]]) -> None:
        print("Fundamentals debug:")
        for metric_name in ("revenue_growth_yoy", "eps_growth_yoy", "fcf_growth_yoy", "operating_margin", "debt_equity"):
            metric = metrics.get(metric_name, {})
            details = metric.get("debug", {})
            print(f"  {metric.get('label', metric_name)}:")
            print(f"    method: {details.get('method', 'N/A')}")
            print(f"    source statement: {details.get('source', 'N/A')}")
            print(f"    row: {details.get('row', 'N/A')}")
            print(f"    dates used: current={details.get('current_dates', 'N/A')} comparison={details.get('comparison_dates', 'N/A')}")
            print(f"    current value: {details.get('current_value', 'N/A')}")
            print(f"    comparison value: {details.get('comparison_value', 'N/A')}")
            print(f"    calculated growth: {StockApp.format_fundamental_value(details.get('growth'), 'percent') if details.get('growth') is not None else 'N/A'}")

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
        if "Volume" not in data:
            return data

        data["VOLUME_SMA20"] = data["Volume"].rolling(20).mean()
        data["RVOL20"] = data["Volume"] / data["VOLUME_SMA20"]
        data["RVOL"] = data["RVOL20"]
        data["VOLUME_EMA20"] = data["Volume"].ewm(span=20, adjust=False).mean()
        data["VOLUME_EMA50"] = data["Volume"].ewm(span=50, adjust=False).mean()
        data["VOLUME_SPIKE"] = data["Volume"] > (2 * data["VOLUME_SMA20"])
        return data

    @staticmethod
    def calculate_volume_trend(data: pd.DataFrame) -> str:
        ema20 = StockApp.latest_valid_value(data.get("VOLUME_EMA20", pd.Series(dtype=float)))
        ema50 = StockApp.latest_valid_value(data.get("VOLUME_EMA50", pd.Series(dtype=float)))

        if ema20 is None or ema50 is None or pd.isna(ema20) or pd.isna(ema50) or ema50 == 0:
            return "Neutral"

        relative_gap = abs(ema20 - ema50) / ema50
        if relative_gap < 0.01:
            return "Neutral"

        return "Rising" if ema20 > ema50 else "Falling"

    @staticmethod
    def compare_price_to_level(price: float | None, level: float | None) -> str:
        if not StockApp.is_valid_number(price) or not StockApp.is_valid_number(level):
            return "n/a"

        return "Above" if price >= level else "Below"

    @staticmethod
    def percentage_distance(value: float | None, reference: float | None) -> float | None:
        if not StockApp.is_valid_number(value) or not StockApp.is_valid_number(reference) or reference == 0:
            return None
        return (value - reference) / reference

    @staticmethod
    def calculate_period_price_summary(data: pd.DataFrame) -> dict[str, float | None]:
        if data.empty or "Close" not in data:
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
            "period_change": StockApp.percentage_distance(end_price, start_price),
            "period_end_vs_average": StockApp.percentage_distance(end_price, average_price)
        }

    @staticmethod
    def format_summary_percent(value: float | None) -> str:
        if value is None or pd.isna(value):
            return "N/A"
        return f"{value * 100:+.1f}%"

    @staticmethod
    def calculate_52w_levels(data: pd.DataFrame) -> tuple[float | None, float | None]:
        if data.empty or "Close" not in data:
            return None, None

        end = data.index[-1]
        try:
            start = end - pd.DateOffset(years=1)
            window = data.loc[data.index >= start]
        except Exception:
            window = data.tail(252)

        if len(window) < 50:
            return None, None

        high_source = window["High"] if "High" in window else window["Close"]
        low_source = window["Low"] if "Low" in window else window["Close"]
        return high_source.max(), low_source.min()

    @staticmethod
    def calculate_cross(data: pd.DataFrame) -> str:
        if "SMA50" not in data or "SMA200" not in data:
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
        if "DAILY_SMA50" not in data or "DAILY_SMA200" not in data:
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

    @staticmethod
    def classify_trend_score(score: int | None) -> str:
        return StockApp.classify_bullish_structure_score(score)

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

    @staticmethod
    def calculate_bullish_structure_score(data: pd.DataFrame) -> dict[str, Any]:
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
        current_price = StockApp.latest_valid_value(data.get("Close", pd.Series(dtype=float)))
        ema20 = StockApp.latest_valid_value(data.get("DAILY_EMA20", pd.Series(dtype=float)))
        ema50 = StockApp.latest_valid_value(data.get("DAILY_EMA50", pd.Series(dtype=float)))
        ema100 = StockApp.latest_valid_value(data.get("DAILY_EMA100", pd.Series(dtype=float)))
        ema200 = StockApp.latest_valid_value(data.get("DAILY_EMA200", pd.Series(dtype=float)))
        sma50 = StockApp.latest_valid_value(data.get("DAILY_SMA50", pd.Series(dtype=float)))
        sma200 = StockApp.latest_valid_value(data.get("DAILY_SMA200", pd.Series(dtype=float)))
        ema50_20_bars_ago = None
        ema50_values = data.get("DAILY_EMA50", pd.Series(dtype=float)).dropna()
        if len(ema50_values) >= 21:
            ema50_20_bars_ago = ema50_values.iloc[-21]

        rsi14 = StockApp.latest_valid_value(data.get("DAILY_RSI14", pd.Series(dtype=float)))
        macd = StockApp.latest_valid_value(data.get("DAILY_MACD", pd.Series(dtype=float)))
        macd_signal = StockApp.latest_valid_value(data.get("DAILY_MACD_SIGNAL", pd.Series(dtype=float)))
        volume = StockApp.latest_valid_value(data.get("Volume", pd.Series(dtype=float)))
        volume_sma20 = StockApp.latest_valid_value(data.get("DAILY_VOLUME_SMA20", pd.Series(dtype=float)))
        rvol20 = StockApp.latest_valid_value(data.get("DAILY_RVOL20", pd.Series(dtype=float)))
        atr14 = StockApp.latest_valid_value(data.get("DAILY_ATR14", pd.Series(dtype=float)))
        atr_pct = StockApp.latest_valid_value(data.get("DAILY_ATR_PCT", pd.Series(dtype=float)))

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
        if not all(StockApp.is_valid_number(value) for value in required_values):
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
        if all(StockApp.is_valid_number(value) for value in confirmation_values):
            confirmation_checks = [
                rvol20 > 1.1 and current_price > ema20,
                volume > volume_sma20,
                ATR_PCT_HEALTHY_MIN <= atr_pct <= ATR_PCT_HEALTHY_MAX
            ]
            confirmation_score = int(sum(confirmation_checks))
            extended_total_score = score + confirmation_score
            extended_rating = StockApp.classify_extended_bullish_score(extended_total_score, trend_score=trend_score)
        else:
            confirmation_score = None
            extended_total_score = None
            extended_rating = "N/A"

        return {
            "score": score,
            "max_score": BULLISH_STRUCTURE_SCORE_MAX,
            "rating": StockApp.classify_bullish_structure_score(score, trend_score=trend_score),
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

    @staticmethod
    def calculate_daily_trend_score(data: pd.DataFrame) -> int | None:
        return StockApp.calculate_bullish_structure_score(data)["score"]

    @staticmethod
    def calculate_daily_structural_summary(
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
        if data is None or data.empty or "Close" not in data:
            return empty_summary

        if as_of is not None:
            as_of = StockApp.align_timestamp_to_index(as_of, data.index)
            data = data.loc[data.index < as_of]
            if data.empty:
                return empty_summary

        current_price = StockApp.latest_valid_value(data["Close"])
        structure_score = StockApp.calculate_bullish_structure_score(data)
        ema20 = structure_score["ema20"]
        ema50 = structure_score["ema50"]
        ema100 = structure_score["ema100"]
        ema200 = structure_score["ema200"]
        sma50 = StockApp.latest_valid_value(data.get("DAILY_SMA50", pd.Series(dtype=float)))
        sma200 = StockApp.latest_valid_value(data.get("DAILY_SMA200", pd.Series(dtype=float)))
        ema50_20_bars_ago = structure_score["ema50_20_bars_ago"]
        rsi14 = structure_score["rsi14"]
        macd = structure_score["macd"]
        macd_signal = structure_score["macd_signal"]
        volume = structure_score["volume"]
        volume_sma20 = structure_score["volume_sma20"]
        rvol20 = structure_score["rvol20"]
        atr_pct = structure_score["atr_pct"]
        high_52w, low_52w = StockApp.calculate_52w_levels(data)
        trend_score = structure_score["score"]
        if trend_score is None:
            return empty_summary

        daily_trend = structure_score["rating"]
        ema_stack_bullish = (
            StockApp.is_valid_number(ema20)
            and StockApp.is_valid_number(ema50)
            and StockApp.is_valid_number(ema100)
            and StockApp.is_valid_number(ema200)
            and ema20 > ema50 > ema100 > ema200
        )
        ema50_rising = (
            StockApp.is_valid_number(ema50)
            and StockApp.is_valid_number(ema50_20_bars_ago)
            and ema50 > ema50_20_bars_ago
        )
        macd_above_signal = StockApp.is_valid_number(macd) and StockApp.is_valid_number(macd_signal) and macd > macd_signal
        macd_above_zero = StockApp.is_valid_number(macd) and macd > 0
        volume_above_sma20 = StockApp.is_valid_number(volume) and StockApp.is_valid_number(volume_sma20) and volume > volume_sma20
        ema20_extension = StockApp.percentage_distance(current_price, ema20)
        sma200_extension = StockApp.percentage_distance(current_price, sma200)

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
            "distance_daily_ema20": StockApp.percentage_distance(current_price, ema20),
            "daily_ema_stack": "Bullish" if ema_stack_bullish else "Mixed",
            "daily_ema50_change_20": StockApp.percentage_distance(ema50, ema50_20_bars_ago),
            "daily_ema50_trend": "Rising" if ema50_rising else "Falling",
            "daily_rsi14": rsi14,
            "daily_macd": macd,
            "daily_macd_signal": macd_signal,
            "daily_macd_vs_signal": "Above Signal" if macd_above_signal else "Below Signal",
            "daily_macd_zero": "Above 0" if macd_above_zero else "Below 0",
            "daily_rvol20": rvol20,
            "daily_atr_pct": atr_pct,
            "daily_atr_pct_state": "Healthy" if StockApp.is_valid_number(atr_pct) and ATR_PCT_HEALTHY_MIN <= atr_pct <= ATR_PCT_HEALTHY_MAX else "Outside Range",
            "distance_volume_sma20": StockApp.percentage_distance(volume, volume_sma20),
            "volume_vs_sma20": "Above" if volume_above_sma20 else "Below",
            "daily_ema20_extension": ema20_extension,
            "daily_ema20_extension_state": "OK" if StockApp.is_valid_number(ema20_extension) and ema20_extension <= 0.08 else "Extended",
            "daily_sma200_extension": sma200_extension,
            "daily_sma200_extension_state": "OK" if StockApp.is_valid_number(sma200_extension) and sma200_extension <= 0.20 else "Extended",
            "daily_trend": daily_trend,
            "daily_cross": StockApp.calculate_daily_cross(data),
            "price_vs_daily_sma50": StockApp.compare_price_to_level(current_price, sma50),
            "price_vs_daily_sma200": StockApp.compare_price_to_level(current_price, sma200),
            "distance_daily_sma50": StockApp.percentage_distance(current_price, sma50),
            "distance_daily_sma200": StockApp.percentage_distance(current_price, sma200),
            "distance_52w_high": StockApp.percentage_distance(current_price, high_52w),
            "distance_52w_low": StockApp.percentage_distance(current_price, low_52w)
        }

    @staticmethod
    def calculate_signal_summary(
        data: pd.DataFrame,
        daily_data: pd.DataFrame | None = None,
        fundamentals: dict[str, dict[str, Any]] | None = None,
        daily_summary_as_of: pd.Timestamp | None = None
    ) -> dict[str, Any]:
        if fundamentals is None and isinstance(daily_data, dict):
            fundamentals = daily_data
            daily_data = None

        current_price = StockApp.latest_valid_value(data["Close"])
        current_rvol = StockApp.latest_valid_value(data.get("RVOL", pd.Series(dtype=float)))
        current_atr = StockApp.latest_valid_value(data.get("ATR14", pd.Series(dtype=float)))
        volume_trend = StockApp.calculate_volume_trend(data)
        period_price_summary = StockApp.calculate_period_price_summary(data)
        daily_summary = StockApp.calculate_daily_structural_summary(
            daily_data,
            as_of=daily_summary_as_of
        )

        fundamentals = fundamentals or {}
        valuation = fundamentals.get("valuation_view", {}).get("value", "Unknown")
        business_health = fundamentals.get("business_health", {}).get("value", "Unknown")
        daily_trend = daily_summary["daily_trend"]
        investment_view = StockApp.calculate_investment_view(business_health, valuation, daily_trend)

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
            "price_vs_ema20": "n/a"
        }

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
    def plot_x_to_numeric(plot_x: pd.Index) -> np.ndarray:
        if isinstance(plot_x, pd.RangeIndex):
            return plot_x.to_numpy(dtype=float)

        try:
            return date2num(pd.to_datetime(plot_x).to_pydatetime())
        except Exception:
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

    @staticmethod
    def format_cursor_timestamp(value: Any) -> str:
        try:
            timestamp = pd.Timestamp(value)
        except Exception:
            return str(value)

        if timestamp.tzinfo is not None:
            timestamp = StockApp.to_host_naive_timestamp(timestamp)

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
            if item["column"] in data
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

    @staticmethod
    def get_spike_times(data: pd.DataFrame) -> pd.Index:
        if "VOLUME_SPIKE" not in data:
            return pd.Index([])

        return data.index[data["VOLUME_SPIKE"].fillna(False)]

    @staticmethod
    def draw_spike_lines(ax: Any, spike_times: pd.Index, data_index: pd.Index | None = None, compressed_x: bool = False) -> None:
        for spike_time in spike_times:
            x_value = StockApp.timestamp_to_plot_x(spike_time, data_index, compressed_x) if data_index is not None else spike_time
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

    @staticmethod
    def plot_earnings_markers(ax: Any, data: pd.DataFrame, earnings_events: pd.DataFrame, compressed_x: bool = False) -> None:
        if earnings_events.empty:
            return

        price_min = data["Low"].min() if "Low" in data else data["Close"].min()
        price_max = data["High"].max() if "High" in data else data["Close"].max()
        price_span = price_max - price_min
        marker_y = price_min + (price_span * 0.06 if price_span else 0)

        for _, event in earnings_events.iterrows():
            event_date = event["date"]
            event_x = StockApp.timestamp_to_plot_x(event_date, data.index, compressed_x)
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
            if normalized in {"above", "above signal", "above 0", "rising", "bullish", "strong bullish", "bullish confirmed", "strong bullish confirmed", "golden cross", "golden state", "cheap", "strong", "stable", "attractive", "ok", "healthy"}:
                return "#16a34a"
            if normalized in {"below", "below signal", "below 0", "falling", "bearish", "strong bearish", "strongly bearish", "weak / bearish", "death cross", "death state", "expensive", "weak", "risky", "extended", "outside range"}:
                return "#dc2626"
            if normalized in {"mixed", "neutral", "n/a", "none", "fair", "unknown", "watchlist"}:
                return "#64748b"
            return "#0ea5e9"

        def trend_score_color(value: int) -> str:
            if value is None:
                return "#64748b"
            if value >= 9:
                return "#16a34a"
            if value <= 5:
                return "#dc2626"
            return "#64748b"

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
            return "#0ea5e9"

        def format_level_distance(level_state: str, distance: float | None) -> str:
            if str(level_state).lower() == "n/a" or distance is None or pd.isna(distance):
                return "N/A"
            return f"{level_state} {self.format_summary_percent(distance)}"

        def format_distance_state(distance: float | None, positive_label: str = "Above", negative_label: str = "Below") -> str:
            if distance is None or pd.isna(distance):
                return "N/A"
            label = positive_label if distance >= 0 else negative_label
            return f"{label} {self.format_summary_percent(distance)}"

        def format_score_part(key: str, max_score: int) -> str:
            value = summary.get(key)
            if value is None:
                return "N/A"
            return f"{int(value)}/{max_score}"

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
            return f"{state} {distance}"

        def all_status_color(*values: str) -> str:
            normalized_values = [str(value).lower() for value in values]
            if all(value in {"above", "above signal", "above 0", "bullish", "rising", "ok"} for value in normalized_values):
                return "#16a34a"
            if any(value in {"below", "below signal", "below 0", "falling", "extended"} for value in normalized_values):
                return "#dc2626"
            return "#64748b"

        trend_score = summary.get("daily_trend_score")
        trend_label = summary.get("daily_trend", StockApp.classify_trend_score(trend_score))
        trend_score_max = summary.get("daily_trend_score_max", BULLISH_STRUCTURE_SCORE_MAX)
        trend_score_text = "N/A" if trend_score is None else f"{int(trend_score)}/{trend_score_max} {trend_label}"
        confirmation_score = summary.get("confirmation_score")
        confirmation_max = summary.get("confirmation_max", CONFIRMATION_SCORE_MAX)
        confirmation_score_text = "N/A" if confirmation_score is None else f"{int(confirmation_score)}/{confirmation_max}"
        extended_total_score = summary.get("extended_total_score")
        extended_max_score = summary.get("extended_max_score", EXTENDED_BULLISH_SCORE_MAX)
        extended_rating = summary.get("extended_rating", "N/A")
        extended_total_text = "N/A"
        if extended_total_score is not None:
            extended_total_text = f"{int(extended_total_score)}/{extended_max_score}"
            if extended_rating != "N/A":
                extended_total_text = f"{extended_total_text} {extended_rating}"
        rvol20 = summary.get("daily_rvol20")
        rvol20_text = "N/A" if rvol20 is None or pd.isna(rvol20) else f"{rvol20:.2f}x"
        sections = [
            (
                "Period",
                [
                    ("End/Current Price", format_price(summary.get("period_end_price", current_price)), "#111827", False),
                    ("Start Price", format_price(summary.get("period_start_price")), "#111827", False),
                    ("Period Change", self.format_summary_percent(summary.get("period_change")), distance_color(summary.get("period_change")), True),
                    ("Average Price", format_price(summary.get("period_average_price")), "#111827", False),
                    ("End vs Average", self.format_summary_percent(summary.get("period_end_vs_average")), distance_color(summary.get("period_end_vs_average")), True)
                ]
            ),
            (
                "Bullish Structure",
                [
                    ("Bullish Structure", trend_score_text, trend_score_color(trend_score), True),
                    ("Confirmation", confirmation_score_text, confirmation_score_color(confirmation_score), True),
                    ("Extended Total", extended_total_text, status_color(extended_rating), True),
                    ("Trend", format_score_part("daily_trend_score_trend", 8), "#111827", False),
                    ("Momentum", format_score_part("daily_trend_score_momentum", 3), "#111827", False),
                    ("Quality", format_score_part("daily_trend_score_quality", 3), "#111827", False)
                ]
            ),
            (
                "Trend",
                [
                    ("vs Daily EMA20", format_distance_state(summary.get("distance_daily_ema20")), distance_color(summary.get("distance_daily_ema20")), True),
                    ("vs Daily SMA50", format_level_distance(summary.get("price_vs_daily_sma50", "n/a"), summary.get("distance_daily_sma50")), distance_color(summary.get("distance_daily_sma50")), True),
                    ("vs Daily SMA200", format_level_distance(summary.get("price_vs_daily_sma200", "n/a"), summary.get("distance_daily_sma200")), distance_color(summary.get("distance_daily_sma200")), True),
                    ("EMA Stack", summary.get("daily_ema_stack", "N/A"), status_color(summary.get("daily_ema_stack", "N/A")), False),
                    ("EMA50 Trend", format_ema50_trend(), status_color(summary.get("daily_ema50_trend", "N/A")), False),
                    ("Daily Cross", summary.get("daily_cross", "N/A"), status_color(summary.get("daily_cross", "N/A")), False)
                ]
            ),
            (
                "Momentum",
                [
                    (
                        "RSI14",
                        format_rsi14(),
                        status_color("Above" if StockApp.is_valid_number(summary.get("daily_rsi14")) and summary.get("daily_rsi14") > 50 else "Below"),
                        False
                    ),
                    (
                        "MACD vs Signal",
                        summary.get("daily_macd_vs_signal", "N/A"),
                        status_color(summary.get("daily_macd_vs_signal", "N/A")),
                        False
                    ),
                    (
                        "MACD vs 0",
                        summary.get("daily_macd_zero", "N/A"),
                        status_color(summary.get("daily_macd_zero", "N/A")),
                        False
                    )
                ]
            ),
            (
                "Volume & Risk",
                [
                    ("Volume Trend", summary.get("volume_trend", "Neutral"), status_color(summary.get("volume_trend", "Neutral")), True),
                    ("Volume vs SMA20", format_level_distance(summary.get("volume_vs_sma20", "N/A"), summary.get("distance_volume_sma20")), distance_color(summary.get("distance_volume_sma20")), True),
                    ("RVOL20", rvol20_text, rvol_color(rvol20), False),
                    ("ATR% Range", summary.get("daily_atr_pct_state", "N/A"), status_color(summary.get("daily_atr_pct_state", "N/A")), False),
                    ("RVOL", rvol_text, rvol_color(current_rvol), False),
                    ("ATR 14", atr_text, "#111827", False),
                    ("EMA20 Extension", format_extension("daily_ema20_extension_state", "daily_ema20_extension"), status_color(summary.get("daily_ema20_extension_state", "N/A")), False),
                    ("SMA200 Extension", format_extension("daily_sma200_extension_state", "daily_sma200_extension"), status_color(summary.get("daily_sma200_extension_state", "N/A")), False)
                ]
            ),
            (
                "Context",
                [
                    ("From Daily 52W High", self.format_summary_percent(summary.get("distance_52w_high")), from_52w_high_color(summary.get("distance_52w_high")), False),
                    ("From Daily 52W Low", self.format_summary_percent(summary.get("distance_52w_low")), from_52w_low_color(summary.get("distance_52w_low")), False),
                    ("Valuation", summary.get("valuation", "Unknown"), status_color(summary.get("valuation", "Unknown")), False),
                    ("Business", summary.get("business_health", "Unknown"), status_color(summary.get("business_health", "Unknown")), False),
                    ("Investment View", summary.get("investment_view", "Watchlist"), status_color(summary.get("investment_view", "Watchlist")), False)
                ]
            )
        ]

        card_left = 0.03
        card_width = 0.94
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
            card_left + 0.016,
            card_top - 0.030,
            "Signal Summary",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9.6,
            fontweight="bold",
            color="#111827",
            zorder=7
        )

        total_rows = sum(len(rows) for _section, rows in sections)
        total_sections = len(sections)
        row_step = min(0.029, (card_height - 0.112) / max(total_rows + (total_sections * 0.98), 1))
        row_step = max(row_step, 0.016)
        title_rule_gap = row_step * 0.68
        after_rule_gap = row_step * 0.20
        section_gap = row_step * 0.22
        section_font_size = 7.7 if row_step >= 0.019 else 7.1
        row_font_size = 6.5 if row_step >= 0.019 else 6.0

        row_y = card_top - 0.064
        for section, section_rows in sections:
            if row_y < card_bottom + 0.014:
                return

            ax.text(
                card_left + 0.016,
                row_y,
                section,
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=section_font_size,
                fontweight="bold",
                color="#111827",
                zorder=7
            )
            ax.plot(
                [card_left + 0.016, card_right - 0.016],
                [row_y - title_rule_gap, row_y - title_rule_gap],
                transform=ax.transAxes,
                color="#e5e7eb",
                linewidth=0.6,
                zorder=6
            )
            row_y -= title_rule_gap + after_rule_gap

            for label, value, color, bold_value in section_rows:
                if row_y < card_bottom + 0.012:
                    return

                value_text = str(value).upper() if label.startswith("vs ") or label in {"Volume Trend"} else str(value)
                ax.text(
                    card_left + 0.016,
                    row_y,
                    label,
                    transform=ax.transAxes,
                    ha="left",
                    va="top",
                    fontsize=row_font_size,
                    color="#374151",
                    zorder=7
                )
                ax.text(
                    card_right - 0.016,
                    row_y,
                    value_text,
                    transform=ax.transAxes,
                    ha="right",
                    va="top",
                    fontsize=row_font_size,
                    fontweight="bold" if bold_value else "normal",
                    color=color,
                    zorder=7
                )
                row_y -= row_step

            row_y -= section_gap

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

        def status_label(name: str, status: str, value: Any) -> str:
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

    def plot_volume_panel(
        self,
        volume_ax: Any,
        data: pd.DataFrame,
        price_ax: Any,
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

        volume_ax.bar(
            plot_x,
            data["Volume"],
            label="Volume",
            width=bar_width,
            color=bar_colors.tolist(),
            alpha=0.55,
            edgecolor="none"
        )
        if show_volume_sma20:
            volume_ax.plot(
                plot_x,
                data["VOLUME_SMA20"],
                label="Volume SMA 20",
                linewidth=2.2,
                color="#2563eb"
            )
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
            self.annotate_point(
                volume_ax,
                max_volume_x,
                max_volume,
                f"Max Vol {self.format_compact_number(max_volume)}",
                "#2563eb"
            )

        rvol_values = data["RVOL"].dropna()
        if not rvol_values.empty:
            max_rvol_time = rvol_values.idxmax()
            max_rvol = rvol_values.loc[max_rvol_time]
            max_rvol_x = self.timestamp_to_plot_x(max_rvol_time, data.index, compressed_x)
            self.annotate_point(
                rvol_ax,
                max_rvol_x,
                max_rvol,
                f"Max RVOL {max_rvol:.2f}x",
                "#f97316"
            )

        handles, labels = volume_ax.get_legend_handles_labels()
        rvol_handles, rvol_labels = rvol_ax.get_legend_handles_labels()
        volume_ax.legend(
            handles + rvol_handles,
            labels + rvol_labels,
            loc="upper left",
            ncols=3,
            fontsize=8,
            framealpha=0.88
        )

        return rvol_ax

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

        if "Volume" in data:
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

    @staticmethod
    def add_indicators(data):
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

        data = StockApp.calculate_volume_indicators(data)

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

    def update_chart(self, refresh_fundamentals: bool = False):
        try:
            ticker = self.get_ticker()
            data, visible_start, visible_end = self.download_data()
            data = self.add_indicators(data)
            if visible_start is not None:
                visible_start = self.align_timestamp_to_index(visible_start, data.index)
                data = data.loc[data.index >= visible_start]
            if visible_end is not None:
                visible_end = self.align_timestamp_to_index(visible_end, data.index)
                data = data.loc[data.index < visible_end]
            if data.empty:
                raise ValueError("No data remains after applying the selected display period.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.figure.clear()
        self._cursor_contexts = {}

        extra_panels = (
            int(self.show_rsi.get())
            + int(self.show_macd.get())
            + int(self.show_volume.get())
            + int(self.show_atr.get())
        )
        total_rows = 1 + extra_panels

        show_fundamentals = self.show_fundamentals.get()
        chart_grid = self.figure.add_gridspec(
            total_rows,
            2,
            width_ratios=[5.35, 1.35],
            wspace=0.08,
            hspace=0.28
        )
        price_ax = self.figure.add_subplot(chart_grid[0, 0])
        if show_fundamentals:
            summary_ax = None
            fundamentals_ax = self.figure.add_subplot(chart_grid[:, 1])
        else:
            summary_ax = self.figure.add_subplot(chart_grid[:, 1])
            fundamentals_ax = None

        compressed_x = self.uses_compressed_axis(self.interval_var.get())
        plot_x = self.get_plot_x(data, compressed_x)
        selected_indicators = self.get_selected_indicators()
        debug_fundamentals = self.show_debug_fundamentals.get()
        fundamental_metrics = self.get_fundamentals(ticker, refresh=refresh_fundamentals, debug=debug_fundamentals) if show_fundamentals else {}
        if show_fundamentals and debug_fundamentals:
            self.print_fundamentals_debug(fundamental_metrics)
        daily_signal_data = self.download_daily_signal_data(ticker, as_of=visible_end)
        signal_summary = self.calculate_signal_summary(
            data,
            daily_signal_data,
            fundamental_metrics,
            daily_summary_as_of=visible_end
        )
        spike_times = self.get_spike_times(data) if self.show_volume.get() else pd.Index([])
        earnings_events = pd.DataFrame(columns=["date", "surprise", "label"])
        if self.show_earnings.get():
            earnings = self.get_earnings_events(ticker)
            earnings_events = self.filter_visible_earnings(earnings, data.index)

        self.plot_price_panel(
            price_ax,
            data,
            ticker,
            self.price_style_var.get(),
            selected_indicators,
            spike_times,
            earnings_events,
            plot_x,
            compressed_x
        )
        self.configure_x_axis(price_ax, data, compressed_x)
        price_cursor_series = [
            self.make_cursor_series("Close", "Close", "#2563eb")
        ]
        price_cursor_specs = [
            ("EMA9", "EMA 9", "#f97316"),
            ("EMA12", "EMA 12", "#a855f7"),
            ("EMA20", "EMA 20", "#0ea5e9"),
            ("EMA50", "EMA 50", "#16a34a"),
            ("EMA100", "EMA 100", "#14b8a6"),
            ("EMA200", "EMA 200", "#64748b"),
            ("SMA20", "SMA 20", "#f59e0b"),
            ("SMA50", "SMA 50", "#22c55e"),
            ("SMA100", "SMA 100", "#14b8a6"),
            ("SMA200", "SMA 200", "#475569")
        ]
        price_cursor_series.extend(
            self.make_cursor_series(label, column, color)
            for column, label, color in price_cursor_specs
            if selected_indicators.get(column)
        )
        if selected_indicators.get("BOLLINGER"):
            price_cursor_series.extend([
                self.make_cursor_series("Bollinger Upper", "BB_UPPER", "#64748b"),
                self.make_cursor_series("Bollinger Lower", "BB_LOWER", "#64748b")
            ])
        self.register_cursor_axis(price_ax, data, plot_x, price_cursor_series)
        if summary_ax is not None:
            self.add_signal_summary_box(summary_ax, signal_summary, card_bottom=0.03, card_height=0.94)
        if fundamentals_ax is not None:
            self.draw_fundamental_dashboard(fundamentals_ax, fundamental_metrics, card_bottom=0.03, card_height=0.94)

        row = 1

        if self.show_rsi.get():
            rsi_ax = self.figure.add_subplot(chart_grid[row, 0], sharex=price_ax)
            rsi_ax.plot(plot_x, data["RSI"], label="RSI 14")
            rsi_ax.axhline(70, linestyle="--", linewidth=0.8)
            rsi_ax.axhline(30, linestyle="--", linewidth=0.8)
            rsi_ax.set_ylabel("RSI")
            rsi_ax.grid(True, alpha=0.3)
            rsi_ax.legend(loc="upper left")
            self.configure_x_axis(rsi_ax, data, compressed_x)
            self.register_cursor_axis(
                rsi_ax,
                data,
                plot_x,
                [self.make_cursor_series("RSI 14", "RSI", "#2563eb")]
            )
            row += 1

        if self.show_macd.get():
            macd_ax = self.figure.add_subplot(chart_grid[row, 0], sharex=price_ax)
            macd_ax.plot(plot_x, data["MACD"], label="MACD")
            macd_ax.plot(plot_x, data["MACD_SIGNAL"], label="Signal")
            macd_ax.axhline(0, linewidth=0.8)
            macd_ax.set_ylabel("MACD")
            macd_ax.grid(True, alpha=0.3)
            macd_ax.legend(loc="upper left")
            self.configure_x_axis(macd_ax, data, compressed_x)
            self.register_cursor_axis(
                macd_ax,
                data,
                plot_x,
                [
                    self.make_cursor_series("MACD", "MACD", "#2563eb"),
                    self.make_cursor_series("Signal", "MACD_SIGNAL", "#f97316")
                ]
            )
            row += 1

        if self.show_volume.get():
            volume_ax = self.figure.add_subplot(chart_grid[row, 0], sharex=price_ax)
            rvol_ax = self.plot_volume_panel(
                volume_ax,
                data,
                price_ax,
                plot_x,
                compressed_x,
                show_volume_sma20=self.show_volume_sma20.get(),
                show_volume_ema50=self.show_volume_ema50.get(),
                show_spike_shading=False
            )
            self.configure_x_axis(volume_ax, data, compressed_x)
            volume_cursor_series = [
                self.make_cursor_series("Volume", "Volume", "#64748b")
            ]
            if self.show_volume_sma20.get():
                volume_cursor_series.append(self.make_cursor_series("Vol SMA 20", "VOLUME_SMA20", "#2563eb"))
            if self.show_volume_ema50.get():
                volume_cursor_series.append(self.make_cursor_series("Vol EMA 50", "VOLUME_EMA50", "#0891b2"))
            self.register_cursor_axis(volume_ax, data, plot_x, volume_cursor_series)
            self.register_cursor_axis(
                rvol_ax,
                data,
                plot_x,
                [self.make_cursor_series("RVOL", "RVOL", "#f97316")]
            )
            row += 1

        if self.show_atr.get():
            atr_ax = self.figure.add_subplot(chart_grid[row, 0], sharex=price_ax)
            atr_ax.plot(plot_x, data["ATR14"], label="ATR 14")
            atr_ax.set_ylabel("ATR")
            atr_ax.grid(True, alpha=0.3)
            atr_ax.legend(loc="upper left")
            self.configure_x_axis(atr_ax, data, compressed_x)
            self.register_cursor_axis(
                atr_ax,
                data,
                plot_x,
                [self.make_cursor_series("ATR 14", "ATR14", "#2563eb")]
            )

        self.canvas.draw()
        self.save_settings()


def parse_args():
    parser = argparse.ArgumentParser(description="Stock technical chart viewer")
    parser.add_argument(
        "--ticker",
        default="",
        help="Ticker symbol to load on startup, for example AAPL, MSFT, SPY, or BTC-USD"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    tk_root = tk.Tk()
    app = StockApp(tk_root, initial_ticker=args.ticker.strip().upper())
    tk_root.mainloop()
