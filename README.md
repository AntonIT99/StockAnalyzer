# Stock Technical Chart

A neutral desktop charting tool for viewing a configurable stock or ETF ticker with common technical indicators.

The application uses `yfinance` for market data, `pandas` for calculations, `matplotlib` for charting, and `tkinter` for the desktop UI.

## Usage

Run the application:

```powershell
py main.py
```

Enter a ticker symbol in the `Ticker` field, choose the period and interval, select the indicators you want to display, then click `Update`.

Examples of ticker formats supported by Yahoo Finance:

```text
AAPL
MSFT
SPY
BTC-USD
SHOP.TO
```

## Indicators

The chart can display these overlays:

```text
EMA 9
EMA 12
EMA 20
EMA 50
EMA 200
SMA 20
SMA 50
SMA 100
SMA 200
Bollinger Bands
```

It can also display these separate indicator panels:

```text
RSI 14
MACD
```

## Moving Average Data Window

The application downloads extra historical data before the selected visible period. This lets longer moving averages, such as `SMA 200` and `EMA 200`, be calculated before the visible chart begins.

After indicators are calculated, the chart is trimmed back to the selected period.

## Core Moving Averages

### EMA 20

The 20-period Exponential Moving Average reacts quickly to recent price changes.

Use it for:

* short-term momentum
* early trend shifts
* recovery or weakness detection

Bullish interpretation:

```text
Price > EMA20
EMA20 rising
```

Bearish interpretation:

```text
Price < EMA20
EMA20 falling
```

### EMA 50

The 50-period Exponential Moving Average shows the medium-term trend.

Use it for:

* trend confirmation
* identifying pullbacks
* filtering shorter-term noise

Bullish interpretation:

```text
Price > EMA50
EMA20 > EMA50
```

Bearish interpretation:

```text
Price < EMA50
EMA20 < EMA50
```

### SMA 50

The 50-period Simple Moving Average is widely watched by traders and institutions.

Use it for:

* medium-term trend analysis
* Golden Cross / Death Cross signals
* dynamic support and resistance

### SMA 200

The 200-period Simple Moving Average is a common long-term trend indicator.

Use it for:

* long-term trend direction
* major support and resistance zones
* broad trend confirmation

### EMA 200

The 200-period Exponential Moving Average is a more reactive version of the long-term trend line.

Use it for:

* earlier long-term trend warnings
* faster reaction to major price changes
* comparing slow trend versus reactive trend

## Moving Average Cross Signals

### Golden Cross

```text
SMA50 crosses above SMA200
```

Interpretation:

The medium-term trend has become stronger than the long-term trend. Traders often interpret this as a possible long-term bullish phase.

### Death Cross

```text
SMA50 crosses below SMA200
```

Interpretation:

The medium-term trend has weakened below the long-term trend. Traders often interpret this as a possible long-term bearish phase.

### EMA20 / EMA50 Bullish Cross

```text
EMA20 crosses above EMA50
```

Interpretation:

Recent price action is improving faster than the medium-term trend.

### EMA20 / EMA50 Bearish Cross

```text
EMA20 crosses below EMA50
```

Interpretation:

Recent price action is deteriorating faster than the medium-term trend.

## RSI Signals

RSI means Relative Strength Index. It measures momentum on a scale from 0 to 100.

### Overbought

```text
RSI > 70
```

Interpretation:

The asset may be stretched upward. Overbought does not automatically mean sell, because strong trends can remain overbought for a long time.

### Oversold

```text
RSI < 30
```

Interpretation:

The asset may be stretched downward. Oversold does not automatically mean buy, because weak trends can remain oversold for a long time.

## MACD Signals

MACD means Moving Average Convergence Divergence.

Standard settings:

```text
MACD Line = EMA12 - EMA26
Signal Line = EMA9 of MACD Line
Histogram = MACD Line - Signal Line
```

### Bullish MACD Cross

```text
MACD Line crosses above Signal Line
```

Interpretation:

Momentum is turning positive.

### Bearish MACD Cross

```text
MACD Line crosses below Signal Line
```

Interpretation:

Momentum is turning negative.

## Bollinger Band Signals

Bollinger Bands usually consist of:

```text
Middle Band = SMA20
Upper Band = SMA20 + 2 standard deviations
Lower Band = SMA20 - 2 standard deviations
```

They show volatility and price extremes.

### Upper Band Touch

```text
Price touches or moves above upper band
```

Interpretation:

The asset is strong or possibly overextended. Context matters.

### Lower Band Touch

```text
Price touches or moves below lower band
```

Interpretation:

The asset is weak or possibly oversold. Context matters.

### Bollinger Squeeze

```text
Bands become unusually narrow
```

Interpretation:

Volatility is low. A larger move may be coming, but the squeeze does not predict direction by itself.

## Common Signal Combinations

### Strong Bullish Setup

```text
Price > EMA20
EMA20 > EMA50
Price > SMA50
SMA50 > SMA200
Price > SMA200
RSI between 50 and 70
MACD above Signal Line
```

### Early Recovery Setup

```text
Price crosses above EMA20
EMA20 starts rising
RSI crosses above 30 or 50
MACD crosses above Signal Line
```

### Warning Setup

```text
Price < EMA20
EMA20 < EMA50
RSI below 50
MACD below Signal Line
```

### Strong Bearish Setup

```text
Price < EMA20
EMA20 < EMA50
Price < SMA50
SMA50 < SMA200
Price < SMA200
RSI below 50
MACD below Signal Line
```

## False Signals

Technical indicators often fail in sideways markets.

Common problems:

* Moving averages produce whipsaws.
* RSI can stay overbought in strong uptrends.
* RSI can stay oversold in strong downtrends.
* MACD can give late signals.
* Bollinger breakouts can reverse quickly.
* Golden Cross and Death Cross are lagging indicators.

## Disclaimer

This application is for analysis and visualization only. Technical indicators are not investment advice. They should be combined with fundamental analysis, valuation, earnings reports, sector trends, and risk management.
