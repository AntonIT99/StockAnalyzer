import pandas as pd


def mark_volume_completion(data: pd.DataFrame, interval: str, now: pd.Timestamp) -> pd.DataFrame:
    """Conservatively finalize calendar bars on the next calendar boundary.

    Without exchange calendars, today's daily volume stays provisional even
    after the close. Intraday bars finalize after their nominal duration.
    """
    result = data.copy()
    if result.empty:
        result["VOLUME_COMPLETE"] = pd.Series(dtype=bool)
        return result
    index = pd.DatetimeIndex(result.index)
    now = pd.Timestamp(now)
    if index.tz is not None:
        now = now.tz_localize(index.tz) if now.tzinfo is None else now.tz_convert(index.tz)
        index = index.tz_localize(None)
        now = now.tz_localize(None)
    elif now.tzinfo is not None:
        now = now.tz_localize(None)
    if "VOLUME_PERIOD_END" in result:
        ends = pd.DatetimeIndex(result["VOLUME_PERIOD_END"]) + pd.Timedelta(days=1)
    elif interval.endswith("m") and interval != "1mo":
        ends = index + pd.Timedelta(minutes=int(interval[:-1]))
    elif interval.endswith("h"):
        ends = index + pd.Timedelta(hours=int(interval[:-1]))
    elif interval == "1wk":
        ends = index.to_period("W-SUN").end_time.normalize() + pd.Timedelta(days=1)
    elif interval in {"1mo", "3mo", "6mo", "1y"}:
        # Aggregated 6mo/1y bars are labelled at their right edge.
        if interval == "6mo":
            ends = pd.DatetimeIndex([
                pd.Timestamp(year=date.year + (date.month > 6), month=1 if date.month > 6 else 7, day=1)
                for date in index
            ])
        else:
            frequency = {"1mo": "M", "3mo": "Q", "1y": "Y"}[interval]
            ends = index.to_period(frequency).end_time.normalize() + pd.Timedelta(days=1)
    else:
        ends = index.normalize() + pd.Timedelta(days=1)
    result["VOLUME_COMPLETE"] = ends <= now
    return result

def flatten_yfinance_columns(data: pd.DataFrame) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()
    flattened = data.copy()
    if isinstance(flattened.columns, pd.MultiIndex):
        flattened.columns = flattened.columns.get_level_values(0)
    return flattened

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
    if rule in {"6ME", "YE"}:
        # Preserve the real period boundary before moving a live bar's label.
        resampled_data["VOLUME_PERIOD_END"] = resampled_data.index
    if not resampled_data.empty and resampled_data.index[-1] > data.index[-1]:
        resampled_data = resampled_data.rename(index={resampled_data.index[-1]: data.index[-1]})
    return resampled_data

def drop_incomplete_price_rows(data: pd.DataFrame) -> pd.DataFrame:
    required_columns = [
        column
        for column in ("Open", "High", "Low", "Close")
        if column in data
    ]
    if not required_columns:
        return data.dropna()
    return data.dropna(subset=required_columns)

def get_bar_width(index):
    if len(index) < 2:
        return 0.8
    deltas = pd.Series(index).diff().dropna()
    if deltas.empty:
        return 0.8
    median_delta = pd.Timedelta(deltas.median())
    median_days = median_delta.total_seconds() / pd.Timedelta(days=1).total_seconds()
    return max(median_days * 0.8, 0.0005)
