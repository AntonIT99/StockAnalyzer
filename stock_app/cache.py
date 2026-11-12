import hashlib
import json
import pickle
import pandas as pd
from .config import CACHE_DIR, CACHE_TTLS
from .time_utils import host_now, to_host_naive_timestamp

def build_cache_key(ticker, period, interval, download_interval):
    cache_parts = {
        "version": 5,
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "download_interval": download_interval,
        "auto_adjust": True
    }
    cache_text = json.dumps(cache_parts, sort_keys=True)
    return hashlib.sha256(cache_text.encode("utf-8")).hexdigest()

def get_cache_path(cache_key):
    return CACHE_DIR / f"{cache_key}.pkl"

def load_cached_data(cache_key, interval):
    cache_path = get_cache_path(cache_key)
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("rb") as cache_file:
            payload = pickle.load(cache_file)
        fetched_at = pd.Timestamp(payload["fetched_at"])
        data = payload["data"]
    except (EOFError, OSError, KeyError, TypeError, ValueError, pickle.PickleError):
        return None
    cache_ttl = CACHE_TTLS.get(interval, pd.Timedelta(hours=6))
    if host_now() - to_host_naive_timestamp(fetched_at) > cache_ttl:
        return None
    return data.copy()

def prune_expired_cache(now=None):
    """Delete cache files that are older than every TTL and can never be served again."""
    max_ttl = max(CACHE_TTLS.values())
    now = host_now() if now is None else pd.Timestamp(now)
    removed = 0
    try:
        cache_files = list(CACHE_DIR.glob("*.pkl"))
    except OSError:
        return removed
    for cache_path in cache_files:
        try:
            modified_at = pd.Timestamp(cache_path.stat().st_mtime, unit="s", tz="UTC")
            if now - to_host_naive_timestamp(modified_at) > max_ttl:
                cache_path.unlink()
                removed += 1
        except OSError:
            continue
    return removed

def save_cached_data(cache_key, data):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": host_now(),
            "data": data.copy()
        }
        with get_cache_path(cache_key).open("wb") as cache_file:
            pickle.dump(payload, cache_file)
    except (OSError, TypeError, ValueError, pickle.PickleError):
        pass
