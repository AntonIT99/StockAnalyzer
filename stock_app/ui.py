"""Tk settings and user interface controls."""

import json
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from .config import CUSTOM_PERIOD, INDICATOR_SETTINGS, PERIOD_OPTIONS, SETTINGS_PATH

class SettingsAndUIMixin:
    @staticmethod
    def load_settings():
        if not SETTINGS_PATH.exists():
            return {}
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
        except (OSError, json.JSONDecodeError):
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
        except OSError:
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
