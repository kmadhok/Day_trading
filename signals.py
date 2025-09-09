import pandas as pd
import numpy as np
from strategy_config import StrategyConfig, StrategyType, get_strategy_config


def calculate_volume_filter(data, lookback_periods=20):
    """
    Calculate volume filter for conservative strategy.
    
    Args:
        data (pd.DataFrame): Data with Volume column
        lookback_periods (int): Lookback period for volume average
    
    Returns:
        pd.DataFrame: Data with volume filter column added
    """
    result = data.copy()
    
    # Calculate rolling average volume
    volume_avg = data['Volume'].rolling(window=lookback_periods, min_periods=lookback_periods).mean()
    
    # Volume filter: current volume > average volume
    result['volume_ok'] = data['Volume'] > volume_avg
    
    return result


def calculate_trend_filters(data, trend_mode="pullback", confirmation_periods=1):
    """
    Calculate trend filter conditions for long and short signals.
    
    Args:
        data (pd.DataFrame): Data with SMA indicators
        trend_mode (str): "pullback" or "stacked"
        confirmation_periods (int): Number of consecutive periods required for trend confirmation
    
    Returns:
        pd.DataFrame: Data with trend filter columns added
    """
    result = data.copy()
    
    if trend_mode == "pullback":
        # Pullback mode: SMA_50 > SMA_200 and SMA_20 < SMA_50 (buying dips in uptrend)
        trend_long_condition = (data['SMA_50'] > data['SMA_200']) & (data['SMA_20'] < data['SMA_50'])
        # Short: SMA_50 < SMA_200 and SMA_20 > SMA_50 (selling rallies in downtrend)
        trend_short_condition = (data['SMA_50'] < data['SMA_200']) & (data['SMA_20'] > data['SMA_50'])
        
    elif trend_mode == "stacked":
        # Stacked mode: SMA_20 > SMA_50 > SMA_200 (strict trend stack)
        trend_long_condition = (data['SMA_20'] > data['SMA_50']) & (data['SMA_50'] > data['SMA_200'])
        # Short: SMA_20 < SMA_50 < SMA_200 (inverse trend stack)
        trend_short_condition = (data['SMA_20'] < data['SMA_50']) & (data['SMA_50'] < data['SMA_200'])
        
    else:
        raise ValueError(f"Invalid trend_mode: {trend_mode}. Must be 'pullback' or 'stacked'")
    
    # Apply confirmation periods requirement
    if confirmation_periods > 1:
        # Require trend condition to be True for confirmation_periods consecutive periods
        trend_long_confirmed = trend_long_condition.rolling(window=confirmation_periods, min_periods=confirmation_periods).sum() == confirmation_periods
        trend_short_confirmed = trend_short_condition.rolling(window=confirmation_periods, min_periods=confirmation_periods).sum() == confirmation_periods
        
        result['trend_long_ok'] = trend_long_confirmed
        result['trend_short_ok'] = trend_short_confirmed
    else:
        result['trend_long_ok'] = trend_long_condition
        result['trend_short_ok'] = trend_short_condition
    
    return result


def calculate_macd_signals(data, require_zero_cross=True):
    """
    Calculate MACD crossover signals.
    
    Args:
        data (pd.DataFrame): Data with MACD and MACDs indicators
        require_zero_cross (bool): Whether to require zero line cross for signals
    
    Returns:
        pd.DataFrame: Data with MACD signal columns added
    """
    result = data.copy()
    
    # Shift data to get previous values (avoid lookahead)
    prev_macd = data['MACD'].shift(1)
    prev_signal = data['MACDs'].shift(1)
    curr_macd = data['MACD']
    curr_signal = data['MACDs']
    
    if require_zero_cross:
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
    else:
        # Any MACD crossover (for aggressive strategy)
        result['macd_up_ok'] = (prev_macd <= prev_signal) & (curr_macd > curr_signal)
        result['macd_down_ok'] = (prev_macd >= prev_signal) & (curr_macd < curr_signal)
    
    return result


def calculate_rsi_signals(data, buy_threshold=52.0, sell_threshold=48.0):
    """
    Calculate RSI crossover signals.
    
    Args:
        data (pd.DataFrame): Data with RSI indicator
        buy_threshold (float): RSI threshold for buy signals
        sell_threshold (float): RSI threshold for sell signals
    
    Returns:
        pd.DataFrame: Data with RSI signal columns added
    """
    result = data.copy()
    
    # Shift data to get previous values (avoid lookahead)
    prev_rsi = data['RSI'].shift(1)
    curr_rsi = data['RSI']
    
    # RSI cross up: RSI_prev < 50 and RSI_now > buy_threshold
    result['rsi_up_ok'] = (prev_rsi < 50) & (curr_rsi > buy_threshold)
    
    # RSI cross down: RSI_prev > 50 and RSI_now < sell_threshold
    result['rsi_down_ok'] = (prev_rsi > 50) & (curr_rsi < sell_threshold)
    
    return result


