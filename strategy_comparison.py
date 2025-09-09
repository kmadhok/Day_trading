import pandas as pd
import os
from datetime import datetime
from strategy_config import StrategyType


def combine_strategy_signals(strategy_results):
    """
    Combine signal data from multiple strategies into a single DataFrame.
    
    Args:
        strategy_results (dict): Dictionary with StrategyType keys and result dicts
    
    Returns:
        pd.DataFrame: Combined data with strategy-specific signal columns
    """
    if not strategy_results:
        raise ValueError("No strategy results provided")
    
    # Use the first strategy's data as the base (all strategies use same market data)
    base_strategy = list(strategy_results.keys())[0]
    base_data = strategy_results[base_strategy]['signal_data'].copy()
    
    # Keep only base columns (market data and indicators)
    base_columns = [
        'Open', 'High', 'Low', 'Close', 'Volume',
        'SMA_20', 'SMA_50', 'SMA_200', 'MACD', 'MACDs', 'RSI'
    ]
    
    combined_data = base_data[base_columns].copy()
    
    # Add strategy-specific signal columns
    for strategy_type, result in strategy_results.items():
        strategy_name = strategy_type.value
        signal_data = result['signal_data']
        
        # Add trend filters (these may vary by strategy due to confirmation periods)
        combined_data[f'trend_long_ok_{strategy_name}'] = signal_data['trend_long_ok']
        combined_data[f'trend_short_ok_{strategy_name}'] = signal_data['trend_short_ok']
        
        # Add MACD signals (may vary by zero-cross requirement)
        combined_data[f'macd_up_ok_{strategy_name}'] = signal_data['macd_up_ok']
        combined_data[f'macd_down_ok_{strategy_name}'] = signal_data['macd_down_ok']
        
        # Add RSI signals (may vary by thresholds)
        combined_data[f'rsi_up_ok_{strategy_name}'] = signal_data['rsi_up_ok']
        combined_data[f'rsi_down_ok_{strategy_name}'] = signal_data['rsi_down_ok']
        
        # Add volume filter for conservative strategy
        if 'volume_ok' in signal_data.columns:
            combined_data[f'volume_ok_{strategy_name}'] = signal_data['volume_ok']
        
        # Add final signals
        combined_data[f'buy_signal_{strategy_name}'] = signal_data['buy_signal']
        combined_data[f'sell_signal_{strategy_name}'] = signal_data['sell_signal']
        combined_data[f'signal_{strategy_name}'] = signal_data['signal']
        combined_data[f'matches_criteria_{strategy_name}'] = signal_data['matches_criteria']
    
    # Round numeric columns for readability
    numeric_columns = ['Open', 'High', 'Low', 'Close', 'SMA_20', 'SMA_50', 'SMA_200', 
                      'MACD', 'MACDs', 'RSI']
    
    for col in numeric_columns:
        if col in combined_data.columns:
            combined_data[col] = combined_data[col].round(4)
    
    return combined_data


