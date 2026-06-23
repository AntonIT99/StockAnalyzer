import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

import yfinance as yf
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


MAX_MOVING_AVERAGE_WINDOW = 200
CACHE_DIR = Path(__file__).with_name(".stock_cache")
PERIOD_OPTIONS = ["1h", "1d", "5d", "15d", "1mo", "3mo", "6mo", "1y", "2y", "3y", "4y", "5y", "10y", "max"]
INTERVAL_OPTIONS = ["1m", "2m", "1h", "1d", "5d", "1wk", "1mo", "3mo", "6mo", "1y"]
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
    "1h": pd.Timedelta(minutes=15),
    "1d": pd.Timedelta(hours=6),
    "5d": pd.Timedelta(hours=12),
    "1wk": pd.Timedelta(days=1),
    "1mo": pd.Timedelta(days=1),
    "3mo": pd.Timedelta(days=1),
    "6mo": pd.Timedelta(days=1),
    "1y": pd.Timedelta(days=1)
}


class StockApp:
    def __init__(self, root, initial_ticker=""):
        self.root = root
        self.root.title("Stock Technical Chart")
        self.root.geometry("1600x900")

        self.ticker_var = tk.StringVar(value=initial_ticker)
        self.period_var = tk.StringVar(value="6mo")
        self.interval_var = tk.StringVar(value="1d")

        self.show_ema9 = tk.BooleanVar(value=False)
        self.show_ema12 = tk.BooleanVar(value=False)
        self.show_ema20 = tk.BooleanVar(value=False)
        self.show_ema50 = tk.BooleanVar(value=False)
        self.show_ema200 = tk.BooleanVar(value=False)
        self.show_sma20 = tk.BooleanVar(value=False)
        self.show_sma50 = tk.BooleanVar(value=False)
        self.show_sma100 = tk.BooleanVar(value=False)
        self.show_sma200 = tk.BooleanVar(value=False)
        self.show_bollinger = tk.BooleanVar(value=False)
        self.show_rsi = tk.BooleanVar(value=False)
        self.show_macd = tk.BooleanVar(value=False)

        self._build_ui()
        if initial_ticker:
            self.update_chart()

    def _build_ui(self):
        controls = ttk.Frame(self.root)
        controls.pack(side="top", fill="x", padx=10, pady=8)

        ttk.Label(controls, text="Ticker:").pack(side="left")
        ticker_entry = ttk.Entry(controls, textvariable=self.ticker_var, width=10)
        ticker_entry.pack(side="left", padx=5)
        ticker_entry.bind("<Return>", lambda _event: self.update_chart())

        ttk.Label(controls, text="Period:").pack(side="left")
        period_combobox = ttk.Combobox(
            controls,
            textvariable=self.period_var,
            values=PERIOD_OPTIONS,
            width=8,
            state="readonly"
        )
        period_combobox.pack(side="left", padx=5)
        period_combobox.bind("<<ComboboxSelected>>", lambda _event: self.update_interval_options())

        ttk.Label(controls, text="Interval:").pack(side="left", padx=(15, 0))
        self.interval_combobox = ttk.Combobox(
            controls,
            textvariable=self.interval_var,
            width=8,
            state="readonly"
        )
        self.interval_combobox.pack(side="left", padx=5)
        self.update_interval_options()

        ttk.Checkbutton(controls, text="EMA 9", variable=self.show_ema9).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="EMA 12", variable=self.show_ema12).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="EMA 20", variable=self.show_ema20).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="EMA 50", variable=self.show_ema50).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="EMA 200", variable=self.show_ema200).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="SMA 20", variable=self.show_sma20).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="SMA 50", variable=self.show_sma50).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="SMA 100", variable=self.show_sma100).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="SMA 200", variable=self.show_sma200).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="Bollinger", variable=self.show_bollinger).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="RSI", variable=self.show_rsi).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="MACD", variable=self.show_macd).pack(side="left", padx=8)

        ttk.Button(controls, text="Update", command=self.update_chart).pack(side="left", padx=15)

        self.figure = Figure(figsize=(11, 7), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_interval_options(self):
        allowed_intervals = self.get_allowed_intervals(self.period_var.get())
        self.interval_combobox["values"] = allowed_intervals

        if self.interval_var.get() not in allowed_intervals:
            self.interval_var.set(allowed_intervals[-1])

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
            download_kwargs["start"] = self.get_download_start(visible_start, interval)
            download_kwargs["end"] = pd.Timestamp.now().normalize() + pd.Timedelta(days=1)

        cache_key = self.build_cache_key(ticker, self.period_var.get(), interval, download_interval)
        data = self.load_cached_data(cache_key, interval)

        if data is None:
            data = yf.download(
                ticker,
                **download_kwargs
            )

            if data is None or data.empty:
                raise ValueError("No data received. Check the ticker, period, or interval.")

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            self.save_cached_data(cache_key, data)

        if data is None or data.empty:
            raise ValueError("No data received. Check the ticker, period, or interval.")

        if interval in RESAMPLE_RULES:
            data = self.resample_ohlcv(data, RESAMPLE_RULES[interval])

        return data.dropna(), visible_start

    @staticmethod
    def build_cache_key(ticker, period, interval, download_interval):
        cache_parts = {
            "version": 1,
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

    def validate_period_interval(self, visible_start, interval):
        if interval not in self.get_allowed_intervals(self.period_var.get()):
            raise ValueError(f"Use an interval less than or equal to the selected period: {self.period_var.get()}.")

        max_lookback = INTERVAL_MAX_LOOKBACKS[interval]
        if max_lookback is None:
            if visible_start is not None and visible_start > pd.Timestamp.now().normalize():
                raise ValueError("Use the 1m, 2m, or 1h interval with the 1h period.")
            return

        if visible_start is None:
            raise ValueError("Yahoo Finance intraday data has a limited lookback window. Use a shorter period with 1m/2m/1h intervals.")

        oldest_allowed_start = pd.Timestamp.now() - max_lookback
        if visible_start < oldest_allowed_start:
            raise ValueError(f"Yahoo Finance {interval} data is limited to roughly the last {max_lookback.days} days. Select a shorter period.")

    @staticmethod
    def get_download_start(visible_start, interval):
        if interval in {"1m", "2m", "1h"}:
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
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.figure.clear()

        extra_panels = int(self.show_rsi.get()) + int(self.show_macd.get())
        total_rows = 1 + extra_panels

        price_ax = self.figure.add_subplot(total_rows, 1, 1)
        price_ax.plot(data.index, data["Close"], label="Close", linewidth=1.6)
        price_ax.set_title(f"{ticker} Technical Chart")
        price_ax.set_ylabel("Price USD")
        price_ax.grid(True, alpha=0.3)

        if self.show_ema9.get():
            price_ax.plot(data.index, data["EMA9"], label="EMA 9", linewidth=1)

        if self.show_ema12.get():
            price_ax.plot(data.index, data["EMA12"], label="EMA 12", linewidth=1)

        if self.show_ema20.get():
            price_ax.plot(data.index, data["EMA20"], label="EMA 20", linewidth=1)

        if self.show_ema50.get():
            price_ax.plot(data.index, data["EMA50"], label="EMA 50", linewidth=1)

        if self.show_ema200.get():
            price_ax.plot(data.index, data["EMA200"], label="EMA 200", linewidth=1)

        if self.show_sma20.get():
            price_ax.plot(data.index, data["SMA20"], label="SMA 20", linewidth=1)

        if self.show_sma50.get():
            price_ax.plot(data.index, data["SMA50"], label="SMA 50", linewidth=1)

        if self.show_sma100.get():
            price_ax.plot(data.index, data["SMA100"], label="SMA 100", linewidth=1)

        if self.show_sma200.get():
            price_ax.plot(data.index, data["SMA200"], label="SMA 200", linewidth=1)

        if self.show_bollinger.get():
            price_ax.plot(data.index, data["BB_UPPER"], label="Bollinger Upper", linewidth=0.9)
            price_ax.plot(data.index, data["BB_LOWER"], label="Bollinger Lower", linewidth=0.9)

        price_ax.legend(loc="upper left")

        row = 2

        if self.show_rsi.get():
            rsi_ax = self.figure.add_subplot(total_rows, 1, row, sharex=price_ax)
            rsi_ax.plot(data.index, data["RSI"], label="RSI 14")
            rsi_ax.axhline(70, linestyle="--", linewidth=0.8)
            rsi_ax.axhline(30, linestyle="--", linewidth=0.8)
            rsi_ax.set_ylabel("RSI")
            rsi_ax.grid(True, alpha=0.3)
            rsi_ax.legend(loc="upper left")
            row += 1

        if self.show_macd.get():
            macd_ax = self.figure.add_subplot(total_rows, 1, row, sharex=price_ax)
            macd_ax.plot(data.index, data["MACD"], label="MACD")
            macd_ax.plot(data.index, data["MACD_SIGNAL"], label="Signal")
            macd_ax.axhline(0, linewidth=0.8)
            macd_ax.set_ylabel("MACD")
            macd_ax.grid(True, alpha=0.3)
            macd_ax.legend(loc="upper left")

        self.figure.tight_layout()
        self.canvas.draw()


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
