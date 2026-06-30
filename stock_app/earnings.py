"""Earnings event fetching and filtering."""

import yfinance as yf
import pandas as pd

class EarningsMixin:
    @classmethod
    def get_earnings_events(cls, ticker: str) -> pd.DataFrame:
        ticker_data = None
        try:
            ticker_data = yf.Ticker(ticker)
            earnings_dates = ticker_data.earnings_dates
        except Exception as exc:
            print(f"Warning: failed to fetch earnings dates for {ticker}: {exc}. Install missing parser dependencies with: py -m pip install -r requirements.txt")
            earnings_dates = None
        events = []
        if isinstance(earnings_dates, pd.DataFrame) and not earnings_dates.empty:
            for event_time, row in earnings_dates.iterrows():
                event_time = pd.Timestamp(event_time)
                surprise = None
                if "Surprise(%)" in row.index and not cls.is_missing_value(row["Surprise(%)"]):
                    surprise = row["Surprise(%)"]
                elif "Surprise %" in row.index and not cls.is_missing_value(row["Surprise %"]):
                    surprise = row["Surprise %"]
                events.append({
                    "date": event_time,
                    "surprise": surprise
                })
        if not events and ticker_data is not None:
            try:
                calendar = ticker_data.calendar
            except Exception as exc:
                print(f"Warning: failed to fetch earnings calendar for {ticker}: {exc}")
                calendar = None
            if calendar is not None:
                if isinstance(calendar, dict):
                    earnings_date = calendar.get("Earnings Date") or calendar.get("EarningsDate")
                elif isinstance(calendar, pd.DataFrame) and "Earnings Date" in calendar.index:
                    earnings_date = calendar.loc["Earnings Date"].dropna()
                elif isinstance(calendar, pd.Series):
                    earnings_date = calendar.get("Earnings Date") or calendar.get("EarningsDate")
                else:
                    earnings_date = None
                if earnings_date is not None:
                    if isinstance(earnings_date, (list, tuple, pd.Series, pd.Index)):
                        earnings_date = earnings_date[0] if len(earnings_date) else None
                    if not cls.is_missing_value(earnings_date):
                        events.append({
                            "date": pd.Timestamp(earnings_date),
                            "surprise": None
                        })
        return pd.DataFrame(events, columns=["date", "surprise"])

    @classmethod
    def filter_visible_earnings(cls, earnings: pd.DataFrame, index: pd.Index) -> pd.DataFrame:
        if earnings.empty or index.empty:
            return pd.DataFrame(columns=["date", "surprise", "label"])
        start = index[0]
        end = index[-1]
        visible_events = []
        for _, event in earnings.iterrows():
            event_date = cls.align_timestamp_to_index(event["date"], index)
            if start <= event_date <= end:
                surprise = event.get("surprise")
                if surprise is None or pd.isna(surprise):
                    label = "E"
                elif surprise > 0:
                    label = "E+"
                elif surprise < 0:
                    label = "E-"
                else:
                    label = "E"
                visible_events.append({
                    "date": event_date,
                    "surprise": surprise,
                    "label": label
                })
        return pd.DataFrame(visible_events, columns=["date", "surprise", "label"])
