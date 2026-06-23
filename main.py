import tkinter as tk
from tkinter import ttk, messagebox

import yfinance as yf
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


DEFAULT_TICKER = "AAPL"
MAX_MOVING_AVERAGE_WINDOW = 200


class StockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Technical Chart")
        self.root.geometry("1600x900")

        self.ticker_var = tk.StringVar(value=DEFAULT_TICKER)
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
        self.update_chart()

    def _build_ui(self):
        controls = ttk.Frame(self.root)
        controls.pack(side="top", fill="x", padx=10, pady=8)

        ttk.Label(controls, text="Ticker:").pack(side="left")
        ticker_entry = ttk.Entry(controls, textvariable=self.ticker_var, width=10)
        ticker_entry.pack(side="left", padx=5)
        ticker_entry.bind("<Return>", lambda _event: self.update_chart())

        ttk.Label(controls, text="Period:").pack(side="left")
        ttk.Combobox(
            controls,
            textvariable=self.period_var,
            values=["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
            width=8,
            state="readonly"
        ).pack(side="left", padx=5)

        ttk.Label(controls, text="Interval:").pack(side="left", padx=(15, 0))
        ttk.Combobox(
            controls,
            textvariable=self.interval_var,
            values=["1d", "1wk", "1mo"],
            width=8,
            state="readonly"
        ).pack(side="left", padx=5)

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

    def download_data(self):
        ticker = self.get_ticker()
        visible_start = self.get_visible_start()
        interval = self.interval_var.get()

        download_kwargs = {
            "interval": interval,
            "auto_adjust": True,
            "progress": False
        }

        if visible_start is None:
            download_kwargs["period"] = self.period_var.get()
        else:
            download_kwargs["start"] = self.get_download_start(visible_start, interval)
            download_kwargs["end"] = pd.Timestamp.now().normalize() + pd.Timedelta(days=1)

        data = yf.download(
            ticker,
            **download_kwargs
        )

        if data is None or data.empty:
            raise ValueError("No data received. Check the ticker, period, or interval.")

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        return data.dropna(), visible_start

    def get_ticker(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            raise ValueError("Enter a ticker symbol.")

        self.ticker_var.set(ticker)
        return ticker

    def get_visible_start(self):
        period = self.period_var.get()
        end = pd.Timestamp.now().normalize()

        period_offsets = {
            "5d": pd.DateOffset(days=5),
            "1mo": pd.DateOffset(months=1),
            "3mo": pd.DateOffset(months=3),
            "6mo": pd.DateOffset(months=6),
            "1y": pd.DateOffset(years=1),
            "2y": pd.DateOffset(years=2),
            "5y": pd.DateOffset(years=5),
            "10y": pd.DateOffset(years=10)
        }

        offset = period_offsets.get(period)
        if offset is None:
            return None

        return end - offset

    @staticmethod
    def get_download_start(visible_start, interval):
        if interval == "1wk":
            return visible_start - pd.DateOffset(weeks=MAX_MOVING_AVERAGE_WINDOW + 20)

        if interval == "1mo":
            return visible_start - pd.DateOffset(months=MAX_MOVING_AVERAGE_WINDOW + 5)

        return visible_start - pd.DateOffset(days=MAX_MOVING_AVERAGE_WINDOW * 2)

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


if __name__ == "__main__":
    tk_root = tk.Tk()
    app = StockApp(tk_root)
    tk_root.mainloop()
