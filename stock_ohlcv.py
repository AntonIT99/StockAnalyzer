import pandas as pd


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
