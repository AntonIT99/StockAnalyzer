from datetime import datetime, timezone, tzinfo
from typing import Any, cast
import pandas as pd

def get_host_timezone() -> tzinfo:
    return datetime.now().astimezone().tzinfo or timezone.utc

def host_now() -> pd.Timestamp:
    return pd.Timestamp.now(tz=get_host_timezone()).tz_localize(None)

def host_today() -> pd.Timestamp:
    return host_now().normalize()

def to_host_naive_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        return cast(pd.Timestamp, timestamp.tz_convert(get_host_timezone()).tz_localize(None))
    return cast(pd.Timestamp, timestamp)

def normalize_index_to_host_timezone(data: pd.DataFrame | None, preserve_dates: bool = False) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    if data.empty or not isinstance(data.index, pd.DatetimeIndex):
        return data
    normalized = data.copy()
    datetime_index = pd.DatetimeIndex(normalized.index)
    if datetime_index.tz is not None:
        datetime_index = datetime_index.tz_convert(get_host_timezone()).tz_localize(None)
    if preserve_dates:
        datetime_index = datetime_index.normalize()
    normalized.index = datetime_index
    return normalized
