"""Fundamental data retrieval, normalization, and classification."""

from typing import Any
import yfinance as yf
import pandas as pd

class FundamentalsMixin:
    @staticmethod
    def fetch_fundamentals(ticker: str) -> dict[str, Any]:
        ticker_data = yf.Ticker(ticker)
        raw: dict[str, Any] = {}
        for name, attribute in (
            ("info", "info"),
            ("fast_info", "fast_info"),
            ("income_stmt", "income_stmt"),
            ("quarterly_income_stmt", "quarterly_income_stmt"),
            ("balance_sheet", "balance_sheet"),
            ("quarterly_balance_sheet", "quarterly_balance_sheet"),
            ("cashflow", "cashflow"),
            ("quarterly_cashflow", "quarterly_cashflow")
        ):
            try:
                value = getattr(ticker_data, attribute)
                if name == "fast_info":
                    try:
                        value = dict(value)
                    except (TypeError, ValueError):
                        value = {}
                raw[name] = value
            except Exception as exc:
                print(f"Warning: failed to fetch {name} for {ticker}: {exc}")
                raw[name] = pd.DataFrame() if "stmt" in name or "sheet" in name or "cashflow" in name else {}
        try:
            raw["history_5y"] = ticker_data.history(period="5y", interval="1mo", auto_adjust=True)
        except Exception as exc:
            print(f"Warning: failed to fetch history_5y for {ticker}: {exc}")
            raw["history_5y"] = pd.DataFrame()
        return raw

    def get_fundamentals(self, ticker: str, refresh: bool = False, debug: bool = False) -> dict[str, Any]:
        if refresh or ticker not in self._fundamentals_cache:
            try:
                raw = self.fetch_fundamentals(ticker)
                self._fundamentals_cache[ticker] = self.calculate_fundamental_metrics(raw, debug=debug)
            except Exception as exc:
                print(f"Warning: failed to calculate fundamentals for {ticker}: {exc}")
                self._fundamentals_cache[ticker] = {}
        return self._fundamentals_cache.get(ticker, {})

    @classmethod
    def first_available(cls, mapping: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = mapping.get(key)
            if not cls.is_missing_value(value):
                return value
        return None

    @staticmethod
    def is_missing_value(value: Any) -> bool:
        if value is None:
            return True
        try:
            return bool(pd.isna(value))
        except (TypeError, ValueError):
            return False

    @classmethod
    def statement_value(cls, statement: Any, row_names: list[str], column_offset: int = 0) -> float | None:
        if not isinstance(statement, pd.DataFrame) or statement.empty:
            return None
        for row_name in row_names:
            if row_name not in statement.index or len(statement.columns) <= column_offset:
                continue
            value = statement.loc[row_name].iloc[column_offset]
            if not cls.is_missing_value(value):
                return float(value)
        return None

    @classmethod
    def statement_growth(cls, statement: Any, row_names: list[str], compare_offset: int) -> float | None:
        latest = cls.statement_value(statement, row_names, 0)
        previous = cls.statement_value(statement, row_names, compare_offset)
        if latest is None or previous is None or previous == 0:
            return None
        return (latest - previous) / abs(previous)

    @classmethod
    def statement_growth_details(
        cls,
        statement: Any,
        row_names: list[str],
        compare_offset: int,
        source_statement: str,
        method: str
    ) -> tuple[float | None, dict[str, Any]]:
        if not isinstance(statement, pd.DataFrame) or statement.empty:
            return None, {"method": method, "source": source_statement, "reason": "statement unavailable"}
        for row_name in row_names:
            row = cls.statement_row(statement, row_name)
            if row is None or len(row) <= compare_offset:
                continue
            current = row.iloc[0]
            comparison = row.iloc[compare_offset]
            if cls.is_missing_value(current) or cls.is_missing_value(comparison) or comparison == 0:
                continue
            growth = (float(current) - float(comparison)) / abs(float(comparison))
            details = {
                "method": method,
                "source": source_statement,
                "row": row_name,
                "current_value": float(current),
                "comparison_value": float(comparison),
                "current_dates": [cls.format_statement_date(row.index[0])],
                "comparison_dates": [cls.format_statement_date(row.index[compare_offset])],
                "growth": growth
            }
            return growth, details
        return None, {"method": method, "source": source_statement, "reason": "row unavailable"}

    @staticmethod
    def statement_row(statement: Any, row_name: str) -> pd.Series | None:
        if not isinstance(statement, pd.DataFrame) or statement.empty or row_name not in statement.index:
            return None
        row = statement.loc[row_name]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        row = row.dropna()
        if row.empty:
            return None
        try:
            row.index = pd.to_datetime(row.index)
            row = row.sort_index(ascending=False)
        except (TypeError, ValueError, AttributeError):
            pass
        return row

    @classmethod
    def calculate_eps_growth_yoy(cls, quarterly_income: Any, annual_income: Any, debug: bool = False) -> tuple[float | None, str | None, dict[str, Any]]:
        diluted_eps = cls.statement_row(quarterly_income, "Diluted EPS")
        basic_eps = cls.statement_row(quarterly_income, "Basic EPS")
        net_income = cls.statement_row(quarterly_income, "Net Income")
        annual_diluted_eps = cls.statement_row(annual_income, "Diluted EPS")
        if debug:
            print("EPS Growth YoY debug:")
            print("  source preference:")
            print("    1. quarterly_income_stmt Diluted EPS TTM vs previous TTM")
            print("    2. quarterly_income_stmt latest Diluted EPS quarter vs same quarter previous year")
            print("    3. income_stmt annual Diluted EPS YoY")
            print("  basic EPS used: no")
            print("  net income used: no")
            if basic_eps is not None:
                print(f"  Basic EPS available but ignored: {cls.format_debug_series(basic_eps)}")
            if net_income is not None:
                print(f"  Net Income available but ignored: {cls.format_debug_series(net_income)}")
            if diluted_eps is not None:
                print(f"  Diluted EPS raw quarterly values: {cls.format_debug_series(diluted_eps)}")
            else:
                print("  Diluted EPS unavailable in quarterly_income_stmt")
            if annual_diluted_eps is not None:
                print(f"  Diluted EPS raw annual values: {cls.format_debug_series(annual_diluted_eps)}")
            else:
                print("  Diluted EPS unavailable in income_stmt")
        result = cls.calculate_eps_growth_from_series(
            diluted_eps,
            current_count=4,
            comparison_start=4,
            comparison_count=4,
            method="TTM YoY",
            source_statement="quarterly_income_stmt",
            debug=debug
        )
        if result[0] is not None:
            return result
        result = cls.calculate_eps_growth_from_series(
            diluted_eps,
            current_count=1,
            comparison_start=4,
            comparison_count=1,
            method="Quarter YoY",
            source_statement="quarterly_income_stmt",
            debug=debug
        )
        if result[0] is not None:
            return result
        result = cls.calculate_eps_growth_from_series(
            annual_diluted_eps,
            current_count=1,
            comparison_start=1,
            comparison_count=1,
            method="Annual YoY",
            source_statement="income_stmt",
            debug=debug
        )
        if result[0] is not None:
            return result
        if debug:
            print("  method used: N/A")
            print("  current_eps: N/A")
            print("  comparison_eps: N/A")
            print("  calculated growth: N/A")
        return None, None, {"method": None, "source": None, "reason": "Diluted EPS unavailable"}

    @classmethod
    def calculate_eps_growth_from_series(
        cls,
        eps_values: pd.Series | None,
        current_count: int,
        comparison_start: int,
        comparison_count: int,
        method: str,
        source_statement: str,
        debug: bool = False
    ) -> tuple[float | None, str | None, dict[str, Any]]:
        required_values = comparison_start + comparison_count
        if eps_values is None or len(eps_values) < required_values:
            found_values = 0 if eps_values is None else len(eps_values)
            if debug:
                print(f"  {method} skipped: need {required_values} diluted EPS values, found {found_values}")
            return None, None, {"method": method, "source": source_statement, "reason": f"need {required_values}, found {found_values}"}
        current_periods = eps_values.iloc[:current_count]
        comparison_periods = eps_values.iloc[comparison_start:comparison_start + comparison_count]
        current_eps = float(current_periods.sum())
        comparison_eps = float(comparison_periods.sum())
        current_dates = [cls.format_statement_date(date) for date in current_periods.index]
        comparison_dates = [cls.format_statement_date(date) for date in comparison_periods.index]
        if comparison_eps == 0:
            if debug:
                print(f"  {method} skipped: comparison_eps is zero")
            return None, None, {"method": method, "source": source_statement, "reason": "comparison EPS is zero"}
        growth = (current_eps - comparison_eps) / abs(comparison_eps)
        details = {
            "method": method,
            "source": source_statement,
            "row": "Diluted EPS",
            "current_value": current_eps,
            "comparison_value": comparison_eps,
            "current_dates": current_dates,
            "comparison_dates": comparison_dates,
            "growth": growth
        }
        if debug:
            print(f"  method used: {method}")
            print(f"  current_eps: {current_eps}")
            print(f"  comparison_eps: {comparison_eps}")
            print(f"  current dates: {current_dates}")
            print(f"  comparison dates: {comparison_dates}")
            print(f"  source statement: {source_statement}")
            print("  source row: Diluted EPS")
            print(f"  calculated growth: {growth * 100:.2f}%")
        return growth, method, details

    @staticmethod
    def format_statement_date(value: Any) -> str:
        try:
            return pd.Timestamp(value).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            return str(value)

    @classmethod
    def format_debug_series(cls, series: pd.Series) -> str:
        values = []
        for date, value in series.items():
            try:
                formatted_value = f"{float(value):.4g}"
            except (TypeError, ValueError):
                formatted_value = str(value)
            values.append(f"{cls.format_statement_date(date)}={formatted_value}")
        return ", ".join(values)

    @classmethod
    def calculate_free_cash_flow(cls, cashflow: Any, column_offset: int = 0) -> float | None:
        operating_cash_flow = cls.statement_value(
            cashflow,
            ["Operating Cash Flow", "Total Cash From Operating Activities"],
            column_offset
        )
        capital_expenditure = cls.statement_value(
            cashflow,
            ["Capital Expenditure", "Capital Expenditures", "CapitalExpenditures"],
            column_offset
        )
        if operating_cash_flow is None or capital_expenditure is None:
            return None
        if capital_expenditure < 0:
            return operating_cash_flow + capital_expenditure
        return operating_cash_flow - capital_expenditure

    @classmethod
    def calculate_fcf_growth_yoy(cls, cashflow: Any) -> tuple[float | None, dict[str, Any]]:
        latest = cls.calculate_free_cash_flow(cashflow, 0)
        previous = cls.calculate_free_cash_flow(cashflow, 1)
        if latest is None or previous is None or previous == 0:
            return None, {"method": "Annual YoY", "source": "cashflow", "reason": "insufficient FCF values"}
        growth = (latest - previous) / abs(previous)
        details = {
            "method": "Annual YoY",
            "source": "cashflow",
            "row": "Operating Cash Flow - Capital Expenditures",
            "current_value": latest,
            "comparison_value": previous,
            "growth": growth
        }
        return growth, details

    @classmethod
    def calculate_fcf_trend(cls, cashflow: Any) -> tuple[str, float | None]:
        latest = cls.calculate_free_cash_flow(cashflow, 0)
        previous = cls.calculate_free_cash_flow(cashflow, 1)
        if latest is None or previous is None or previous == 0:
            return "Neutral", None
        relative_gap = abs(latest - previous) / abs(previous)
        if relative_gap < 0.05:
            return "Neutral", (latest - previous) / abs(previous)
        change = (latest - previous) / abs(previous)
        return ("Rising" if latest > previous else "Falling"), change

    @staticmethod
    def format_trend_with_change(direction: str, change: float | None) -> str:
        if change is None:
            return direction
        return f"{direction} ({change * 100:+.1f}%)"

    @classmethod
    def calculate_pe_history(cls, price_history: Any, annual_income: Any) -> dict[str, float | None]:
        result = {"pe_3y_avg": None, "pe_5y_avg": None}
        eps = cls.statement_row(annual_income, "Diluted EPS")
        if eps is None or not isinstance(price_history, pd.DataFrame) or price_history.empty or "Close" not in price_history.columns:
            return result
        pe_values = []
        history = price_history.copy()
        try:
            history = cls.normalize_index_to_host_timezone(history, preserve_dates=True)
        except (TypeError, ValueError, AttributeError):
            return result
        for date, eps_value in eps.items():
            if cls.is_missing_value(eps_value) or float(eps_value) == 0:
                continue
            statement_date = pd.Timestamp(date)
            if statement_date.tzinfo is not None:
                statement_date = cls.to_host_naive_timestamp(statement_date)
            historical_prices = history.loc[history.index <= statement_date]
            if historical_prices.empty:
                continue
            price = historical_prices["Close"].dropna().iloc[-1]
            pe_values.append((statement_date, float(price) / float(eps_value)))
        if not pe_values:
            return result
        pe_values = sorted(pe_values, key=lambda item: item[0], reverse=True)
        three_year_values = [value for _date, value in pe_values[:3]]
        five_year_values = [value for _date, value in pe_values[:5]]
        if len(three_year_values) >= 3:
            result["pe_3y_avg"] = sum(three_year_values) / len(three_year_values)
        if len(five_year_values) >= 5:
            result["pe_5y_avg"] = sum(five_year_values) / len(five_year_values)
        return result

    @staticmethod
    def valuation_history_label(current: float | None, historical_average: float | None) -> tuple[float | None, str | None]:
        if current is None or historical_average is None or historical_average == 0:
            return None, None
        difference = (float(current) - float(historical_average)) / abs(float(historical_average))
        if difference < -0.25:
            label = "below history"
        elif difference > 0.25:
            label = "above history"
        else:
            label = "near history"
        return difference, label

    @classmethod
    def calculate_shareholder_view(cls, metrics: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        revenue_growth = metrics["revenue_growth_yoy"]["value"]
        eps_growth = metrics["eps_growth_yoy"]["value"]
        operating_margin = metrics["operating_margin"]["value"]
        roe = metrics["return_on_equity"]["value"]
        forward_pe = metrics["forward_pe"]["value"]
        peg = metrics["peg_ratio"]["value"]
        debt_equity = metrics["debt_equity"]["value"]
        if any(cls.is_missing_value(value) for value in (revenue_growth, eps_growth, operating_margin, roe)):
            business_health = "Unknown"
        elif revenue_growth < 0 or eps_growth < 0:
            business_health = "Weak"
        elif revenue_growth > 0.05 and eps_growth > 0.05 and operating_margin > 0.10 and roe > 0.10:
            business_health = "Strong"
        elif sum(value > 0 for value in (revenue_growth, eps_growth, operating_margin, roe)) >= 3:
            business_health = "Stable"
        else:
            business_health = "Weak"
        if cls.is_missing_value(forward_pe) or cls.is_missing_value(peg):
            valuation = "Unknown"
        elif forward_pe < 12 and peg < 1.5:
            valuation = "Cheap"
        elif forward_pe < 20 and peg < 2:
            valuation = "Fair"
        elif forward_pe > 25 or peg > 2.5:
            valuation = "Expensive"
        else:
            valuation = "Fair"
        if cls.is_missing_value(debt_equity):
            balance_sheet = "Unknown"
        elif debt_equity < 0.5:
            balance_sheet = "Strong"
        elif debt_equity < 1.5:
            balance_sheet = "Moderate"
        else:
            balance_sheet = "Risky"
        if "Unknown" in {business_health, valuation, balance_sheet}:
            overall = "Unknown"
        elif business_health == "Strong" and valuation in {"Cheap", "Fair"} and balance_sheet in {"Strong", "Moderate"}:
            overall = "Attractive"
        elif business_health == "Weak" or valuation == "Expensive" or balance_sheet == "Risky":
            overall = "Risky"
        else:
            overall = "Watchlist"
        return {
            "business_health": {"label": "Business Health", "value": business_health, "type": "text", "section": "Shareholder View"},
            "valuation_view": {"label": "Valuation", "value": valuation, "type": "text", "section": "Shareholder View"},
            "balance_sheet_view": {"label": "Balance Sheet", "value": balance_sheet, "type": "text", "section": "Shareholder View"},
            "overall_fundamental_view": {"label": "Overall View", "value": overall, "type": "text", "section": "Shareholder View"}
        }

    @classmethod
    def calculate_fundamental_metrics(cls, raw: dict[str, Any], debug: bool = False) -> dict[str, dict[str, Any]]:
        info = raw.get("info") if isinstance(raw.get("info"), dict) else {}
        fast_info = raw.get("fast_info") if isinstance(raw.get("fast_info"), dict) else {}
        income = raw.get("income_stmt")
        quarterly_income = raw.get("quarterly_income_stmt")
        balance_sheet = raw.get("balance_sheet")
        quarterly_balance_sheet = raw.get("quarterly_balance_sheet")
        cashflow = raw.get("cashflow")
        quarterly_cashflow = raw.get("quarterly_cashflow")
        price_history = raw.get("history_5y")
        total_debt = cls.first_available(info, "totalDebt")
        cash = cls.first_available(info, "totalCash")
        total_equity = cls.statement_value(balance_sheet, ["Stockholders Equity", "Total Stockholder Equity"])
        if total_debt is None:
            total_debt = cls.statement_value(balance_sheet, ["Total Debt", "Net Debt"])
        if cash is None:
            cash = cls.statement_value(balance_sheet, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        if total_debt is None:
            total_debt = cls.statement_value(quarterly_balance_sheet, ["Total Debt", "Net Debt"])
        if cash is None:
            cash = cls.statement_value(quarterly_balance_sheet, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        if total_equity is None:
            total_equity = cls.statement_value(quarterly_balance_sheet, ["Stockholders Equity", "Total Stockholder Equity"])
        net_debt = None
        if total_debt is not None and cash is not None:
            net_debt = float(total_debt) - float(cash)
        debt_to_equity = None
        if total_debt is not None and total_equity not in (None, 0):
            debt_to_equity = float(total_debt) / float(total_equity)
        else:
            raw_debt_to_equity = cls.first_available(info, "debtToEquity")
            if raw_debt_to_equity is not None:
                debt_to_equity = float(raw_debt_to_equity) / 100 if raw_debt_to_equity > 10 else float(raw_debt_to_equity)
        revenue_growth, revenue_growth_details = cls.statement_growth_details(income, ["Total Revenue"], 1, "income_stmt", "Annual YoY")
        if revenue_growth is None:
            revenue_growth, revenue_growth_details = cls.statement_growth_details(quarterly_income, ["Total Revenue"], 4, "quarterly_income_stmt", "Quarter YoY")
        if revenue_growth is None:
            revenue_growth = cls.first_available(info, "revenueGrowth")
            revenue_growth_details = {"method": "info.revenueGrowth", "source": "info", "current_value": revenue_growth}
        eps_growth, eps_growth_method, eps_growth_details = cls.calculate_eps_growth_yoy(quarterly_income, income, debug=debug)
        free_cash_flow = cls.calculate_free_cash_flow(cashflow)
        if free_cash_flow is None:
            free_cash_flow = cls.calculate_free_cash_flow(quarterly_cashflow)
        fcf_growth, fcf_growth_details = cls.calculate_fcf_growth_yoy(cashflow)
        if fcf_growth is None:
            fcf_growth, fcf_growth_details = cls.calculate_fcf_growth_yoy(quarterly_cashflow)
            if fcf_growth_details.get("source") == "cashflow":
                fcf_growth_details["source"] = "quarterly_cashflow"
        fcf_trend, fcf_trend_change = cls.calculate_fcf_trend(cashflow)
        if fcf_trend == "Neutral" and fcf_trend_change is None:
            fcf_trend, fcf_trend_change = cls.calculate_fcf_trend(quarterly_cashflow)
        fcf_trend_text = cls.format_trend_with_change(fcf_trend, fcf_trend_change)
        operating_income = cls.statement_value(income, ["Operating Income", "OperatingIncome"])
        total_revenue = cls.statement_value(income, ["Total Revenue"])
        operating_margin = None
        if operating_income is not None and total_revenue not in (None, 0):
            operating_margin = operating_income / total_revenue
        else:
            operating_margin = cls.first_available(info, "operatingMargins")
        operating_margin_details = {
            "method": "Operating Income / Total Revenue" if operating_income is not None and total_revenue not in (None, 0) else "info.operatingMargins",
            "source": "income_stmt" if operating_income is not None and total_revenue not in (None, 0) else "info",
            "current_value": operating_margin,
            "comparison_value": None
        }
        current_pe = cls.first_available(info, "trailingPE")
        pe_history = cls.calculate_pe_history(price_history, income)
        pe_3y_diff, pe_3y_label = cls.valuation_history_label(current_pe, pe_history["pe_3y_avg"])
        pe_5y_diff, pe_5y_label = cls.valuation_history_label(current_pe, pe_history["pe_5y_avg"])
        metrics = {
            "market_cap": {"label": "Market Cap", "value": cls.first_available(info, "marketCap") or fast_info.get("market_cap"), "type": "money", "section": "Valuation"},
            "enterprise_value": {"label": "Enterprise Value", "value": cls.first_available(info, "enterpriseValue"), "type": "money", "section": "Valuation"},
            "trailing_pe": {"label": "Trailing P/E", "value": current_pe, "type": "multiple", "section": "Valuation"},
            "forward_pe": {"label": "Forward P/E", "value": cls.first_available(info, "forwardPE"), "type": "multiple", "section": "Valuation"},
            "peg_ratio": {"label": "PEG Ratio", "value": cls.first_available(info, "pegRatio", "trailingPegRatio"), "type": "multiple", "section": "Valuation"},
            "price_sales": {"label": "Price/Sales", "value": cls.first_available(info, "priceToSalesTrailing12Months"), "type": "multiple", "section": "Valuation"},
            "price_book": {"label": "Price/Book", "value": cls.first_available(info, "priceToBook"), "type": "multiple", "section": "Valuation"},
            "ev_revenue": {"label": "EV/Revenue", "value": cls.first_available(info, "enterpriseToRevenue"), "type": "multiple", "section": "Valuation"},
            "ev_ebitda": {"label": "EV/EBITDA", "value": cls.first_available(info, "enterpriseToEbitda"), "type": "multiple", "section": "Valuation"},
            "pe_vs_3y_avg": {"label": "P/E vs 3Y Avg", "value": pe_3y_diff, "type": "history_percent", "section": "Valuation", "history_label": pe_3y_label},
            "pe_vs_5y_avg": {"label": "P/E vs 5Y Avg", "value": pe_5y_diff, "type": "history_percent", "section": "Valuation", "history_label": pe_5y_label},
            "ev_ebitda_vs_3y_avg": {"label": "EV/EBITDA vs 3Y Avg", "value": None, "type": "history_percent", "section": "Valuation", "history_label": None},
            "price_sales_vs_3y_avg": {"label": "P/S vs 3Y Avg", "value": None, "type": "history_percent", "section": "Valuation", "history_label": None},
            "revenue_growth_yoy": {"label": "Revenue Growth YoY", "value": revenue_growth, "type": "percent", "section": "Growth", "debug": revenue_growth_details},
            "eps_growth_yoy": {"label": "EPS Growth YoY", "value": eps_growth, "type": "percent", "section": "Growth", "debug": eps_growth_details},
            "eps_growth_method": {"label": "EPS Growth Method", "value": eps_growth_method, "type": "text", "section": "Growth"},
            "free_cash_flow": {"label": "Free Cash Flow", "value": free_cash_flow, "type": "money", "section": "Cash Flow"},
            "fcf_growth_yoy": {"label": "FCF Growth YoY", "value": fcf_growth, "type": "percent", "section": "Cash Flow", "debug": fcf_growth_details},
            "fcf_trend": {"label": "FCF Trend", "value": fcf_trend_text, "type": "text", "section": "Cash Flow"},
            "operating_margin": {"label": "Operating Margin", "value": operating_margin, "type": "percent", "section": "Quality", "debug": operating_margin_details},
            "profit_margin": {"label": "Profit Margin", "value": cls.first_available(info, "profitMargins"), "type": "percent", "section": "Quality"},
            "return_on_equity": {"label": "Return on Equity", "value": cls.first_available(info, "returnOnEquity"), "type": "percent", "section": "Quality"},
            "return_on_assets": {"label": "Return on Assets", "value": cls.first_available(info, "returnOnAssets"), "type": "percent", "section": "Quality"},
            "total_debt": {"label": "Total Debt", "value": total_debt, "type": "money", "section": "Balance Sheet"},
            "cash": {"label": "Cash", "value": cash, "type": "money", "section": "Balance Sheet"},
            "net_debt": {"label": "Net Debt", "value": net_debt, "type": "money", "section": "Balance Sheet"},
            "debt_equity": {"label": "Debt/Equity", "value": debt_to_equity, "type": "multiple", "section": "Balance Sheet", "debug": {"method": "Total Debt / Total Equity", "source": "balance_sheet", "current_value": total_debt, "comparison_value": total_equity}},
            "current_ratio": {"label": "Current Ratio", "value": cls.first_available(info, "currentRatio"), "type": "multiple", "section": "Balance Sheet"}
        }
        metrics.update(cls.calculate_shareholder_view(metrics))
        for metric_name, metric in metrics.items():
            metric["status"] = cls.classify_fundamental_metric(metric_name, metric.get("value"))
        return metrics

    @classmethod
    def format_fundamental_value(cls, value: Any, metric_type: str) -> str:
        if cls.is_missing_value(value):
            return "N/A"
        if metric_type == "text":
            return str(value)
        if metric_type == "money":
            return cls.format_compact_number(float(value))
        if metric_type == "percent":
            return f"{float(value) * 100:.1f}%"
        if metric_type == "history_percent":
            return f"{float(value) * 100:+.0f}%"
        if metric_type == "multiple":
            return f"{float(value):.1f}x"
        return str(value)

    @classmethod
    def classify_fundamental_metric(cls, name: str, value: Any) -> str:
        if cls.is_missing_value(value):
            return "neutral"
        if name in {"trailing_pe", "forward_pe"}:
            value = float(value)
            if value < 10:
                return "good"
            if value <= 20:
                return "neutral"
            if value > 25:
                return "bad"
            return "neutral"
        if name == "peg_ratio":
            value = float(value)
            if value < 1:
                return "good"
            if value <= 2:
                return "neutral"
            return "bad"
        if name == "debt_equity":
            value = float(value)
            if value < 0.5:
                return "good"
            if value <= 1.5:
                return "neutral"
            return "bad"
        if name == "fcf_trend":
            normalized = str(value).lower()
            if normalized.startswith("rising"):
                return "good"
            if normalized.startswith("falling"):
                return "bad"
            return "neutral"
        if name in {"pe_vs_3y_avg", "pe_vs_5y_avg", "ev_ebitda_vs_3y_avg", "price_sales_vs_3y_avg"}:
            if cls.is_missing_value(value):
                return "neutral"
            if value < -0.25:
                return "good"
            if value > 0.25:
                return "bad"
            return "neutral"
        if name in {"business_health", "balance_sheet_view"}:
            normalized = str(value).lower()
            if normalized in {"strong", "stable", "moderate"}:
                return "good" if normalized == "strong" else "neutral"
            if normalized in {"weak", "risky"}:
                return "bad"
            return "neutral"
        if name == "valuation_view":
            normalized = str(value).lower()
            if normalized == "cheap":
                return "good"
            if normalized == "expensive":
                return "bad"
            return "neutral"
        if name == "overall_fundamental_view":
            normalized = str(value).lower()
            if normalized == "attractive":
                return "good"
            if normalized == "risky":
                return "bad"
            return "neutral"
        return "neutral"

    @classmethod
    def print_fundamentals_debug(cls, metrics: dict[str, dict[str, Any]]) -> None:
        print("Fundamentals debug:")
        for metric_name in ("revenue_growth_yoy", "eps_growth_yoy", "fcf_growth_yoy", "operating_margin", "debt_equity"):
            metric = metrics.get(metric_name, {})
            details = metric.get("debug", {})
            print(f"  {metric.get('label', metric_name)}:")
            print(f"    method: {details.get('method', 'N/A')}")
            print(f"    source statement: {details.get('source', 'N/A')}")
            print(f"    row: {details.get('row', 'N/A')}")
            print(f"    dates used: current={details.get('current_dates', 'N/A')} comparison={details.get('comparison_dates', 'N/A')}")
            print(f"    current value: {details.get('current_value', 'N/A')}")
            print(f"    comparison value: {details.get('comparison_value', 'N/A')}")
            print(f"    calculated growth: {cls.format_fundamental_value(details.get('growth'), 'percent') if details.get('growth') is not None else 'N/A'}")
