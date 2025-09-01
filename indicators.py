import pandas as pd
import numpy as np


def calculate_sma(data, periods):
    """
    Calculate Simple Moving Averages for given periods.
    
    Args:
        data (pd.DataFrame): OHLCV data
        periods (list): List of periods for SMA calculation
    
    Returns:
        pd.DataFrame: Data with SMA columns added
    """
    result = data.copy()
    
    for period in periods:
        col_name = f'SMA_{period}'
        result[col_name] = data['Close'].rolling(window=period, min_periods=period).mean()
    
    return result


def calculate_ema(series, span, adjust=False):
    """
    Calculate Exponential Moving Average.
    
    Args:
        series (pd.Series): Price series
        span (int): EMA span
        adjust (bool): Whether to adjust for bias
    
    Returns:
        pd.Series: EMA values
    """
    return series.ewm(span=span, adjust=adjust).mean()


def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9, adjust=False):
    """
    Calculate MACD indicator.
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal_period)
    
    Args:
        data (pd.DataFrame): OHLCV data
        fast_period (int): Fast EMA period
        slow_period (int): Slow EMA period
        signal_period (int): Signal line EMA period
        adjust (bool): Whether to adjust EMAs for bias
    
    Returns:
        pd.DataFrame: Data with MACD and MACDs columns added
    """
    result = data.copy()
    
    # Calculate EMAs
    ema_fast = calculate_ema(data['Close'], fast_period, adjust=adjust)
    ema_slow = calculate_ema(data['Close'], slow_period, adjust=adjust)
    
    # Calculate MACD line
    macd_line = ema_fast - ema_slow
    
    # Calculate Signal line
    signal_line = calculate_ema(macd_line, signal_period, adjust=adjust)
    
    result['MACD'] = macd_line
    result['MACDs'] = signal_line
    
    return result


def wilder_rsi(series, period=14):
    """
    Calculate RSI using Wilder's smoothing method (EWM approximation).
    
    Args:
        series (pd.Series): Price series
        period (int): RSI period
    
    Returns:
        pd.Series: RSI values
    """
    # Calculate price changes
    delta = series.diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Wilder's smoothing (equivalent to EWM with alpha=1/period)
    alpha = 1.0 / period
    
    # Calculate average gains and losses using EWM
    avg_gains = gains.ewm(alpha=alpha, adjust=False).mean()
    avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()
    
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def simple_rsi(series, period=14):
    """
    Calculate RSI using simple rolling averages.
    
    Args:
        series (pd.Series): Price series
        period (int): RSI period
    
    Returns:
        pd.Series: RSI values
    """
    # Calculate price changes
    delta = series.diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Calculate average gains and losses using rolling mean
    avg_gains = gains.rolling(window=period, min_periods=period).mean()
    avg_losses = losses.rolling(window=period, min_periods=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_rsi(data, period=14, wilder=True):
    """
    Calculate RSI indicator.
    
    Args:
        data (pd.DataFrame): OHLCV data
        period (int): RSI period
        wilder (bool): Whether to use Wilder's smoothing method
    
    Returns:
        pd.DataFrame: Data with RSI column added
    """
    result = data.copy()
    
    if wilder:
        result['RSI'] = wilder_rsi(data['Close'], period)
    else:
        result['RSI'] = simple_rsi(data['Close'], period)
    
    return result


def calculate_all_indicators(data, sma_periods=[20, 50, 200], 
                           macd_params=(12, 26, 9), rsi_period=14, 
                           wilder_rsi=True, adjust_ema=False):
    """
    Calculate all required indicators for the trading strategy.
    
    Args:
        data (pd.DataFrame): OHLCV data
        sma_periods (list): SMA periods to calculate
        macd_params (tuple): MACD parameters (fast, slow, signal)
        rsi_period (int): RSI period
        wilder_rsi (bool): Whether to use Wilder's RSI
        adjust_ema (bool): Whether to adjust EMAs for bias
    
    Returns:
        pd.DataFrame: Data with all indicators added
    """
    if data.empty:
        raise ValueError("Input data is empty")
    
    result = data.copy()
    
    # Calculate SMAs
    result = calculate_sma(result, sma_periods)
    
    # Calculate MACD
    fast, slow, signal = macd_params
    result = calculate_macd(result, fast, slow, signal, adjust=adjust_ema)
    
    # Calculate RSI
    result = calculate_rsi(result, rsi_period, wilder_rsi)
    
    return result


def drop_warmup_period(data, min_warmup=200):
    """
    Drop initial rows that don't have enough data for reliable indicator calculation.
    
    Args:
        data (pd.DataFrame): Data with indicators
        min_warmup (int): Minimum number of bars before starting analysis
    
    Returns:
        pd.DataFrame: Data with warmup period removed
    """
    if len(data) <= min_warmup:
        raise ValueError(f"Insufficient data: {len(data)} bars, need more than {min_warmup}")
    
    # Drop the first min_warmup rows
    result = data.iloc[min_warmup:].copy()
    
    # Verify no NaN values remain in indicator columns
    indicator_columns = [col for col in result.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']]
    
    if result[indicator_columns].isnull().any().any():
        # Find first valid index where all indicators are not null
        first_valid_idx = result[indicator_columns].dropna().index[0]
        result = result.loc[first_valid_idx:].copy()
    
    return result