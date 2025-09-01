#!/usr/bin/env python3
"""
Day Trading Signal Engine - Main Application
Implements SMA + MACD + RSI strategy with Yahoo Finance data

Usage:
    python main.py --ticker SPY --interval 15m --period 60d --trend-mode pullback
"""

import argparse
import sys
import time
from datetime import datetime

# Import our modules
from data import get_market_data, validate_data_quality
from indicators import calculate_all_indicators, drop_warmup_period
from signals import generate_signals, get_signal_summary
from export import export_with_summary
from backtest import SimpleBacktest


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Day Trading Signal Engine - SMA + MACD + RSI Strategy',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Data parameters
    parser.add_argument(
        '--ticker', 
        type=str, 
        default='SPY',
        help='Stock ticker symbol'
    )
    
    parser.add_argument(
        '--interval', 
        type=str, 
        default='15m',
        help='Data interval (e.g., 15m, 1h, 1d)'
    )
    
    parser.add_argument(
        '--period', 
        type=str, 
        default='60d',
        help='Data period (e.g., 60d, 1y)'
    )
    
    # Strategy parameters
    parser.add_argument(
        '--trend-mode', 
        type=str, 
        choices=['pullback', 'stacked'],
        default='pullback',
        help='Trend mode: pullback (50>200 & 20<50) or stacked (20>50>200)'
    )
    
    parser.add_argument(
        '--wilder-rsi', 
        action='store_true',
        default=True,
        help='Use Wilder RSI calculation method'
    )
    
    parser.add_argument(
        '--regular-hours-only', 
        action='store_true',
        default=True,
        help='Filter to regular trading hours (9:30-16:00 ET)'
    )
    
    # Output parameters
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default=None,
        help='Output directory for CSV files'
    )
    
    parser.add_argument(
        '--filename', 
        type=str, 
        default=None,
        help='Custom output filename'
    )
    
    # Backtest parameters
    parser.add_argument(
        '--backtest', 
        action='store_true',
        help='Run backtest simulation'
    )
    
    parser.add_argument(
        '--initial-capital', 
        type=float, 
        default=10000,
        help='Initial capital for backtesting'
    )
    
    parser.add_argument(
        '--commission', 
        type=float, 
        default=0.0,
        help='Commission per trade'
    )
    
    parser.add_argument(
        '--slippage', 
        type=float, 
        default=0.001,
        help='Slippage as fraction of price (e.g., 0.001 = 0.1%)'
    )
    
    # Display options
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--quiet', 
        action='store_true',
        help='Minimize output (only errors and final results)'
    )
    
    return parser.parse_args()