def export_combined_strategies(strategy_results, ticker="SPY", interval="15m", 
                             trend_mode="pullback", output_dir=None, filename=None):
    """
    Export combined strategy data to CSV.
    
    Args:
        strategy_results (dict): Dictionary with StrategyType keys and result dicts
        ticker (str): Stock ticker
        interval (str): Time interval
        trend_mode (str): Trend mode used
        output_dir (str): Output directory (optional)
        filename (str): Custom filename (optional)
    
    Returns:
        dict: Export summary
    """
    try:
        # Combine strategy data
        combined_data = combine_strategy_signals(strategy_results)
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"signals_{ticker}_{interval}_{trend_mode}_all_strategies_{date_str}.csv"
        else:
            # Modify filename to indicate all strategies
            if filename.endswith('.csv'):
                filename = filename.replace('.csv', '_all_strategies.csv')
            else:
                filename += '_all_strategies.csv'
        
        # Create full filepath
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
        else:
            filepath = filename
        
        # Export to CSV
        combined_data.to_csv(filepath, index=True, index_label='Datetime')
        
        # Verify the file was created
        if not os.path.exists(filepath):
            raise Exception(f"Failed to create file: {filepath}")
        
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            raise Exception(f"Created empty file: {filepath}")
        
        # Create summary
        summary = {
            "export_successful": True,
            "filepath": filepath,
            "file_size_bytes": file_size,
            "ticker": ticker,
            "interval": interval,
            "trend_mode": trend_mode,
            "total_rows": len(combined_data),
            "strategies_included": [s.value for s in strategy_results.keys()],
            "export_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return summary
        
    except Exception as e:
        return {
            "export_successful": False,
            "error": str(e),
            "ticker": ticker,
            "interval": interval,
            "trend_mode": trend_mode
        }


def create_strategy_comparison(strategy_results, ticker="SPY", interval="15m", 
                             trend_mode="pullback", output_dir=None):
    """
    Create a strategy comparison summary CSV.
    
    Args:
        strategy_results (dict): Dictionary with StrategyType keys and result dicts
        ticker (str): Stock ticker
        interval (str): Time interval
        trend_mode (str): Trend mode used
        output_dir (str): Output directory (optional)
    
    Returns:
        dict: Comparison summary and export info
    """
    try:
        comparison_data = []
        
        for strategy_type, result in strategy_results.items():
            config = result['config']
            summary = result['signal_summary']
            backtest = result['backtest_results']
            
            row = {
                'strategy': config.name,
                'strategy_type': strategy_type.value,
                'description': config.description,
                'total_bars': summary['total_bars'],
                'buy_signals': summary['buy_signals'],
                'sell_signals': summary['sell_signals'],
                'total_signals': summary['buy_signals'] + summary['sell_signals'],
                'buy_frequency_pct': summary['buy_frequency_pct'],
                'sell_frequency_pct': summary['sell_frequency_pct'],
                'signal_rate_pct': summary['buy_frequency_pct'] + summary['sell_frequency_pct'],
                'indicators_required': config.indicators_required,
                'rsi_buy_threshold': config.rsi_buy_threshold,
                'rsi_sell_threshold': config.rsi_sell_threshold,
                'macd_require_zero_cross': config.macd_require_zero_cross,
                'trend_confirmation_periods': config.trend_confirmation_periods,
                'use_volume_filter': config.use_volume_filter
            }
            
            # Add backtest results if available
            if backtest:
                row.update({
                    'total_trades': backtest['total_trades'],
                    'win_rate_pct': backtest['win_rate'],
                    'total_return_pct': backtest['total_return_pct'],
                    'max_drawdown_pct': backtest['max_drawdown'],
                    'profit_factor': backtest['profit_factor'],
                    'sharpe_ratio': backtest['sharpe_ratio'],
                    'avg_win_pct': backtest['avg_win_pct'],
                    'avg_loss_pct': backtest['avg_loss_pct']
                })
            else:
                row.update({
                    'total_trades': 0,
                    'win_rate_pct': 0,
                    'total_return_pct': 0,
                    'max_drawdown_pct': 0,
                    'profit_factor': 0,
                    'sharpe_ratio': 0,
                    'avg_win_pct': 0,
                    'avg_loss_pct': 0
                })
            
            comparison_data.append(row)
        
        # Create DataFrame
        comparison_df = pd.DataFrame(comparison_data)
        
        # Generate filename
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"strategy_comparison_{ticker}_{interval}_{trend_mode}_{date_str}.csv"
        
        # Create full filepath
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
        else:
            filepath = filename
        
        # Export comparison CSV
        comparison_df.to_csv(filepath, index=False)
        
        # Verify the file was created
        if not os.path.exists(filepath):
            raise Exception(f"Failed to create comparison file: {filepath}")
        
        file_size = os.path.getsize(filepath)
        
        summary = {
            "comparison_successful": True,
            "filepath": filepath,
            "file_size_bytes": file_size,
            "ticker": ticker,
            "interval": interval,
            "trend_mode": trend_mode,
            "strategies_compared": len(comparison_data),
            "export_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "comparison_data": comparison_df
        }
        
        return summary
        
    except Exception as e:
        return {
            "comparison_successful": False,
            "error": str(e),
            "ticker": ticker,
            "interval": interval,
            "trend_mode": trend_mode
        }


def print_strategy_comparison(comparison_summary):
    """
    Print a formatted strategy comparison to console.
    
    Args:
        comparison_summary (dict): Summary from create_strategy_comparison
    """
    if not comparison_summary.get("comparison_successful", False):
        print(f"Comparison failed: {comparison_summary.get('error', 'Unknown error')}")
        return
    
    df = comparison_summary["comparison_data"]
    
    print(f"\n{'='*100}")
    print("STRATEGY COMPARISON SUMMARY")
    print(f"{'='*100}")
    
    # Strategy overview
    print(f"\n{'Strategy':<15} {'Signals':<12} {'Rate %':<8} {'Win %':<8} {'Return %':<10} {'Drawdown %':<12}")
    print("-" * 85)
    
    for _, row in df.iterrows():
        signals = f"{row['buy_signals']}B/{row['sell_signals']}S"
        print(f"{row['strategy']:<15} {signals:<12} {row['signal_rate_pct']:<8.2f} "
              f"{row['win_rate_pct']:<8.1f} {row['total_return_pct']:<10.2f} {row['max_drawdown_pct']:<12.2f}")
    
    print(f"\n{'='*100}")
    
    # Best performers
    if len(df) > 1:
        best_return = df.loc[df['total_return_pct'].idxmax(), 'strategy']
        best_winrate = df.loc[df['win_rate_pct'].idxmax(), 'strategy']
        best_sharpe = df.loc[df['sharpe_ratio'].idxmax(), 'strategy']
        lowest_drawdown = df.loc[df['max_drawdown_pct'].idxmin(), 'strategy']
        
        print("BEST PERFORMERS:")
        print(f"  Highest Return: {best_return}")
        print(f"  Highest Win Rate: {best_winrate}")
        print(f"  Best Sharpe Ratio: {best_sharpe}")
        print(f"  Lowest Drawdown: {lowest_drawdown}")
        print(f"{'='*100}")