"""Chart refresh orchestration."""

from tkinter import messagebox
import pandas as pd

class ChartUpdateMixin:
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
            daily_summary_as_of=visible_end,
            period_start_as_of=visible_start
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
