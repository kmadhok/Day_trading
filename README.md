# Day Trading Signal Engine

A Python-based day trading signal generator that implements SMA + MACD + RSI strategy with Yahoo Finance data.

## Features

- Fetches 15-minute OHLCV data from Yahoo Finance
- Calculates SMA (20, 50, 200), MACD (12,26,9), and RSI (14) indicators
- Generates BUY/SELL/HOLD signals based on precise trading rules
- Supports two trend modes: "pullback" and "stacked"
- Exports detailed CSV with all indicators and signals
- Optional backtesting with equity curve and trade log
- No lookahead bias - signals evaluated on completed bars only

## Installation

1. Ensure Python 3.7+ is installed
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

Or manually install:
```bash
pip install yfinance>=0.2.28 pandas>=2.0.0 numpy>=1.24.0 pytz>=2023.3
```

## Usage

### Basic Usage
Generate signals for SPY with default settings:
```bash
python main.py
```

### Advanced Usage
```bash
python main.py --ticker SPY --interval 15m --period 60d --trend-mode pullback --verbose
```

### With Backtesting
```bash
python main.py --ticker SPY --backtest --initial-capital 10000 --commission 1.0 --slippage 0.001
```

## Command Line Options

### Data Parameters
- `--ticker`: Stock ticker symbol (default: SPY)
- `--interval`: Data interval - 15m, 1h, 1d (default: 15m)
- `--period`: Data period - 60d, 1y (default: 60d)

### Strategy Parameters
- `--trend-mode`: Trend mode - "pullback" or "stacked" (default: pullback)
- `--wilder-rsi`: Use Wilder RSI calculation (default: True)
- `--regular-hours-only`: Filter to regular trading hours 9:30-16:00 ET (default: True)

### Output Parameters
- `--output-dir`: Output directory for CSV files
- `--filename`: Custom output filename

### Backtesting Parameters
- `--backtest`: Enable backtesting
- `--initial-capital`: Initial capital (default: 10000)
- `--commission`: Commission per trade (default: 0.0)
- `--slippage`: Slippage as fraction (default: 0.001 = 0.1%)

### Display Options
- `--verbose`: Enable detailed output
- `--quiet`: Minimize output

## Trading Strategy Rules

### Long (BUY) Signals
All conditions must be met simultaneously:

**Pullback Mode (default):**
- Trend: SMA_50 > SMA_200 AND SMA_20 < SMA_50
- MACD: Cross up below zero (MACD > Signal, both < 0)
- RSI: Cross up from <50 to >52

**Stacked Mode:**
- Trend: SMA_20 > SMA_50 > SMA_200
- MACD: Cross up below zero (MACD > Signal, both < 0)
- RSI: Cross up from <50 to >52

### Short (SELL) Signals
All conditions must be met simultaneously:

**Pullback Mode:**
- Trend: SMA_50 < SMA_200 AND SMA_20 > SMA_50
- MACD: Cross down above zero (MACD < Signal, both > 0)
- RSI: Cross down from >50 to <48

**Stacked Mode:**
- Trend: SMA_20 < SMA_50 < SMA_200
- MACD: Cross down above zero (MACD < Signal, both > 0)
- RSI: Cross down from >50 to <48

## Output Files

### Signal CSV
Contains all OHLCV data, indicators, and signals:
- `Open`, `High`, `Low`, `Close`, `Volume`
- `SMA_20`, `SMA_50`, `SMA_200`
- `MACD`, `MACDs` (signal line)
- `RSI`
- `trend_long_ok`, `trend_short_ok`
- `macd_up_ok`, `macd_down_ok`
- `rsi_up_ok`, `rsi_down_ok`
- `buy_signal`, `sell_signal`, `signal`
- `matches_criteria`

### Backtest CSV (if enabled)
Contains performance metrics, trade log, and equity curve.

## Examples

### Compare Trend Modes
```bash
# Pullback mode
python main.py --ticker SPY --trend-mode pullback --output-dir results --verbose

# Stacked mode  
python main.py --ticker SPY --trend-mode stacked --output-dir results --verbose
```

### Different Tickers and Timeframes
```bash
# QQQ with 1-hour bars
python main.py --ticker QQQ --interval 1h --period 60d --backtest

# TSLA with 15-minute bars
python main.py --ticker TSLA --interval 15m --period 30d --backtest --verbose
```

## Performance Notes

- Typical execution time: <5 seconds for 60-day 15-minute data
- Yahoo Finance intraday data limited to ~60 days
- Regular trading hours filtering recommended for better signal quality
- 200+ bars required for reliable indicator calculations

## Risk Disclaimer

This is a research tool for educational purposes. Past performance does not guarantee future results. Always test strategies thoroughly and never risk more than you can afford to lose.

## File Structure

```
day_trading/
├── main.py          # Main application entry point
├── data.py          # Yahoo Finance data fetching
├── indicators.py    # Technical indicator calculations
├── signals.py       # Signal generation logic
├── export.py        # CSV export functionality
├── backtest.py      # Simple backtesting engine
├── requirements.txt # Python dependencies
└── README.md        # This file
```