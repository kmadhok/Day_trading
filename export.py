import pandas as pd
import os
from datetime import datetime


def prepare_export_data(data, ticker="SPY", interval="15m"):
    """
    Prepare data for CSV export with all required columns.
    
    Expected columns in output CSV:
    - Open, High, Low, Close, Volume
    - SMA_20, SMA_50, SMA_200  
    - MACD, MACDs (signal line)
    - RSI
    - trend_long_ok, trend_short_ok, macd_up_ok, macd_down_ok, rsi_up_ok, rsi_down_ok
    - buy_signal, sell_signal, signal (BUY/SELL/HOLD)
    - matches_criteria (BUY or SELL)
    
    Args:
        data (pd.DataFrame): Data with all indicators and signals
        ticker (str): Stock ticker for metadata
        interval (str): Time interval for metadata
    
    Returns:
        pd.DataFrame: Data ready for CSV export
    """
    if data.empty:
        raise ValueError("Input data is empty")
    
    # Define expected columns in order
    expected_columns = [
        # OHLCV data
        'Open', 'High', 'Low', 'Close', 'Volume',
        # SMA indicators
        'SMA_20', 'SMA_50', 'SMA_200',
        # MACD indicators
        'MACD', 'MACDs',
        # RSI indicator
        'RSI',
        # Trend filters
        'trend_long_ok', 'trend_short_ok',
        # MACD signals
        'macd_up_ok', 'macd_down_ok',
        # RSI signals
        'rsi_up_ok', 'rsi_down_ok',
        # Final signals
        'buy_signal', 'sell_signal', 'signal',
        # Matches criteria
        'matches_criteria'
    ]
    
    # Check for missing columns
    missing_columns = [col for col in expected_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Select and reorder columns
    export_data = data[expected_columns].copy()
    
    # Round numeric columns for readability
    numeric_columns = ['Open', 'High', 'Low', 'Close', 'SMA_20', 'SMA_50', 'SMA_200', 
                      'MACD', 'MACDs', 'RSI']
    
    for col in numeric_columns:
        if col in export_data.columns:
            export_data[col] = export_data[col].round(4)
    
    # Ensure proper data types for boolean columns
    boolean_columns = ['trend_long_ok', 'trend_short_ok', 'macd_up_ok', 'macd_down_ok',
                      'rsi_up_ok', 'rsi_down_ok', 'buy_signal', 'sell_signal', 'matches_criteria']
    
    for col in boolean_columns:
        if col in export_data.columns:
            export_data[col] = export_data[col].astype(bool)
    
    return export_data


def generate_filename(ticker="SPY", interval="15m", trend_mode="pullback", 
                     timestamp=None, output_dir=None):
    """
    Generate a descriptive filename for the CSV export.
    
    Args:
        ticker (str): Stock ticker
        interval (str): Time interval
        trend_mode (str): Trend mode used
        timestamp (datetime): Timestamp for filename (default: current time)
        output_dir (str): Output directory path
    
    Returns:
        str: Complete file path
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # Create base filename
    date_str = timestamp.strftime("%Y%m%d_%H%M%S")
    filename = f"signals_{ticker}_{interval}_{trend_mode}_{date_str}.csv"
    
    # Add output directory if specified
    if output_dir:
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
    else:
        filepath = filename
    
    return filepath


def export_to_csv(data, ticker="SPY", interval="15m", trend_mode="pullback",
                 output_dir=None, filename=None):
    """
    Export trading signals data to CSV file.
    
    Args:
        data (pd.DataFrame): Data with all indicators and signals
        ticker (str): Stock ticker
        interval (str): Time interval
        trend_mode (str): Trend mode used
        output_dir (str): Output directory (optional)
        filename (str): Custom filename (optional)
    
    Returns:
        str: Path to exported CSV file
    """
    if data.empty:
        raise ValueError("Cannot export empty data")
    
    # Prepare data for export
    export_data = prepare_export_data(data, ticker, interval)
    
    # Generate filename if not provided
    if filename is None:
        filepath = generate_filename(ticker, interval, trend_mode, output_dir=output_dir)
    else:
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
        else:
            filepath = filename
    
    # Export to CSV
    try:
        export_data.to_csv(filepath, index=True, index_label='Datetime')
        
        # Verify the file was created and has content
        if not os.path.exists(filepath):
            raise Exception(f"Failed to create file: {filepath}")
        
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            raise Exception(f"Created empty file: {filepath}")
        
        return filepath
        
    except Exception as e:
        raise Exception(f"Failed to export CSV to {filepath}: {str(e)}")


def create_export_summary(data, filepath, ticker="SPY", interval="15m", 
                         trend_mode="pullback"):
    """
    Create a summary of the exported data.
    
    Args:
        data (pd.DataFrame): Exported data
        filepath (str): Path to CSV file
        ticker (str): Stock ticker
        interval (str): Time interval
        trend_mode (str): Trend mode used
    
    Returns:
        dict: Export summary
    """
    if data.empty:
        return {"error": "Data is empty"}
    
    # Count signals
    buy_signals = data['buy_signal'].sum() if 'buy_signal' in data.columns else 0
    sell_signals = data['sell_signal'].sum() if 'sell_signal' in data.columns else 0
    total_signals = buy_signals + sell_signals
    
    # Get date range
    start_date = data.index[0] if len(data) > 0 else None
    end_date = data.index[-1] if len(data) > 0 else None
    
    # File info
    file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    
    summary = {
        "export_successful": True,
        "filepath": filepath,
        "file_size_bytes": file_size,
        "ticker": ticker,
        "interval": interval,
        "trend_mode": trend_mode,
        "total_rows": len(data),
        "date_range": {
            "start": start_date.strftime("%Y-%m-%d %H:%M:%S") if start_date else None,
            "end": end_date.strftime("%Y-%m-%d %H:%M:%S") if end_date else None
        },
        "signals": {
            "buy_count": int(buy_signals),
            "sell_count": int(sell_signals),
            "total_count": int(total_signals),
            "signal_rate_pct": round(total_signals / len(data) * 100, 2) if len(data) > 0 else 0
        },
        "export_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return summary


def export_with_summary(data, ticker="SPY", interval="15m", trend_mode="pullback",
                       output_dir=None, filename=None, print_summary=True):
    """
    Export data to CSV and return summary.
    
    Args:
        data (pd.DataFrame): Data with all indicators and signals
        ticker (str): Stock ticker
        interval (str): Time interval
        trend_mode (str): Trend mode used
        output_dir (str): Output directory (optional)
        filename (str): Custom filename (optional)
        print_summary (bool): Whether to print summary to console
    
    Returns:
        dict: Export summary including filepath
    """
    try:
        # Export to CSV
        filepath = export_to_csv(data, ticker, interval, trend_mode, output_dir, filename)
        
        # Create summary
        summary = create_export_summary(data, filepath, ticker, interval, trend_mode)
        
        if print_summary:
            print(f"\nExport Summary:")
            print(f"File: {summary['filepath']}")
            print(f"Ticker: {summary['ticker']} ({summary['interval']})")
            print(f"Trend Mode: {summary['trend_mode']}")
            print(f"Rows: {summary['total_rows']:,}")
            print(f"Date Range: {summary['date_range']['start']} to {summary['date_range']['end']}")
            print(f"Signals: {summary['signals']['buy_count']} BUY, {summary['signals']['sell_count']} SELL ({summary['signals']['signal_rate_pct']}%)")
            print(f"File Size: {summary['file_size_bytes']:,} bytes")
        
        return summary
        
    except Exception as e:
        error_summary = {
            "export_successful": False,
            "error": str(e),
            "ticker": ticker,
            "interval": interval,
            "trend_mode": trend_mode
        }
        
        if print_summary:
            print(f"\nExport Failed: {str(e)}")
        
        return error_summary