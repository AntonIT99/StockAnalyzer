"""Market data download, cache, and date-window handling."""

import yfinance as yf
import pandas as pd
from .config import CUSTOM_PERIOD, DAILY_SIGNAL_PERIOD, DOWNLOAD_INTERVALS, INTERVAL_MAX_LOOKBACKS, INTRADAY_INTERVALS, MAX_MOVING_AVERAGE_WINDOW, PERIOD_DURATIONS, RESAMPLE_RULES

class MarketDataMixin:
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
                if not type(self).is_missing_value(value):
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
        if data is None or data.empty or "Close" not in data.columns:
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

    @classmethod
    def parse_date_entry(cls, value, label):
        text = str(value).strip()
        if not text:
            raise ValueError(f"Enter a custom {label} in YYYY-MM-DD format.")
        try:
            parsed = pd.Timestamp(text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Enter a valid custom {label} in YYYY-MM-DD format.") from exc
        if pd.isna(parsed):
            raise ValueError(f"Enter a valid custom {label} in YYYY-MM-DD format.")
        if parsed.tzinfo is not None:
            parsed = cls.to_host_naive_timestamp(parsed)
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

    @classmethod
    def align_timestamp_to_index(cls, timestamp, index):
        index_tz = getattr(index, "tz", None)
        aligned_timestamp = pd.Timestamp(timestamp)
        if index_tz is None:
            if aligned_timestamp.tzinfo is not None:
                return cls.to_host_naive_timestamp(aligned_timestamp)
            return aligned_timestamp
        if aligned_timestamp.tzinfo is None:
            return aligned_timestamp.tz_localize(cls.get_host_timezone()).tz_convert(index_tz)
        return aligned_timestamp.tz_convert(index_tz)
