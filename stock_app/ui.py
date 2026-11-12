"""Tk settings and user interface controls."""

import json
import sys
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from .config import CUSTOM_PERIOD, INDICATOR_SETTINGS, PERIOD_OPTIONS, SETTINGS_PATH, VIEW_OPTIONS
from .theme import DARK, DARK_TK, LIGHT, figure_background, set_theme

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
            "current_view": self.current_view_var.get(),
            "dark_mode": bool(self.dark_mode_var.get()),
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
            values=["Line", "Candlesticks", "Line + Candlesticks"],
            width=18,
            state="readonly"
        )
        price_style_combobox.pack(side="left", padx=5)
        price_style_combobox.bind("<<ComboboxSelected>>", lambda _event: self.on_display_option_changed())
        ttk.Button(top_controls, text="Update", command=lambda: self.update_chart(refresh_fundamentals=True)).pack(side="left", padx=15)
        ttk.Label(top_controls, text="View:").pack(side="left", padx=(2, 0))
        view_combobox = ttk.Combobox(
            top_controls,
            textvariable=self.current_view_var,
            values=VIEW_OPTIONS,
            width=18,
            state="readonly"
        )
        view_combobox.pack(side="left", padx=5)
        view_combobox.bind("<<ComboboxSelected>>", lambda _event: self.on_view_changed())
        ttk.Checkbutton(top_controls, text="Dark Mode", variable=self.dark_mode_var, command=self.on_theme_changed).pack(side="right", padx=(15, 0))
        self._comboboxes = [period_combobox, self.interval_combobox, price_style_combobox, view_combobox]
        indicator_checkbuttons = [
            ("EMA 9", self.show_ema9),
            ("EMA 12", self.show_ema12),
            ("EMA 20", self.show_ema20),
            ("EMA 50", self.show_ema50),
            ("EMA 100", self.show_ema100),
            ("EMA 200", self.show_ema200),
            ("SMA 20", self.show_sma20),
            ("SMA 50", self.show_sma50),
            ("SMA 100", self.show_sma100),
            ("SMA 200", self.show_sma200),
            ("Bollinger", self.show_bollinger),
            ("RSI", self.show_rsi),
            ("MACD", self.show_macd),
            ("Volume", self.show_volume),
            ("Vol SMA20", self.show_volume_sma20),
            ("Vol EMA50", self.show_volume_ema50),
            ("ATR 14", self.show_atr),
            ("Earnings", self.show_earnings),
            ("Debug Fundamentals", self.show_debug_fundamentals),
        ]
        for text, variable in indicator_checkbuttons:
            ttk.Checkbutton(indicator_controls, text=text, variable=variable, command=self.on_display_option_changed).pack(side="left", padx=8)
        self.figure = Figure(figsize=(11, 7), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_period_changed(self):
        self.toggle_custom_date_controls()
        self.update_interval_options(persist=True)

    def on_display_option_changed(self):
        """Indicators and style only change the drawing, not the loaded data."""
        self.save_settings()
        self.redraw_chart()

    def on_view_changed(self):
        self.save_settings()
        refresh_fundamentals = self.current_view_var.get() == "Fundamentals"
        if self._chart_state is not None:
            self.redraw_chart(refresh_fundamentals=refresh_fundamentals)
        elif self.ticker_var.get().strip():
            self.update_chart(refresh_fundamentals=refresh_fundamentals)

    def on_theme_changed(self):
        self.save_settings()
        self.apply_theme()
        if self._chart_state is not None:
            self.redraw_chart()
        else:
            self.canvas.draw_idle()

    def apply_theme(self):
        """Apply the selected light or dark theme to the controls and the figure."""
        dark = bool(self.dark_mode_var.get())
        set_theme(DARK if dark else LIGHT)
        style = ttk.Style(self.root)
        if not hasattr(self, "_native_theme"):
            self._native_theme = {
                "ttk_theme": style.theme_use(),
                "root_background": self.root.cget("background"),
                "listbox": self._read_combobox_list_colors(),
            }
        if dark:
            colors = DARK_TK
            style.theme_use("clam")
            style.configure(
                ".",
                background=colors["background"],
                foreground=colors["foreground"],
                fieldbackground=colors["field"],
                bordercolor=colors["border"],
                lightcolor=colors["background"],
                darkcolor=colors["background"],
                troughcolor=colors["field"],
                insertcolor=colors["foreground"],
                selectbackground=colors["accent"],
                selectforeground=colors["accent_foreground"],
            )
            style.map(".", foreground=[("disabled", colors["disabled"])])
            style.configure("TButton", background=colors["field"], padding=(10, 3))
            style.map(
                "TButton",
                background=[("pressed", colors["pressed"]), ("active", colors["hover"])],
                bordercolor=[("focus", colors["accent"])],
            )
            style.configure("TEntry", fieldbackground=colors["field"], padding=2)
            style.map("TEntry", bordercolor=[("focus", colors["accent"])])
            style.configure(
                "TCombobox",
                background=colors["field"],
                arrowcolor=colors["foreground"],
                padding=2,
            )
            style.map(
                "TCombobox",
                fieldbackground=[("readonly", colors["field"])],
                foreground=[("readonly", colors["foreground"])],
                selectbackground=[("readonly", colors["field"])],
                selectforeground=[("readonly", colors["foreground"])],
                background=[("active", colors["hover"])],
                bordercolor=[("focus", colors["accent"])],
            )
            style.configure(
                "TCheckbutton",
                indicatorbackground=colors["field"],
                indicatorforeground=colors["accent_foreground"],
                upperbordercolor=colors["border"],
                lowerbordercolor=colors["border"],
            )
            style.map(
                "TCheckbutton",
                background=[("active", colors["background"])],
                indicatorbackground=[("selected", colors["accent"]), ("active", colors["hover"])],
            )
            root_background = colors["background"]
            listbox_colors = {
                "background": colors["field"],
                "foreground": colors["foreground"],
                "selectbackground": colors["accent"],
                "selectforeground": colors["accent_foreground"],
            }
        else:
            style.theme_use(self._native_theme["ttk_theme"])
            root_background = self._native_theme["root_background"]
            listbox_colors = self._native_theme["listbox"]
        self.root.configure(background=root_background)
        self._apply_combobox_list_colors(listbox_colors)
        self.figure.set_facecolor(figure_background())
        self.canvas.get_tk_widget().configure(background=figure_background(), highlightthickness=0)
        self._apply_title_bar_theme(dark)

    def _combobox_listbox(self, combobox):
        """Return the Tk path of a combobox's drop-down listbox."""
        popdown = self.root.tk.call("ttk::combobox::PopdownWindow", combobox)
        return f"{popdown}.f.l"

    def _read_combobox_list_colors(self):
        options = ("background", "foreground", "selectbackground", "selectforeground")
        try:
            listbox = self._combobox_listbox(self._comboboxes[0])
            return {option: str(self.root.tk.call(listbox, "cget", f"-{option}")) for option in options}
        except (tk.TclError, IndexError):
            return {}

    def _apply_combobox_list_colors(self, colors):
        for combobox in self._comboboxes:
            try:
                listbox = self._combobox_listbox(combobox)
                for option, value in colors.items():
                    self.root.tk.call(listbox, "configure", f"-{option}", value)
            except tk.TclError:
                continue

    def _apply_title_bar_theme(self, dark):
        """Ask Windows to draw the window's title bar dark or light."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.root.update_idletasks()
            window_handle = ctypes.windll.user32.GetParent(self.root.winfo_id())
            use_dark = ctypes.c_int(1 if dark else 0)
            # DWMWA_USE_IMMERSIVE_DARK_MODE
            ctypes.windll.dwmapi.DwmSetWindowAttribute(window_handle, 20, ctypes.byref(use_dark), ctypes.sizeof(use_dark))
        except (AttributeError, OSError, tk.TclError):
            pass

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
