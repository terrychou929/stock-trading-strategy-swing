import numpy as np
import pandas as pd
import sys
import yfinance as yf
from datetime import datetime, timedelta

# Parameters
INITIAL_CAPITAL = 1000000  # Initial capital in TWD
LOOKBACK_YEARS = 2  # Years of historical data
MA_PERIOD = 20  # Moving average period
RSI_PERIOD = 14  # RSI period
PROFIT_TARGET = 0.05  # 5% profit target
STOP_LOSS = -0.03  # 3% stop loss
MAX_HOLD_DAYS = 20  # Maximum holding period (~1 month)
FEE_RATE = 0.001425   # Transaction Fee
TAX_RATE = 0.003      # Sold Fee
SLIPPAGE = 0.001      # Slip Rate (will be dynamic later)


def fetch_stock_data(stock_code, start_date, end_date):
    """
    Fetch daily stock data from yfinance
    Args:
        stock_code (str): Stock symbol (e.g., '2330.TW' for TSMC, 'TSLA' for TESLA)
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format
    Returns:
        DataFrame: Daily OHLCV data
    """
    stock = yf.Ticker(stock_code)
    df = stock.history(start=start_date, end=end_date)
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]


def trading_strategy(df):
    """
    Implement trading strategy: Buy at relative low point and sell within a month
    Args:
        df (DataFrame): Stock data with OHLCV
    Returns:
        tuple: Lists of buy signals and sell signals
    """
    # Calculate moving averages
    df['MA'] = df['Close'].rolling(window=MA_PERIOD).mean()  # 20-day MA
    df['MA50'] = df['Close'].rolling(window=50).mean()       # 50-day MA for trend confirmation
    
    # Calculate RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Dynamic RSI oversold threshold based on 50-day mean and standard deviation
    RSI_OVERSOLD = df['RSI'].rolling(window=50).mean() - 2 * df['RSI'].rolling(window=50).std()
    
    # Volume moving average for liquidity filter
    df['Volume_MA'] = df['Volume'].rolling(window=10).mean()
    
    # Dynamic slippage based on volume
    SLIPPAGE = 0.001 * (df['Volume'].mean() / df['Volume'])
    
    buy_signals = []
    sell_signals = []
    position = None
    hold_days = 0
    trailing_stop = None  # For trailing stop mechanism
    
    for i in range(MA_PERIOD, len(df)):
        # Buy condition: Price below MA, RSI < dynamic oversold, rising MA50 trend, and sufficient volume
        if (df['Close'].iloc[i] < df['MA'].iloc[i] and 
            df['RSI'].iloc[i] < RSI_OVERSOLD.iloc[i] and 
            df['MA50'].diff().iloc[i] > 0 and  # Confirm 50-day MA is rising
            df['Volume'].iloc[i] > df['Volume_MA'].iloc[i] and  # Volume exceeds 10-day average
            position is None):
            buy_price = df['Close'].iloc[i]
            buy_signals.append({
                'date': df.index[i],
                'price': buy_price,
                'signal': 'BUY'
            })
            position = {
                'buy_price': buy_price,
                'buy_date': df.index[i],
                'highest_price': buy_price  # Track highest price for trailing stop
            }
            trailing_stop = buy_price * (1 + STOP_LOSS)  # Initial trailing stop at 3% below buy price
            hold_days = 0
            
        # Sell condition: Hit profit target, trailing stop, or max hold days
        elif position is not None:
            hold_days += 1
            current_price = df['Close'].iloc[i]
            profit_loss = (current_price - position['buy_price']) / position['buy_price']
            
            # Update highest price and trailing stop (e.g., 2% below highest price)
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
                trailing_stop = current_price * (1 - 0.02)  # Trailing stop at 2% below highest price
            
            # Sell if profit target reached, trailing stop hit, or max hold days exceeded
            if (profit_loss >= PROFIT_TARGET or
                current_price <= trailing_stop or
                hold_days >= MAX_HOLD_DAYS):
                sell_signals.append({
                    'date': df.index[i],
                    'price': current_price,
                    'signal': 'SELL'
                })
                position = None
                trailing_stop = None
    
    return buy_signals, sell_signals

# Backtest function (adjusted for dynamic slippage)
def backtest_strategy(df, initial_capital):
    """
    Backtest the trading strategy with dynamic slippage
    Args:
        df (DataFrame): Stock data
        initial_capital (float): Initial capital in TWD
    Returns:
        dict: Backtest results
    """
    buy_signals, sell_signals = trading_strategy(df)
    capital = initial_capital
    shares = 0
    trades = []
    
    # Calculate dynamic slippage
    df['Slippage'] = 0.001 * (df['Volume'].mean() / df['Volume'])
    
    for buy, sell in zip(buy_signals, sell_signals):
        buy_idx = df.index.get_loc(buy['date'])
        sell_idx = df.index.get_loc(sell['date'])
        buy_price = buy['price'] * (1 + df['Slippage'].iloc[buy_idx])  # Apply dynamic slippage
        sell_price = sell['price'] * (1 - df['Slippage'].iloc[sell_idx])

        # Buy Transaction
        shares = capital // buy_price
        cost = shares * buy_price
        buy_fee = cost * FEE_RATE
        capital -= (cost + buy_fee)

        # Sell Transaction
        revenue = shares * sell_price
        sell_fee = revenue * FEE_RATE
        tax = revenue * TAX_RATE
        capital += (revenue - sell_fee - tax)

        # Record Transaction
        profit = revenue - cost - buy_fee - sell_fee - tax
        trades.append({
            'buy_date': buy['date'],
            'buy_price': buy_price,
            'sell_date': sell['date'],
            'sell_price': sell_price,
            'profit': profit,
            'shares': shares
        })
    
    final_value = capital + (shares * df['Close'].iloc[-1] if shares > 0 else 0)
    return {
        'trades': trades,
        'final_capital': capital,
        'final_value': final_value,
        'total_profit': final_value - initial_capital,
        'num_trades': len(trades)
    }


def print_results(stock_code, start_date, end_date, results):
    """
    Print backtest results
    Args:
        stock_code (str): Stock symbol
        start_date (datetime): Start date
        end_date (datetime): End date
        results (dict): Backtest results
    """
    print(f"Stock: {stock_code}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Initial Capital: {INITIAL_CAPITAL:,} TWD")
    print(f"Final Value: {results['final_value']:,.2f} TWD")
    print(f"Total Profit: {results['total_profit']:,.2f} TWD")
    print(f"Number of Trades: {results['num_trades']}")
    print("\n=================")
    print("\nTrade Details:")
    for trade in results['trades']:
        print(f"Buy: {trade['buy_date'].date()} at {trade['buy_price']:,.2f}")
        print(f"Sell: {trade['sell_date'].date()} at {trade['sell_price']:,.2f}")
        print(f"Profit: {trade['profit']:,.2f} TWD")
        print(f"Shares: {trade['shares']}")
        print("-" * 30)

# Main execution
if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Please provide a stock code, e.g., python main.py 2330.TW")
        sys.exit(1)
    
    stock_code = sys.argv[1]    
    # Set dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * LOOKBACK_YEARS)
    
    # Fetch data
    df = fetch_stock_data(
        stock_code,
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    # Run backtest
    results = backtest_strategy(df, INITIAL_CAPITAL)
    
    # Print results
    print_results(stock_code, start_date, end_date, results)