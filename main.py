import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any

import yfinance as yf
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.ticker import FuncFormatter


MAX_MOVING_AVERAGE_WINDOW = 200
CACHE_DIR = Path(__file__).with_name(".stock_cache")
SETTINGS_PATH = Path(__file__).with_name(".stock_settings.json")
INTRADAY_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "1h"}
PERIOD_OPTIONS = ["1h", "1d", "5d", "15d", "1mo", "3mo", "6mo", "1y", "2y", "3y", "4y", "5y", "10y", "max"]
INTERVAL_OPTIONS = ["1m", "2m", "5m", "15m", "30m", "1h", "1d", "5d", "1wk", "1mo", "3mo", "6mo", "1y"]
PERIOD_DURATIONS = {
    "1h": pd.Timedelta(hours=1),
    "1d": pd.Timedelta(days=1),
    "5d": pd.Timedelta(days=5),
    "15d": pd.Timedelta(days=15),
    "1mo": pd.Timedelta(days=30),
    "3mo": pd.Timedelta(days=90),
    "6mo": pd.Timedelta(days=180),
    "1y": pd.Timedelta(days=365),
    "2y": pd.Timedelta(days=365 * 2),
    "3y": pd.Timedelta(days=365 * 3),
    "4y": pd.Timedelta(days=365 * 4),
    "5y": pd.Timedelta(days=365 * 5),
    "10y": pd.Timedelta(days=365 * 10),
    "max": None
}
INTERVAL_DURATIONS = {
    "1m": pd.Timedelta(minutes=1),
    "2m": pd.Timedelta(minutes=2),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "1d": pd.Timedelta(days=1),
    "5d": pd.Timedelta(days=5),
    "1wk": pd.Timedelta(weeks=1),
    "1mo": pd.Timedelta(days=30),
    "3mo": pd.Timedelta(days=90),
    "6mo": pd.Timedelta(days=180),
    "1y": pd.Timedelta(days=365)
}
INTERVAL_MAX_LOOKBACKS = {
    "1m": pd.Timedelta(days=8),
    "2m": pd.Timedelta(days=60),
    "5m": pd.Timedelta(days=60),
    "15m": pd.Timedelta(days=60),
    "30m": pd.Timedelta(days=60),
    "1h": pd.Timedelta(days=730),
    "1d": None,
    "5d": None,
    "1wk": None,
    "1mo": None,
    "3mo": None,
    "6mo": None,
    "1y": None
}
DOWNLOAD_INTERVALS = {
    "1m": "1m",
    "2m": "2m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "1d": "1d",
    "5d": "5d",
    "1wk": "1wk",
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "1d",
    "1y": "1d"
}
RESAMPLE_RULES = {
    "6mo": "6ME",
    "1y": "YE"
}
CACHE_TTLS = {
    "1m": pd.Timedelta(minutes=2),
    "2m": pd.Timedelta(minutes=5),
    "5m": pd.Timedelta(minutes=10),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(minutes=15),
    "1d": pd.Timedelta(hours=6),
    "5d": pd.Timedelta(hours=12),
    "1wk": pd.Timedelta(days=1),
    "1mo": pd.Timedelta(days=1),
    "3mo": pd.Timedelta(days=1),
    "6mo": pd.Timedelta(days=1),
    "1y": pd.Timedelta(days=1)
}
INDICATOR_SETTINGS = [
    "show_ema9",
    "show_ema12",
    "show_ema20",
    "show_ema50",
    "show_ema200",
    "show_sma20",
    "show_sma50",
    "show_sma100",
    "show_sma200",
    "show_bollinger",
    "show_rsi",
    "show_macd",
    "show_volume",
    "show_volume_ema50",
    "show_atr",
    "show_earnings"
]