def generate_signals(data, trend_mode="pullback", strategy_type=StrategyType.CURRENT):
    """
    Generate BUY/SELL/HOLD signals based on strategy configuration.
    
    Args:
        data (pd.DataFrame): Data with all indicators
        trend_mode (str): "pullback" or "stacked"
        strategy_type (StrategyType): Strategy configuration to use
    
    Returns:
        pd.DataFrame: Data with signal columns added
    """
    if data.empty:
        raise ValueError("Input data is empty")
    
    result = data.copy()
    
    # Get strategy configuration
    config = get_strategy_config(strategy_type)
    
    # Calculate all signal components based on strategy configuration
    result = calculate_trend_filters(result, trend_mode, config.trend_confirmation_periods)
    result = calculate_macd_signals(result, config.macd_require_zero_cross)
    result = calculate_rsi_signals(result, config.rsi_buy_threshold, config.rsi_sell_threshold)
    
    # Add volume filter for conservative strategy
    if config.use_volume_filter:
        result = calculate_volume_filter(result, config.volume_lookback_periods)
    
    # Create indicator lists for flexible signal generation
    buy_conditions = [result['trend_long_ok'], result['macd_up_ok'], result['rsi_up_ok']]
    sell_conditions = [result['trend_short_ok'], result['macd_down_ok'], result['rsi_down_ok']]
    
    # Add volume condition for conservative strategy
    if config.use_volume_filter:
        buy_conditions.append(result['volume_ok'])
        sell_conditions.append(result['volume_ok'])
    
    # Generate signals based on strategy requirements
    if config.indicators_required == len([c for c in buy_conditions if 'volume_ok' not in str(c)]):
        # All indicators must align (current and conservative)
        if config.use_volume_filter:
            # Conservative: all 3 indicators + volume
            result['buy_signal'] = (
                result['trend_long_ok'] & 
                result['macd_up_ok'] & 
                result['rsi_up_ok'] & 
                result['volume_ok']
            )
            result['sell_signal'] = (
                result['trend_short_ok'] & 
                result['macd_down_ok'] & 
                result['rsi_down_ok'] & 
                result['volume_ok']
            )
        else:
            # Current: all 3 indicators
            result['buy_signal'] = (
                result['trend_long_ok'] & 
                result['macd_up_ok'] & 
                result['rsi_up_ok']
            )
            result['sell_signal'] = (
                result['trend_short_ok'] & 
                result['macd_down_ok'] & 
                result['rsi_down_ok']
            )
    else:
        # Aggressive: any 2 of 3 indicators
        buy_signal_count = (
            result['trend_long_ok'].astype(int) + 
            result['macd_up_ok'].astype(int) + 
            result['rsi_up_ok'].astype(int)
        )
        sell_signal_count = (
            result['trend_short_ok'].astype(int) + 
            result['macd_down_ok'].astype(int) + 
            result['rsi_down_ok'].astype(int)
        )
        
        result['buy_signal'] = buy_signal_count >= config.indicators_required
        result['sell_signal'] = sell_signal_count >= config.indicators_required
    
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


def get_signal_summary(data, trend_mode="pullback", strategy_type=StrategyType.CURRENT):
    """
    Get a summary of signal generation results.
    
    Args:
        data (pd.DataFrame): Data with signals
        trend_mode (str): Trend mode used
        strategy_type (StrategyType): Strategy type used
    
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
    
    config = get_strategy_config(strategy_type)
    
    summary = {
        "strategy_name": config.name,
        "strategy_type": strategy_type.value,
        "trend_mode": trend_mode,
        "total_bars": total_bars,
        "buy_signals": len(buy_timestamps),
        "sell_signals": len(sell_timestamps),
        "buy_frequency_pct": round(buy_freq, 2),
        "sell_frequency_pct": round(sell_freq, 2),
        "first_signal_time": min(buy_timestamps + sell_timestamps) if (buy_timestamps + sell_timestamps) else None,
        "last_signal_time": max(buy_timestamps + sell_timestamps) if (buy_timestamps + sell_timestamps) else None,
        "strategy_description": config.description,
        "validation": validation
    }
    
    return summary