def print_progress(message, verbose=True):
    """Print progress message if verbose mode is enabled."""
    if verbose:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def main():
    """Main application entry point."""
    start_time = time.time()
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        verbose = args.verbose and not args.quiet
        
        print_progress("Starting Day Trading Signal Engine", verbose)
        print_progress(f"Configuration: {args.ticker} {args.interval} ({args.period}, {args.trend_mode} mode)", verbose)
        
        # Step 1: Fetch market data
        print_progress("Fetching market data from Yahoo Finance...", verbose)
        
        try:
            data = get_market_data(
                ticker=args.ticker,
                period=args.period,
                interval=args.interval,
                regular_hours_only=args.regular_hours_only
            )
            print_progress(f"Fetched {len(data)} bars from {data.index[0]} to {data.index[-1]}", verbose)
            
        except Exception as e:
            print(f"Error fetching data: {str(e)}", file=sys.stderr)
            return 1
        
        # Step 2: Validate data quality
        print_progress("Validating data quality...", verbose)
        
        try:
            validate_data_quality(data, min_bars=200)
            print_progress("Data validation passed", verbose)
            
        except Exception as e:
            print(f"Data validation failed: {str(e)}", file=sys.stderr)
            return 1
        
        # Step 3: Calculate indicators
        print_progress("Calculating technical indicators (SMA, MACD, RSI)...", verbose)
        
        try:
            data_with_indicators = calculate_all_indicators(
                data,
                sma_periods=[20, 50, 200],
                macd_params=(12, 26, 9),
                rsi_period=14,
                wilder_rsi=args.wilder_rsi,
                adjust_ema=False
            )
            print_progress("Technical indicators calculated", verbose)
            
        except Exception as e:
            print(f"Error calculating indicators: {str(e)}", file=sys.stderr)
            return 1
        
        # Step 4: Drop warm-up period
        print_progress("Removing warm-up period...", verbose)
        
        try:
            clean_data = drop_warmup_period(data_with_indicators, min_warmup=200)
            print_progress(f"Clean data: {len(clean_data)} bars after warm-up removal", verbose)
            
        except Exception as e:
            print(f"Error processing warm-up period: {str(e)}", file=sys.stderr)
            return 1
        
        # Step 5: Generate trading signals
        print_progress(f"Generating trading signals ({args.trend_mode} mode)...", verbose)
        
        try:
            signal_data = generate_signals(clean_data, trend_mode=args.trend_mode)
            signal_summary = get_signal_summary(signal_data, trend_mode=args.trend_mode)
            
            if not signal_summary["validation"]["valid"]:
                print(f"Signal validation failed: {signal_summary['validation']['error']}", file=sys.stderr)
                return 1
            
            print_progress(f"Signals generated: {signal_summary['buy_signals']} BUY, {signal_summary['sell_signals']} SELL", verbose)
            
        except Exception as e:
            print(f"Error generating signals: {str(e)}", file=sys.stderr)
            return 1
        
        # Step 6: Export to CSV
        print_progress("Exporting signals to CSV...", verbose)
        
        try:
            export_summary = export_with_summary(
                signal_data,
                ticker=args.ticker,
                interval=args.interval,
                trend_mode=args.trend_mode,
                output_dir=args.output_dir,
                filename=args.filename,
                print_summary=verbose
            )
            
            if not export_summary["export_successful"]:
                print(f"Export failed: {export_summary['error']}", file=sys.stderr)
                return 1
            
        except Exception as e:
            print(f"Error exporting CSV: {str(e)}", file=sys.stderr)
            return 1
        
        # Step 7: Run backtest if requested
        backtest_results = None
        if args.backtest:
            print_progress("Running backtest simulation...", verbose)
            
            try:
                bt = SimpleBacktest(
                    initial_capital=args.initial_capital,
                    commission=args.commission,
                    slippage=args.slippage
                )
                
                backtest_results = bt.run_backtest(signal_data)
                
                if verbose:
                    print("\nBacktest Results:")
                    print(f"Total Trades: {backtest_results['total_trades']}")
                    print(f"Win Rate: {backtest_results['win_rate']}%")
                    print(f"Total Return: ${backtest_results['total_return']} ({backtest_results['total_return_pct']}%)")
                    print(f"Max Drawdown: {backtest_results['max_drawdown']}%")
                    print(f"Profit Factor: {backtest_results['profit_factor']}")
                    print(f"Sharpe Ratio: {backtest_results['sharpe_ratio']}")
                
                # Export backtest results
                if args.output_dir or args.filename:
                    bt_filename = f"backtest_{args.ticker}_{args.interval}_{args.trend_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    if args.output_dir:
                        bt_filepath = f"{args.output_dir}/{bt_filename}"
                    else:
                        bt_filepath = bt_filename
                    
                    bt.export_results(bt_filepath, args.ticker, args.interval, args.trend_mode)
                    print_progress(f"Backtest results exported to: {bt_filepath}", verbose)
                
            except Exception as e:
                print(f"Error running backtest: {str(e)}", file=sys.stderr)
                return 1
        
        # Final summary
        elapsed_time = time.time() - start_time
        
        if not args.quiet:
            print(f"\n{'='*60}")
            print("DAY TRADING SIGNAL ENGINE - EXECUTION COMPLETE")
            print(f"{'='*60}")
            print(f"Ticker: {args.ticker} ({args.interval})")
            print(f"Trend Mode: {args.trend_mode}")
            print(f"Data Period: {args.period}")
            print(f"Processing Time: {elapsed_time:.2f} seconds")
            print(f"CSV Output: {export_summary['filepath']}")
            print(f"Total Bars: {signal_summary['total_bars']:,}")
            print(f"BUY Signals: {signal_summary['buy_signals']}")
            print(f"SELL Signals: {signal_summary['sell_signals']}")
            print(f"Signal Rate: {signal_summary['buy_frequency_pct'] + signal_summary['sell_frequency_pct']:.2f}%")
            
            if backtest_results:
                print(f"Backtest Return: {backtest_results['total_return_pct']}%")
                print(f"Win Rate: {backtest_results['win_rate']}%")
            
            print(f"{'='*60}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 1
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())