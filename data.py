import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz


def fetch_data(ticker="SPY", period="60d", interval="15m", auto_adjust=True):
    """
    Fetch OHLCV data from Yahoo Finance.
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Data period (e.g., "60d", "1y")
        interval (str): Data interval (e.g., "15m", "1h")
        auto_adjust (bool): Whether to auto-adjust for splits/dividends
    
    Returns:
        pd.DataFrame: OHLCV data with datetime index
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
            prepost=True,
            actions=False
        )
        
        if data.empty:
            raise ValueError(f"No data retrieved for ticker {ticker}")
        
        # Ensure we have the required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Convert timezone to US Eastern (market time) if needed
        if data.index.tz is not None:
            if str(data.index.tz) != 'America/New_York':
                data.index = data.index.tz_convert('America/New_York')
        else:
            # Assume UTC and convert to Eastern
            data.index = data.index.tz_localize('UTC').tz_convert('America/New_York')
        
        return data
        
    except Exception as e:
        raise Exception(f"Error fetching data for {ticker}: {str(e)}")


def filter_regular_hours(data, start_time="09:30", end_time="16:00"):
    """
    Filter data to regular trading hours (RTH).
    
    Args:
        data (pd.DataFrame): OHLCV data with datetime index
        start_time (str): Start time in HH:MM format
        end_time (str): End time in HH:MM format
    
    Returns:
        pd.DataFrame: Filtered data for regular trading hours only
    """
    if data.empty:
        return data
    
    # Parse time strings
    start_time_obj = time(*map(int, start_time.split(':')))
    end_time_obj = time(*map(int, end_time.split(':')))
    
    # Filter based on time of day
    mask = (data.index.time >= start_time_obj) & (data.index.time <= end_time_obj)
    
    # Also filter out weekends (though Yahoo Finance typically doesn't include them)
    mask = mask & (data.index.weekday < 5)  # Monday=0, Friday=4
    
    filtered_data = data[mask].copy()
    
    return filtered_data


def get_market_data(ticker="SPY", period="60d", interval="15m", 
                   regular_hours_only=True, auto_adjust=True):
    """
    Main function to get market data with optional RTH filtering.
    
    Args:
        ticker (str): Stock ticker symbol
        period (str): Data period
        interval (str): Data interval
        regular_hours_only (bool): Whether to filter to regular trading hours
        auto_adjust (bool): Whether to auto-adjust for splits/dividends
    
    Returns:
        pd.DataFrame: Processed market data
    """
    # Fetch raw data
    data = fetch_data(ticker, period, interval, auto_adjust)
    
    # Filter to regular hours if requested
    if regular_hours_only:
        data = filter_regular_hours(data)
    
    # Remove any rows with NaN values
    data = data.dropna()
    
    if data.empty:
        raise ValueError(f"No valid data remaining after processing for {ticker}")
    
    return data


def validate_data_quality(data, min_bars=200):
    """
    Validate that we have sufficient data quality for indicator calculations.
    
    Args:
        data (pd.DataFrame): OHLCV data
        min_bars (int): Minimum number of bars required
    
    Returns:
        bool: True if data quality is sufficient
    
    Raises:
        ValueError: If data quality is insufficient
    """
    if data.empty:
        raise ValueError("Data is empty")
    
    if len(data) < min_bars:
        raise ValueError(f"Insufficient data: {len(data)} bars, need at least {min_bars}")
    
    # Check for any remaining NaN values
    if data.isnull().any().any():
        raise ValueError("Data contains NaN values")
    
    # Check for reasonable price data (no zeros or negative values)
    price_columns = ['Open', 'High', 'Low', 'Close']
    for col in price_columns:
        if (data[col] <= 0).any():
            raise ValueError(f"Invalid prices found in {col} column")
    
    # Check that High >= Low, High >= Open/Close, Low <= Open/Close
    if not (data['High'] >= data['Low']).all():
        raise ValueError("High prices less than Low prices found")
    
    if not (data['High'] >= data[['Open', 'Close']].max(axis=1)).all():
        raise ValueError("High prices less than Open/Close prices found")
    
    if not (data['Low'] <= data[['Open', 'Close']].min(axis=1)).all():
        raise ValueError("Low prices greater than Open/Close prices found")
    
    return True