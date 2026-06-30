from pathlib import Path
import pandas as pd

MAX_MOVING_AVERAGE_WINDOW = 200
BULLISH_STRUCTURE_SCORE_MAX = 14
CONFIRMATION_SCORE_MAX = 3
EXTENDED_BULLISH_SCORE_MAX = BULLISH_STRUCTURE_SCORE_MAX + CONFIRMATION_SCORE_MAX
ATR_PCT_HEALTHY_MIN = 0.01
ATR_PCT_HEALTHY_MAX = 0.06
DAILY_SIGNAL_PERIOD = "2y"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".stock_cache"
SETTINGS_PATH = PROJECT_ROOT / ".stock_settings.json"
CUSTOM_PERIOD = "Custom"
INTRADAY_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "1h"}
COMPRESSED_AXIS_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d"}
PERIOD_OPTIONS = ["1h", "1d", "1wk", "2wk", "1mo", "3mo", "6mo", "1y", "2y", "3y", "4y", "5y", "10y", CUSTOM_PERIOD, "max"]
INTERVAL_OPTIONS = ["1m", "2m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo", "3mo", "6mo", "1y"]
PERIOD_DURATIONS = {
    "1h": pd.Timedelta(hours=1),
    "1d": pd.Timedelta(days=1),
    "1wk": pd.Timedelta(weeks=1),
    "2wk": pd.Timedelta(weeks=2),
    "1mo": pd.Timedelta(days=30),
    "3mo": pd.Timedelta(days=90),
    "6mo": pd.Timedelta(days=180),
    "1y": pd.Timedelta(days=365),
    "2y": pd.Timedelta(days=365 * 2),
    "3y": pd.Timedelta(days=365 * 3),
    "4y": pd.Timedelta(days=365 * 4),
    "5y": pd.Timedelta(days=365 * 5),
    "10y": pd.Timedelta(days=365 * 10),
    "max": None
}
INTERVAL_DURATIONS = {
    "1m": pd.Timedelta(minutes=1),
    "2m": pd.Timedelta(minutes=2),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "1d": pd.Timedelta(days=1),
    "1wk": pd.Timedelta(weeks=1),
    "1mo": pd.Timedelta(days=30),
    "3mo": pd.Timedelta(days=90),
    "6mo": pd.Timedelta(days=180),
    "1y": pd.Timedelta(days=365)
}
INTERVAL_MAX_LOOKBACKS = {
    "1m": pd.Timedelta(days=8),
    "2m": pd.Timedelta(days=60),
    "5m": pd.Timedelta(days=60),
    "15m": pd.Timedelta(days=60),
    "30m": pd.Timedelta(days=60),
    "1h": pd.Timedelta(days=730),
    "1d": None,
    "1wk": None,
    "1mo": None,
    "3mo": None,
    "6mo": None,
    "1y": None
}
DOWNLOAD_INTERVALS = {
    "1m": "1m",
    "2m": "2m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "1d": "1d",
    "1wk": "1wk",
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "1d",
    "1y": "1d"
}
RESAMPLE_RULES = {
    "6mo": "6ME",
    "1y": "YE"
}
CACHE_TTLS = {
    "1m": pd.Timedelta(minutes=2),
    "2m": pd.Timedelta(minutes=5),
    "5m": pd.Timedelta(minutes=10),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(minutes=15),
    "1d": pd.Timedelta(hours=6),
    "1wk": pd.Timedelta(days=1),
    "1mo": pd.Timedelta(days=1),
    "3mo": pd.Timedelta(days=1),
    "6mo": pd.Timedelta(days=1),
    "1y": pd.Timedelta(days=1)
}
INDICATOR_SETTINGS = [
    "show_ema9",
    "show_ema12",
    "show_ema20",
    "show_ema50",
    "show_ema100",
    "show_ema200",
    "show_sma20",
    "show_sma50",
    "show_sma100",
    "show_sma200",
    "show_bollinger",
    "show_rsi",
    "show_macd",
    "show_volume",
    "show_volume_sma20",
    "show_volume_ema50",
    "show_atr",
    "show_earnings",
    "show_fundamentals",
    "show_debug_fundamentals"
]
