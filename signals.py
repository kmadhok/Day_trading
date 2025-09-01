import pandas as pd
import numpy as np


def calculate_trend_filters(data, trend_mode="pullback"):
    """
    Calculate trend filter conditions for long and short signals.
    
    Args:
        data (pd.DataFrame): Data with SMA indicators
        trend_mode (str): "pullback" or "stacked"
    
    Returns:
        pd.DataFrame: Data with trend filter columns added
    """
    result = data.copy()
    
    if trend_mode == "pullback":
        # Pullback mode: SMA_50 > SMA_200 and SMA_20 < SMA_50 (buying dips in uptrend)
        result['trend_long_ok'] = (data['SMA_50'] > data['SMA_200']) & (data['SMA_20'] < data['SMA_50'])
        # Short: SMA_50 < SMA_200 and SMA_20 > SMA_50 (selling rallies in downtrend)
        result['trend_short_ok'] = (data['SMA_50'] < data['SMA_200']) & (data['SMA_20'] > data['SMA_50'])
        
    elif trend_mode == "stacked":
        # Stacked mode: SMA_20 > SMA_50 > SMA_200 (strict trend stack)
        result['trend_long_ok'] = (data['SMA_20'] > data['SMA_50']) & (data['SMA_50'] > data['SMA_200'])
        # Short: SMA_20 < SMA_50 < SMA_200 (inverse trend stack)
        result['trend_short_ok'] = (data['SMA_20'] < data['SMA_50']) & (data['SMA_50'] < data['SMA_200'])
        
    else:
        raise ValueError(f"Invalid trend_mode: {trend_mode}. Must be 'pullback' or 'stacked'")
    
    return result


def calculate_macd_signals(data):
    """
    Calculate MACD crossover signals.
    
    Args:
        data (pd.DataFrame): Data with MACD and MACDs indicators
    
    Returns:
        pd.DataFrame: Data with MACD signal columns added
    """
    result = data.copy()
    
    # Shift data to get previous values (avoid lookahead)
    prev_macd = data['MACD'].shift(1)
    prev_signal = data['MACDs'].shift(1)
    curr_macd = data['MACD']
    curr_signal = data['MACDs']
    
    # MACD cross up below zero:
    # MACD_prev <= Signal_prev and MACD_now > Signal_now and MACD_now < 0 and Signal_now < 0
    result['macd_up_ok'] = (
        (prev_macd <= prev_signal) & 
        (curr_macd > curr_signal) & 
        (curr_macd < 0) & 
        (curr_signal < 0)
    )
    
    # MACD cross down above zero:
    # MACD_prev >= Signal_prev and MACD_now < Signal_now and MACD_now > 0 and Signal_now > 0
    result['macd_down_ok'] = (
        (prev_macd >= prev_signal) & 
        (curr_macd < curr_signal) & 
        (curr_macd > 0) & 
        (curr_signal > 0)
    )
    
    return result


def calculate_rsi_signals(data):
    """
    Calculate RSI crossover signals.
    
    Args:
        data (pd.DataFrame): Data with RSI indicator
    
    Returns:
        pd.DataFrame: Data with RSI signal columns added
    """
    result = data.copy()
    
    # Shift data to get previous values (avoid lookahead)
    prev_rsi = data['RSI'].shift(1)
    curr_rsi = data['RSI']
    
    # RSI cross up: RSI_prev < 50 and RSI_now > 52
    result['rsi_up_ok'] = (prev_rsi < 50) & (curr_rsi > 52)
    
    # RSI cross down: RSI_prev > 50 and RSI_now < 48
    result['rsi_down_ok'] = (prev_rsi > 50) & (curr_rsi < 48)
    
    return result