class StockApp:
    def __init__(self, root, initial_ticker=""):
        settings = self.load_settings()

        self.root = root
        self.root.title("Stock Technical Chart")
        self.root.geometry("1600x900")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        ticker = initial_ticker or settings.get("ticker", "")
        period = settings.get("period", "6mo")
        if period not in PERIOD_OPTIONS:
            period = "6mo"

        interval = settings.get("interval", "1d")
        if interval not in self.get_allowed_intervals(period):
            interval = "1d" if "1d" in self.get_allowed_intervals(period) else self.get_allowed_intervals(period)[-1]

        self.ticker_var = tk.StringVar(value=ticker)
        self.period_var = tk.StringVar(value=period)
        self.interval_var = tk.StringVar(value=interval)
        self.price_style_var = tk.StringVar(value=settings.get("price_style", "Line"))
        if self.price_style_var.get() not in {"Line", "Candlesticks"}:
            self.price_style_var.set("Line")

        indicator_settings = settings.get("indicators", {})
        self.show_ema9 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema9", False)))
        self.show_ema12 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema12", False)))
        self.show_ema20 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema20", False)))
        self.show_ema50 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema50", False)))
        self.show_ema200 = tk.BooleanVar(value=bool(indicator_settings.get("show_ema200", False)))
        self.show_sma20 = tk.BooleanVar(value=bool(indicator_settings.get("show_sma20", False)))
        self.show_sma50 = tk.BooleanVar(value=bool(indicator_settings.get("show_sma50", False)))
        self.show_sma100 = tk.BooleanVar(value=bool(indicator_settings.get("show_sma100", False)))
        self.show_sma200 = tk.BooleanVar(value=bool(indicator_settings.get("show_sma200", False)))
        self.show_bollinger = tk.BooleanVar(value=bool(indicator_settings.get("show_bollinger", False)))
        self.show_rsi = tk.BooleanVar(value=bool(indicator_settings.get("show_rsi", False)))
        self.show_macd = tk.BooleanVar(value=bool(indicator_settings.get("show_macd", False)))
        self.show_volume = tk.BooleanVar(value=bool(indicator_settings.get("show_volume", False)))
        self.show_volume_ema50 = tk.BooleanVar(value=bool(indicator_settings.get("show_volume_ema50", True)))
        self.show_atr = tk.BooleanVar(value=bool(indicator_settings.get("show_atr", False)))
        self.show_earnings = tk.BooleanVar(value=bool(indicator_settings.get("show_earnings", False)))

        self._build_ui()
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
        period_combobox.bind("<<ComboboxSelected>>", lambda _event: self.update_interval_options(persist=True))

        ttk.Label(top_controls, text="Interval:").pack(side="left", padx=(15, 0))
        self.interval_combobox = ttk.Combobox(
            top_controls,
            textvariable=self.interval_var,
            width=8,
            state="readonly"
        )
        self.interval_combobox.pack(side="left", padx=5)
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

        ttk.Button(top_controls, text="Update", command=self.update_chart).pack(side="left", padx=15)

        ttk.Checkbutton(indicator_controls, text="EMA 9", variable=self.show_ema9, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 12", variable=self.show_ema12, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 20", variable=self.show_ema20, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 50", variable=self.show_ema50, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="EMA 200", variable=self.show_ema200, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="SMA 20", variable=self.show_sma20, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="SMA 50", variable=self.show_sma50, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="SMA 100", variable=self.show_sma100, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="SMA 200", variable=self.show_sma200, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Bollinger", variable=self.show_bollinger, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="RSI", variable=self.show_rsi, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="MACD", variable=self.show_macd, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Volume", variable=self.show_volume, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Vol EMA50", variable=self.show_volume_ema50, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="ATR 14", variable=self.show_atr, command=self.save_settings).pack(side="left", padx=8)
        ttk.Checkbutton(indicator_controls, text="Earnings", variable=self.show_earnings, command=self.save_settings).pack(side="left", padx=8)

        self.figure = Figure(figsize=(11, 7), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_interval_options(self, persist=False):
        allowed_intervals = self.get_allowed_intervals(self.period_var.get())
        self.interval_combobox["values"] = allowed_intervals

        if self.interval_var.get() not in allowed_intervals:
            self.interval_var.set(allowed_intervals[-1])

        if persist:
            self.save_settings()

    @staticmethod
    def get_allowed_intervals(period):
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

        if INTERVAL_DURATIONS[interval] > period_duration:
            return False

        return max_lookback is None or period_duration <= max_lookback

    def download_data(self):
        ticker = self.get_ticker()
        visible_start = self.get_visible_start()
        interval = self.interval_var.get()
        download_interval = self.get_download_interval(interval)

        download_kwargs = {
            "interval": download_interval,
            "auto_adjust": True,
            "progress": False
        }

        if visible_start is None:
            self.validate_period_interval(visible_start, interval)
            download_kwargs["period"] = self.period_var.get()
        else:
            self.validate_period_interval(visible_start, interval)
            intraday_period = self.get_intraday_download_period(interval, self.period_var.get())
            if intraday_period is None:
                download_kwargs["start"] = self.get_download_start(visible_start, interval)
                download_kwargs["end"] = pd.Timestamp.now().normalize() + pd.Timedelta(days=1)
            else:
                download_kwargs["period"] = intraday_period

        cache_key = self.build_cache_key(ticker, self.period_var.get(), interval, download_interval)
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

        if interval in RESAMPLE_RULES:
            data = self.resample_ohlcv(data, RESAMPLE_RULES[interval])

        return data.dropna(), visible_start

    @staticmethod
    def flatten_yfinance_columns(data: pd.DataFrame) -> pd.DataFrame:
        if data is None or data.empty:
            return pd.DataFrame()

        flattened = data.copy()
        if isinstance(flattened.columns, pd.MultiIndex):
            flattened.columns = flattened.columns.get_level_values(0)

        return flattened

    @staticmethod
    def build_cache_key(ticker, period, interval, download_interval):
        cache_parts = {
            "version": 3,
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "download_interval": download_interval,
            "auto_adjust": True
        }
        cache_text = json.dumps(cache_parts, sort_keys=True)
        return hashlib.sha256(cache_text.encode("utf-8")).hexdigest()

    @staticmethod
    def get_cache_path(cache_key):
        return CACHE_DIR / f"{cache_key}.pkl"

    @staticmethod
    def load_cached_data(cache_key, interval):
        cache_path = StockApp.get_cache_path(cache_key)
        if not cache_path.exists():
            return None

        try:
            payload = pd.read_pickle(cache_path)
            fetched_at = pd.Timestamp(payload["fetched_at"])
            data = payload["data"]
        except Exception:
            return None

        cache_ttl = CACHE_TTLS.get(interval, pd.Timedelta(hours=6))
        if pd.Timestamp.now() - fetched_at > cache_ttl:
            return None

        return data.copy()

    @staticmethod
    def save_cached_data(cache_key, data):
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            pd.to_pickle(
                {
                    "fetched_at": pd.Timestamp.now(),
                    "data": data.copy()
                },
                StockApp.get_cache_path(cache_key)
            )
        except Exception:
            pass

    def get_ticker(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            raise ValueError("Enter a ticker symbol.")

        self.ticker_var.set(ticker)
        return ticker

    def get_visible_start(self):
        period = self.period_var.get()
        end = pd.Timestamp.now()

        period_offsets = {
            "1h": pd.DateOffset(hours=1),
            "1d": pd.DateOffset(days=1),
            "5d": pd.DateOffset(days=5),
            "15d": pd.DateOffset(days=15),
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
            return "5d"

        if interval == "2m":
            return "1mo"

        if interval in {"5m", "15m", "30m"}:
            return "1mo"

        if period in {"1h", "1d", "5d", "15d", "1mo"}:
            return "1mo"

        return period

    def validate_period_interval(self, visible_start, interval):
        if interval not in self.get_allowed_intervals(self.period_var.get()):
            raise ValueError(f"Use an interval less than or equal to the selected period: {self.period_var.get()}.")

        max_lookback = INTERVAL_MAX_LOOKBACKS[interval]
        if max_lookback is None:
            if visible_start is not None and visible_start > pd.Timestamp.now().normalize():
                raise ValueError("Use a minute or hourly interval with the 1h period.")
            return

        if visible_start is None:
            raise ValueError("Yahoo Finance intraday data has a limited lookback window. Use a shorter period with intraday intervals.")

        oldest_allowed_start = pd.Timestamp.now() - max_lookback
        if visible_start < oldest_allowed_start:
            raise ValueError(f"Yahoo Finance {interval} data is limited to roughly the last {max_lookback.days} days. Select a shorter period.")

    @staticmethod
    def get_download_start(visible_start, interval):
        if interval in INTRADAY_INTERVALS:
            return visible_start

        if interval == "1wk":
            return visible_start - pd.DateOffset(weeks=MAX_MOVING_AVERAGE_WINDOW + 20)

        if interval == "5d":
            return visible_start - pd.DateOffset(days=MAX_MOVING_AVERAGE_WINDOW * 7)

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
    def resample_ohlcv(data, rule):
        resample_columns = {}

        if "Open" in data:
            resample_columns["Open"] = "first"
        if "High" in data:
            resample_columns["High"] = "max"
        if "Low" in data:
            resample_columns["Low"] = "min"
        if "Close" in data:
            resample_columns["Close"] = "last"
        if "Volume" in data:
            resample_columns["Volume"] = "sum"

        resampled_data = data.resample(rule).agg(resample_columns).dropna()
        if not resampled_data.empty and resampled_data.index[-1] > data.index[-1]:
            resampled_data = resampled_data.rename(index={resampled_data.index[-1]: data.index[-1]})

        return resampled_data

    @staticmethod
    def align_timestamp_to_index(timestamp, index):
        index_tz = getattr(index, "tz", None)
        aligned_timestamp = pd.Timestamp(timestamp)

        if index_tz is None:
            if aligned_timestamp.tzinfo is not None:
                return aligned_timestamp.tz_convert(None)
            return aligned_timestamp

        if aligned_timestamp.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo
            return aligned_timestamp.tz_localize(local_tz).tz_convert(index_tz)

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
    def get_bar_width(index):
        if len(index) < 2:
            return 0.8

        deltas = pd.Series(index).diff().dropna()
        if deltas.empty:
            return 0.8

        median_delta = deltas.median()
        return max(median_delta / pd.Timedelta(days=1) * 0.8, 0.0005)

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
    def latest_valid_value(series):
        values = series.dropna()
        if values.empty:
            return None

        return values.iloc[-1]

    @staticmethod
    def calculate_volume_indicators(data: pd.DataFrame) -> pd.DataFrame:
        if "Volume" not in data:
            return data

        data["VOLUME_AVG30"] = data["Volume"].rolling(30).mean()
        data["RVOL"] = data["Volume"] / data["VOLUME_AVG30"]
        data["VOLUME_EMA20"] = data["Volume"].ewm(span=20, adjust=False).mean()
        data["VOLUME_EMA50"] = data["Volume"].ewm(span=50, adjust=False).mean()
        data["VOLUME_SPIKE"] = data["Volume"] > (2 * data["VOLUME_AVG30"])
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
        if price is None or level is None or pd.isna(price) or pd.isna(level):
            return "n/a"

        return "Above" if price >= level else "Below"

    @staticmethod
    def calculate_signal_summary(data: pd.DataFrame) -> dict[str, Any]:
        current_price = StockApp.latest_valid_value(data["Close"])
        current_rvol = StockApp.latest_valid_value(data.get("RVOL", pd.Series(dtype=float)))
        current_atr = StockApp.latest_valid_value(data.get("ATR14", pd.Series(dtype=float)))
        sma50 = StockApp.latest_valid_value(data.get("SMA50", pd.Series(dtype=float)))
        sma200 = StockApp.latest_valid_value(data.get("SMA200", pd.Series(dtype=float)))
        ema20 = StockApp.latest_valid_value(data.get("EMA20", pd.Series(dtype=float)))
        volume_trend = StockApp.calculate_volume_trend(data)

        price_conditions = []
        for level in (sma50, sma200, ema20):
            if current_price is not None and level is not None and not pd.isna(current_price) and not pd.isna(level):
                price_conditions.append(current_price >= level)

        available_conditions = price_conditions
        bullish_count = sum(available_conditions)

        if not available_conditions:
            overall_trend = "Neutral"
        elif bullish_count >= 2 and volume_trend != "Falling":
            overall_trend = "Bullish"
        elif bullish_count <= 1 and volume_trend != "Rising":
            overall_trend = "Bearish"
        else:
            overall_trend = "Neutral"

        return {
            "current_price": current_price,
            "price_vs_sma50": StockApp.compare_price_to_level(current_price, sma50),
            "price_vs_sma200": StockApp.compare_price_to_level(current_price, sma200),
            "price_vs_ema20": StockApp.compare_price_to_level(current_price, ema20),
            "current_rvol": current_rvol,
            "atr14": current_atr,
            "volume_trend": volume_trend,
            "overall_trend": overall_trend
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
    def get_spike_times(data: pd.DataFrame) -> pd.Index:
        if "VOLUME_SPIKE" not in data:
            return pd.Index([])

        return data.index[data["VOLUME_SPIKE"].fillna(False)]

    @staticmethod
    def draw_spike_lines(ax: Any, spike_times: pd.Index) -> None:
        for spike_time in spike_times:
            ax.axvline(
                spike_time,
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
        earnings_events: pd.DataFrame
    ) -> None:
        if price_style == "Candlesticks":
            self.plot_candlesticks(ax, data)
        else:
            ax.plot(data.index, data["Close"], label="Close", linewidth=1.6, color="#2563eb")

        indicator_specs = [
            ("EMA9", "EMA 9"),
            ("EMA12", "EMA 12"),
            ("EMA20", "EMA 20"),
            ("EMA50", "EMA 50"),
            ("EMA200", "EMA 200"),
            ("SMA20", "SMA 20"),
            ("SMA50", "SMA 50"),
            ("SMA100", "SMA 100"),
            ("SMA200", "SMA 200")
        ]
        for column, label in indicator_specs:
            if selected_indicators.get(column):
                ax.plot(data.index, data[column], label=label, linewidth=1)

        if selected_indicators.get("BOLLINGER"):
            ax.plot(data.index, data["BB_UPPER"], label="Bollinger Upper", linewidth=0.9)
            ax.plot(data.index, data["BB_LOWER"], label="Bollinger Lower", linewidth=0.9)

        self.draw_spike_lines(ax, spike_times)
        self.plot_earnings_markers(ax, data, earnings_events)

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
    def plot_earnings_markers(ax: Any, data: pd.DataFrame, earnings_events: pd.DataFrame) -> None:
        if earnings_events.empty:
            return

        price_min = data["Low"].min() if "Low" in data else data["Close"].min()
        price_max = data["High"].max() if "High" in data else data["Close"].max()
        price_span = price_max - price_min
        marker_y = price_min + (price_span * 0.06 if price_span else 0)

        for _, event in earnings_events.iterrows():
            event_date = event["date"]
            label = event["label"]
            ax.axvline(event_date, color="#64748b", linestyle=":", linewidth=0.8, alpha=0.55, zorder=1)
            ax.text(
                event_date,
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

    def plot_candlesticks(self, ax: Any, data: pd.DataFrame) -> None:
        bar_width = self.get_bar_width(data.index) * 0.72
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

        ax.vlines(data.index, data["Low"], data["High"], color=colors.tolist(), linewidth=0.9, alpha=0.9, label="_nolegend_")
        ax.bar(
            data.index,
            body_height,
            bottom=body_bottom,
            width=bar_width,
            color=colors.tolist(),
            edgecolor=colors.tolist(),
            linewidth=0.7,
            alpha=0.86,
            label="_nolegend_"
        )

    def add_signal_summary_box(self, ax: Any, summary: dict[str, Any]) -> None:
        ax.set_axis_off()
        current_price = summary.get("current_price")
        current_rvol = summary.get("current_rvol")
        atr14 = summary.get("atr14")
        price_text = f"{current_price:.2f}" if current_price is not None and not pd.isna(current_price) else "n/a"
        rvol_text = f"{current_rvol:.2f}x" if current_rvol is not None and not pd.isna(current_rvol) else "n/a"
        atr_text = f"{atr14:.2f}" if atr14 is not None and not pd.isna(atr14) else "n/a"

        def status_color(value: str) -> str:
            normalized = str(value).lower()
            if normalized in {"above", "rising", "bullish"}:
                return "#16a34a"
            if normalized in {"below", "falling", "bearish"}:
                return "#dc2626"
            if normalized in {"neutral", "n/a"}:
                return "#64748b"
            return "#0ea5e9"

        def rvol_color(value: float | None) -> str:
            if value is None or pd.isna(value):
                return "#64748b"
            if value >= 2:
                return "#f97316"
            if value >= 1:
                return "#16a34a"
            return "#0ea5e9"

        rows = [
            ("Price", price_text, "#111827"),
            ("vs SMA 50", summary.get("price_vs_sma50", "n/a"), status_color(summary.get("price_vs_sma50", "n/a"))),
            ("vs SMA 200", summary.get("price_vs_sma200", "n/a"), status_color(summary.get("price_vs_sma200", "n/a"))),
            ("vs EMA 20", summary.get("price_vs_ema20", "n/a"), status_color(summary.get("price_vs_ema20", "n/a"))),
            ("", "", "#111827"),
            ("Volume Trend", summary.get("volume_trend", "Neutral"), status_color(summary.get("volume_trend", "Neutral"))),
            ("RVOL", rvol_text, rvol_color(current_rvol)),
            ("ATR 14", atr_text, "#111827"),
            ("", "", "#111827"),
            ("Trend", summary.get("overall_trend", "Neutral").upper(), status_color(summary.get("overall_trend", "Neutral")))
        ]

        card_left = 0.04
        card_bottom = 0.50
        card_width = 0.92
        card_height = 0.46
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
            card_top - 0.035,
            "Signal Summary",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.3,
            fontweight="bold",
            color="#111827",
            zorder=7
        )

        row_y = card_top - 0.09
        row_step = 0.045
        for label, value, color in rows:
            if not label:
                row_y -= row_step * 0.55
                continue

            ax.text(
                card_left + 0.018,
                row_y,
                label,
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=8,
                color="#111827",
                zorder=7
            )
            ax.text(
                card_right - 0.018,
                row_y,
                str(value).upper() if label.startswith("vs ") or label in {"Volume Trend", "Trend"} else str(value),
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=8,
                fontweight="bold" if label in {"Volume Trend", "Trend"} or label.startswith("vs ") else "normal",
                color=color,
                zorder=7
            )
            row_y -= row_step

    def plot_volume_panel(
        self,
        volume_ax: Any,
        data: pd.DataFrame,
        price_ax: Any,
        show_volume_ema50: bool = True,
        show_spike_shading: bool = False
    ) -> Any:
        bar_width = self.get_bar_width(data.index)

        rising_volume = data["Close"] >= data["Close"].shift()
        rising_volume = rising_volume.fillna(True)
        bar_colors = rising_volume.map({True: "#16a34a", False: "#dc2626"})

        volume_ax.bar(
            data.index,
            data["Volume"],
            label="Volume",
            width=bar_width,
            color=bar_colors.tolist(),
            alpha=0.55,
            edgecolor="none"
        )
        volume_ax.plot(
            data.index,
            data["VOLUME_AVG30"],
            label="30-Day Avg Volume",
            linewidth=2.2,
            color="#2563eb"
        )
        if show_volume_ema50:
            volume_ax.plot(
                data.index,
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
            data.index,
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
            rvol_ax.scatter(
                event_data.index,
                event_data["RVOL"],
                label="RVOL > 2",
                color="#f97316",
                edgecolors="white",
                linewidths=0.6,
                s=34,
                zorder=5
            )

            if show_spike_shading:
                highlight_half_width = pd.Timedelta(days=bar_width / 2)
                for event_time in event_data.index:
                    volume_ax.axvspan(
                        event_time - highlight_half_width,
                        event_time + highlight_half_width,
                        color="#f97316",
                        alpha=0.08,
                        linewidth=0
                    )

        spike_times = self.get_spike_times(data)
        self.draw_spike_lines(volume_ax, spike_times)

        latest_volume = self.latest_valid_value(data["Volume"])
        latest_avg_volume = self.latest_valid_value(data["VOLUME_AVG30"])
        latest_rvol = self.latest_valid_value(data["RVOL"])
        volume_trend = self.calculate_volume_trend(data)

        rvol_text = f"{latest_rvol:.2f}x" if latest_rvol is not None else "n/a"
        volume_title = (
            f"Volume | Current {self.format_compact_number(latest_volume)}"
            f" | Avg30 {self.format_compact_number(latest_avg_volume)}"
            f" | RVOL {rvol_text}"
            f" | Trend {volume_trend}"
        )
        volume_ax.set_title(volume_title, fontsize=10, loc="left")

        volume_values = data["Volume"].dropna()
        if not volume_values.empty:
            max_volume_time = volume_values.idxmax()
            max_volume = volume_values.loc[max_volume_time]
            self.annotate_point(
                volume_ax,
                max_volume_time,
                max_volume,
                f"Max Vol {self.format_compact_number(max_volume)}",
                "#2563eb"
            )

        rvol_values = data["RVOL"].dropna()
        if not rvol_values.empty:
            max_rvol_time = rvol_values.idxmax()
            max_rvol = rvol_values.loc[max_rvol_time]
            self.annotate_point(
                rvol_ax,
                max_rvol_time,
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

        return volume_ax

    @staticmethod
    def add_indicators(data):
        data["EMA9"] = data["Close"].ewm(span=9, adjust=False).mean()
        data["EMA12"] = data["Close"].ewm(span=12, adjust=False).mean()
        data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
        data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()
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

        ema12 = data["Close"].ewm(span=12, adjust=False).mean()
        ema26 = data["Close"].ewm(span=26, adjust=False).mean()
        data["MACD"] = ema12 - ema26
        data["MACD_SIGNAL"] = data["MACD"].ewm(span=9, adjust=False).mean()

        return data

    def update_chart(self):
        try:
            ticker = self.get_ticker()
            data, visible_start = self.download_data()
            data = self.add_indicators(data)
            if visible_start is not None:
                visible_start = self.align_timestamp_to_index(visible_start, data.index)
                data = data.loc[data.index >= visible_start]
            if data.empty:
                raise ValueError("No data remains after applying the selected display period.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.figure.clear()

        extra_panels = (
            int(self.show_rsi.get())
            + int(self.show_macd.get())
            + int(self.show_volume.get())
            + int(self.show_atr.get())
        )
        total_rows = 1 + extra_panels

        chart_grid = self.figure.add_gridspec(
            total_rows,
            2,
            width_ratios=[5.4, 1.2],
            wspace=0.08,
            hspace=0.28
        )
        price_ax = self.figure.add_subplot(chart_grid[0, 0])
        summary_ax = self.figure.add_subplot(chart_grid[:, 1])
        signal_summary = self.calculate_signal_summary(data)
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
            self.get_selected_indicators(),
            spike_times,
            earnings_events
        )
        self.add_signal_summary_box(summary_ax, signal_summary)

        row = 1

        if self.show_rsi.get():
            rsi_ax = self.figure.add_subplot(chart_grid[row, 0], sharex=price_ax)
            rsi_ax.plot(data.index, data["RSI"], label="RSI 14")
            rsi_ax.axhline(70, linestyle="--", linewidth=0.8)
            rsi_ax.axhline(30, linestyle="--", linewidth=0.8)
            rsi_ax.set_ylabel("RSI")
            rsi_ax.grid(True, alpha=0.3)
            rsi_ax.legend(loc="upper left")
            row += 1

        if self.show_macd.get():
            macd_ax = self.figure.add_subplot(chart_grid[row, 0], sharex=price_ax)
            macd_ax.plot(data.index, data["MACD"], label="MACD")
            macd_ax.plot(data.index, data["MACD_SIGNAL"], label="Signal")
            macd_ax.axhline(0, linewidth=0.8)
            macd_ax.set_ylabel("MACD")
            macd_ax.grid(True, alpha=0.3)
            macd_ax.legend(loc="upper left")
            row += 1

        if self.show_volume.get():
            volume_ax = self.figure.add_subplot(chart_grid[row, 0], sharex=price_ax)
            self.plot_volume_panel(
                volume_ax,
                data,
                price_ax,
                show_volume_ema50=self.show_volume_ema50.get(),
                show_spike_shading=False
            )
            row += 1

        if self.show_atr.get():
            atr_ax = self.figure.add_subplot(chart_grid[row, 0], sharex=price_ax)
            atr_ax.plot(data.index, data["ATR14"], label="ATR 14")
            atr_ax.set_ylabel("ATR")
            atr_ax.grid(True, alpha=0.3)
            atr_ax.legend(loc="upper left")

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
