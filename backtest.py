import pandas as pd
import numpy as np
from datetime import datetime


class SimpleBacktest:
    """
    Simple backtesting engine for trading signals.
    
    Execution assumption: if a signal occurs on bar t, enter/exit at bar t+1 open.
    Only one position at a time. No stops/TP by default.
    """
    
    def __init__(self, initial_capital=10000, commission=0.0, slippage=0.0):
        """
        Initialize the backtest engine.
        
        Args:
            initial_capital (float): Starting capital
            commission (float): Commission per trade (flat fee)
            slippage (float): Slippage as fraction of price (e.g., 0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.reset()
    
    def reset(self):
        """Reset backtest state."""
        self.capital = self.initial_capital
        self.position = 0  # 1 = long, -1 = short, 0 = no position
        self.entry_price = None
        self.entry_time = None
        self.trades = []
        self.equity_curve = []
        
    def calculate_fill_price(self, open_price, signal_type):
        """
        Calculate actual fill price including slippage.
        
        Args:
            open_price (float): Open price for the bar
            signal_type (str): 'BUY' or 'SELL'
        
        Returns:
            float: Fill price after slippage
        """
        if signal_type == 'BUY':
            # Pay slippage when buying
            return open_price * (1 + self.slippage)
        elif signal_type == 'SELL':
            # Lose slippage when selling
            return open_price * (1 - self.slippage)
        else:
            return open_price
    
    def execute_trade(self, timestamp, open_price, signal_type):
        """
        Execute a trade based on signal.
        
        Args:
            timestamp: Trade timestamp
            open_price (float): Open price for execution
            signal_type (str): 'BUY' or 'SELL'
        
        Returns:
            dict: Trade execution details
        """
        fill_price = self.calculate_fill_price(open_price, signal_type)
        
        trade_info = {
            'timestamp': timestamp,
            'signal': signal_type,
            'price': fill_price,
            'commission': self.commission,
            'position_before': self.position,
            'position_after': None,
            'pnl': 0.0,
            'capital_before': self.capital,
            'capital_after': None
        }
        
        if signal_type == 'BUY':
            if self.position == 0:
                # Enter long position
                self.position = 1
                self.entry_price = fill_price
                self.entry_time = timestamp
                self.capital -= self.commission
                trade_info['action'] = 'ENTER_LONG'
                
            elif self.position == -1:
                # Close short and enter long
                pnl = (self.entry_price - fill_price) * abs(self.position)
                self.capital += pnl - self.commission
                
                # Record the close trade
                self.trades.append({
                    'entry_time': self.entry_time,
                    'exit_time': timestamp,
                    'entry_price': self.entry_price,
                    'exit_price': fill_price,
                    'position': self.position,
                    'pnl': pnl,
                    'commission': self.commission
                })
                
                # Enter new long position
                self.position = 1
                self.entry_price = fill_price
                self.entry_time = timestamp
                self.capital -= self.commission
                trade_info['pnl'] = pnl
                trade_info['action'] = 'CLOSE_SHORT_ENTER_LONG'
            
        elif signal_type == 'SELL':
            if self.position == 0:
                # Enter short position
                self.position = -1
                self.entry_price = fill_price
                self.entry_time = timestamp
                self.capital -= self.commission
                trade_info['action'] = 'ENTER_SHORT'
                
            elif self.position == 1:
                # Close long and enter short
                pnl = (fill_price - self.entry_price) * abs(self.position)
                self.capital += pnl - self.commission
                
                # Record the close trade
                self.trades.append({
                    'entry_time': self.entry_time,
                    'exit_time': timestamp,
                    'entry_price': self.entry_price,
                    'exit_price': fill_price,
                    'position': self.position,
                    'pnl': pnl,
                    'commission': self.commission
                })
                
                # Enter new short position
                self.position = -1
                self.entry_price = fill_price
                self.entry_time = timestamp
                self.capital -= self.commission
                trade_info['pnl'] = pnl
                trade_info['action'] = 'CLOSE_LONG_ENTER_SHORT'
        
        trade_info['position_after'] = self.position
        trade_info['capital_after'] = self.capital
        
        return trade_info
    
    def calculate_unrealized_pnl(self, current_price):
        """
        Calculate unrealized P&L for current position.
        
        Args:
            current_price (float): Current market price
        
        Returns:
            float: Unrealized P&L
        """
        if self.position == 0 or self.entry_price is None:
            return 0.0
        
        if self.position == 1:  # Long position
            return (current_price - self.entry_price) * abs(self.position)
        elif self.position == -1:  # Short position
            return (self.entry_price - current_price) * abs(self.position)
        
        return 0.0
    
    def run_backtest(self, data):
        """
        Run backtest on signal data.
        
        Args:
            data (pd.DataFrame): Data with OHLCV, signals, and next bar open prices
        
        Returns:
            dict: Backtest results
        """
        if data.empty:
            raise ValueError("Input data is empty")
        
        self.reset()
        
        # Prepare data with next bar open prices for execution
        data_with_next_open = data.copy()
        data_with_next_open['next_open'] = data['Open'].shift(-1)
        
        # Track equity curve
        equity_history = []
        
        for i, (timestamp, row) in enumerate(data_with_next_open.iterrows()):
            # Calculate current equity (realized + unrealized)
            unrealized_pnl = self.calculate_unrealized_pnl(row['Close'])
            current_equity = self.capital + unrealized_pnl
            
            equity_history.append({
                'timestamp': timestamp,
                'capital': self.capital,
                'unrealized_pnl': unrealized_pnl,
                'total_equity': current_equity,
                'position': self.position,
                'price': row['Close']
            })
            
            # Check for signals and execute if we have next open price
            if pd.notna(row['next_open']):
                if row['signal'] in ['BUY', 'SELL']:
                    trade_info = self.execute_trade(
                        timestamp, row['next_open'], row['signal']
                    )
        
        # Close any remaining position at the last price
        if self.position != 0:
            last_row = data_with_next_open.iloc[-1]
            last_price = last_row['Close']
            
            pnl = self.calculate_unrealized_pnl(last_price)
            self.capital += pnl - self.commission
            
            self.trades.append({
                'entry_time': self.entry_time,
                'exit_time': last_row.name,
                'entry_price': self.entry_price,
                'exit_price': last_price,
                'position': self.position,
                'pnl': pnl,
                'commission': self.commission
            })
            
            self.position = 0
        
        # Convert equity curve to DataFrame
        self.equity_curve = pd.DataFrame(equity_history)
        
        return self.get_backtest_results()
    
    def get_backtest_results(self):
        """
        Get comprehensive backtest results.
        
        Returns:
            dict: Backtest performance metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'total_return': 0.0,
                'total_return_pct': 0.0,
                'final_capital': self.capital,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0
            }
        
        # Calculate basic metrics
        trades_df = pd.DataFrame(self.trades)
        total_pnl = trades_df['pnl'].sum()
        total_commission = trades_df['commission'].sum()
        net_pnl = total_pnl - total_commission
        
        # Win/Loss analysis
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        total_trades = len(trades_df)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0
        avg_win = winning_trades['pnl'].mean() if win_count > 0 else 0
        avg_loss = abs(losing_trades['pnl'].mean()) if loss_count > 0 else 0
        
        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if win_count > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if loss_count > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Drawdown calculation
        if not self.equity_curve.empty:
            running_max = self.equity_curve['total_equity'].expanding().max()
            drawdown = (self.equity_curve['total_equity'] - running_max) / running_max
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0.0
        
        # Returns calculation
        total_return = net_pnl
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Sharpe ratio (simplified - assumes daily data)
        if not self.equity_curve.empty:
            returns = self.equity_curve['total_equity'].pct_change().dropna()
            if len(returns) > 1 and returns.std() > 0:
                sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': round(win_rate * 100, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'total_pnl': round(total_pnl, 2),
            'total_commission': round(total_commission, 2),
            'net_pnl': round(net_pnl, 2),
            'total_return': round(total_return, 2),
            'total_return_pct': round(total_return_pct, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'inf',
            'sharpe_ratio': round(sharpe_ratio, 2)
        }
    
    def get_trade_log(self):
        """
        Get detailed trade log.
        
        Returns:
            pd.DataFrame: Trade log with all trade details
        """
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trades)
    
    def export_results(self, filepath, ticker="SPY", interval="15m", trend_mode="pullback"):
        """
        Export backtest results to CSV.
        
        Args:
            filepath (str): Output file path
            ticker (str): Stock ticker
            interval (str): Time interval
            trend_mode (str): Trend mode used
        
        Returns:
            str: Path to exported file
        """
        results = self.get_backtest_results()
        trade_log = self.get_trade_log()
        
        # Create summary
        summary_data = {
            'Metric': list(results.keys()),
            'Value': list(results.values())
        }
        summary_df = pd.DataFrame(summary_data)
        
        # Write to CSV with multiple sections
        with open(filepath, 'w') as f:
            f.write(f"# Backtest Results - {ticker} {interval} ({trend_mode} mode)\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n")
            summary_df.to_csv(f, index=False)
            f.write("\n")
            
            if not trade_log.empty:
                f.write("## Trade Log\n")
                trade_log.to_csv(f, index=False)
                f.write("\n")
            
            if not self.equity_curve.empty:
                f.write("## Equity Curve\n")
                self.equity_curve.to_csv(f, index=False)
        
        return filepath