def generate_signals(data, trend_mode="pullback"):
    """
    Generate BUY/SELL/HOLD signals based on all conditions.
    
    Long (BUY) must satisfy all:
    - Trend filter (depends on trend_mode)
    - MACD cross up below zero
    - RSI cross up through 50 to >52
    
    Short (SELL) must satisfy all:
    - Trend filter (depends on trend_mode)
    - MACD cross down above zero
    - RSI cross down through 50 to <48
    
    Args:
        data (pd.DataFrame): Data with all indicators
        trend_mode (str): "pullback" or "stacked"
    
    Returns:
        pd.DataFrame: Data with signal columns added
    """
    if data.empty:
        raise ValueError("Input data is empty")
    
    result = data.copy()
    
    # Calculate all signal components
    result = calculate_trend_filters(result, trend_mode)
    result = calculate_macd_signals(result)
    result = calculate_rsi_signals(result)
    
    # Generate BUY signals
    result['buy_signal'] = (
        result['trend_long_ok'] & 
        result['macd_up_ok'] & 
        result['rsi_up_ok']
    )
    
    # Generate SELL signals
    result['sell_signal'] = (
        result['trend_short_ok'] & 
        result['macd_down_ok'] & 
        result['rsi_down_ok']
    )
    
    # Create final signal column
    result['signal'] = 'HOLD'
    result.loc[result['buy_signal'], 'signal'] = 'BUY'
    result.loc[result['sell_signal'], 'signal'] = 'SELL'
    
    # Create matches_criteria column (BUY or SELL)
    result['matches_criteria'] = result['buy_signal'] | result['sell_signal']
    
    return result


def validate_signals(data):
    """
    Validate signal generation results.
    
    Args:
        data (pd.DataFrame): Data with signals
    
    Returns:
        dict: Validation results
    """
    if data.empty:
        return {"valid": False, "error": "Data is empty"}
    
    required_columns = [
        'trend_long_ok', 'trend_short_ok', 'macd_up_ok', 'macd_down_ok',
        'rsi_up_ok', 'rsi_down_ok', 'buy_signal', 'sell_signal', 
        'signal', 'matches_criteria'
    ]
    
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        return {"valid": False, "error": f"Missing columns: {missing_columns}"}
    
    # Count signals
    buy_count = data['buy_signal'].sum()
    sell_count = data['sell_signal'].sum()
    hold_count = (data['signal'] == 'HOLD').sum()
    
    # Check for simultaneous BUY and SELL signals (should not happen)
    simultaneous = (data['buy_signal'] & data['sell_signal']).sum()
    if simultaneous > 0:
        return {"valid": False, "error": f"Found {simultaneous} simultaneous BUY and SELL signals"}
    
    # Check signal column consistency
    signal_buy_count = (data['signal'] == 'BUY').sum()
    signal_sell_count = (data['signal'] == 'SELL').sum()
    
    if buy_count != signal_buy_count:
        return {"valid": False, "error": f"BUY signal mismatch: {buy_count} vs {signal_buy_count}"}
    
    if sell_count != signal_sell_count:
        return {"valid": False, "error": f"SELL signal mismatch: {sell_count} vs {signal_sell_count}"}
    
    return {
        "valid": True,
        "total_bars": len(data),
        "buy_signals": buy_count,
        "sell_signals": sell_count,
        "hold_signals": hold_count,
        "signal_rate": (buy_count + sell_count) / len(data) * 100
    }


def get_signal_summary(data, trend_mode="pullback"):
    """
    Get a summary of signal generation results.
    
    Args:
        data (pd.DataFrame): Data with signals
        trend_mode (str): Trend mode used
    
    Returns:
        dict: Signal summary
    """
    validation = validate_signals(data)
    
    if not validation["valid"]:
        return validation
    
    # Get timestamps of signals
    buy_timestamps = data[data['buy_signal']].index.tolist()
    sell_timestamps = data[data['sell_signal']].index.tolist()
    
    # Calculate signal frequencies
    total_bars = len(data)
    buy_freq = len(buy_timestamps) / total_bars * 100 if total_bars > 0 else 0
    sell_freq = len(sell_timestamps) / total_bars * 100 if total_bars > 0 else 0
    
    summary = {
        "trend_mode": trend_mode,
        "total_bars": total_bars,
        "buy_signals": len(buy_timestamps),
        "sell_signals": len(sell_timestamps),
        "buy_frequency_pct": round(buy_freq, 2),
        "sell_frequency_pct": round(sell_freq, 2),
        "first_signal_time": min(buy_timestamps + sell_timestamps) if (buy_timestamps + sell_timestamps) else None,
        "last_signal_time": max(buy_timestamps + sell_timestamps) if (buy_timestamps + sell_timestamps) else None,
        "validation": validation
    }
    
    return summary