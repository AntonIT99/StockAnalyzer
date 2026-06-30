"""StockApp composition root."""

import tkinter as tk
from typing import Any
import pandas as pd
from .cache import build_cache_key, get_cache_path, load_cached_data, save_cached_data
from .config import PERIOD_OPTIONS
from .ohlcv import drop_incomplete_price_rows, flatten_yfinance_columns, get_bar_width, resample_ohlcv
from .time_utils import get_host_timezone, host_now, host_today, normalize_index_to_host_timezone, to_host_naive_timestamp
from .chart_update import ChartUpdateMixin
from .fundamental_dashboard import FundamentalDashboardMixin
from .price_chart import PriceChartMixin
from .signal_summary_chart import SignalSummaryChartMixin
from .volume_chart import VolumeChartMixin
from .cursor import ChartCursorMixin
from .data import MarketDataMixin
from .earnings import EarningsMixin
from .fundamentals import FundamentalsMixin
from .periods import PeriodSelectionMixin
from .plot_axes import PlotAxisMixin
from .technical import TechnicalAnalysisMixin
from .ui import SettingsAndUIMixin

# noinspection PyTypeChecker,PyPandasTruthValueIsAmbiguous,PyShadowingNames,PyUnusedLocal,PyUnresolvedReferences,PyUnboundLocalVariable,PyBroadException
class StockApp(
    SettingsAndUIMixin,
    PeriodSelectionMixin,
    MarketDataMixin,
    EarningsMixin,
    PlotAxisMixin,
    FundamentalsMixin,
    TechnicalAnalysisMixin,
    ChartCursorMixin,
    PriceChartMixin,
    SignalSummaryChartMixin,
    FundamentalDashboardMixin,
    VolumeChartMixin,
    ChartUpdateMixin,
):
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
