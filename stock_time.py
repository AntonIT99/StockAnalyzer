from datetime import datetime
from typing import Any

import pandas as pd


def get_host_timezone():
    return datetime.now().astimezone().tzinfo


def host_now() -> pd.Timestamp:
    return pd.Timestamp.now(tz=get_host_timezone()).tz_localize(None)


def host_today() -> pd.Timestamp:
    return host_now().normalize()


def to_host_naive_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        return timestamp.tz_convert(get_host_timezone()).tz_localize(None)
    return timestamp


def normalize_index_to_host_timezone(data: pd.DataFrame, preserve_dates: bool = False) -> pd.DataFrame:
    if data is None or data.empty or not isinstance(data.index, pd.DatetimeIndex):
        return data

    normalized = data.copy()
    if normalized.index.tz is not None:
        normalized.index = normalized.index.tz_convert(get_host_timezone()).tz_localize(None)

    if preserve_dates:
        normalized.index = normalized.index.normalize()

    return normalized
