from pathlib import Path
import pandas as pd

MAX_MOVING_AVERAGE_WINDOW = 200
TREND_STRUCTURE_SCORE_MAX = 15
MOMENTUM_SCORE_MAX = 6
SETUP_QUALITY_SCORE_MAX = 5
CONFIRMATION_SCORE_MAX = 5
BULLISH_STRUCTURE_SCORE_MAX = TREND_STRUCTURE_SCORE_MAX + MOMENTUM_SCORE_MAX + SETUP_QUALITY_SCORE_MAX
EXTENDED_BULLISH_SCORE_MAX = BULLISH_STRUCTURE_SCORE_MAX + CONFIRMATION_SCORE_MAX
TECHNICAL_SCORE_WEIGHTS = {
    "trend": 0.40,
    "momentum": 0.25,
    "setup": 0.15,
    "confirmation": 0.20,
}
if not abs(sum(TECHNICAL_SCORE_WEIGHTS.values()) - 1.0) < 1e-9:
    raise ValueError("TECHNICAL_SCORE_WEIGHTS must add up to 1.0")
TECHNICAL_ASSESSMENT_WEAK_PERCENTAGES = {
    "trend": 60.0,
    "momentum": 50.0,
    "setup": 50.0,
    "confirmation": 50.0,
}


class PullbackRiskConfig:
    LOOKBACK_BARS = 20
    ATR_MODERATE = 1.5
    ATR_EXTENDED = 2.0
    ATR_EXTREME = 3.0
    RSI_ELEVATED = 70
    RSI_EXHAUSTED = 75
    RSI_EXTREME = 80
    RSI_DIVERGENCE_DROP = 5
    LOW_RVOL = 0.8
    MACD_FALLING_BARS = 3

    CATEGORY_MAX = {
        "price_extension": 25,
        "momentum_exhaustion": 30,
        "participation_risk": 20,
        "reversal_signals": 25,
    }
    POINTS = {
        "extension_above_2_atr": 15,
        "extension_above_3_atr": 25,
        "rsi_above_75": 10,
        "rsi_above_80": 15,
        "rsi_falling_above_70": 5,
        "macd_histogram_falling_3": 10,
        "bearish_divergence": 15,
        "low_volume_new_high": 15,
        "rising_price_low_volume": 5,
        "bollinger_breakout_failure": 15,
        "spike_rejection_candle": 10,
        "failed_previous_high": 15,
    }
ATR_PCT_HEALTHY_MIN = 0.01
ATR_PCT_HEALTHY_MAX = 0.06
DAILY_SIGNAL_PERIOD = "2y"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".stock_cache"
SETTINGS_PATH = PROJECT_ROOT / ".stock_settings.json"
CUSTOM_PERIOD = "Custom"
AUTO_SELECT_PERIOD = "Auto-Select"
VIEW_OPTIONS = ["Signal Summary", "Extended Summary", "Fundamentals"]
AUTO_SELECT_PERIODS_BY_INTERVAL = {
    "1m": "4h",
    "2m": "1d",
    "5m": "2d",
    "15m": "2wk",
    "30m": "1mo",
    "1h": "2mo",
    "1d": "1y",
    "1wk": "4y",
    "1mo": "max",
    "3mo": "max",
    "6mo": "max",
}
INTRADAY_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "1h"}
COMPRESSED_AXIS_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d"}
PERIOD_OPTIONS = [AUTO_SELECT_PERIOD, "1h", "2h", "4h", "1d", "2d", "1wk", "2wk", "1mo", "3mo", "6mo", "1y", "2y", "3y", "4y", "5y", "10y", CUSTOM_PERIOD, "max"]
INTERVAL_OPTIONS = ["1m", "2m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo", "3mo", "6mo", "1y"]
PERIOD_DURATIONS = {
    "1h": pd.Timedelta(hours=1),
    "2h": pd.Timedelta(hours=2),
    "4h": pd.Timedelta(hours=4),
    "1d": pd.Timedelta(days=1),
    "2d": pd.Timedelta(days=2),
    "1wk": pd.Timedelta(weeks=1),
    "2wk": pd.Timedelta(weeks=2),
    "1mo": pd.Timedelta(days=30),
    "2mo": pd.Timedelta(days=60),
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
    "show_debug_fundamentals"
]
