# Taiwan Stock Trading Strategy

This Python script implements a trading strategy for Taiwan stock market using daily price data. It fetches historical data, applies a technical analysis-based strategy, backtests it, and reports the results.

## Features
- Fetches daily OHLCV (Open, High, Low, Close, Volume) data using yfinance
- Implements a momentum-based trading strategy
- Backtests the strategy with historical data
- Provides detailed trade results and performance metrics

## Strategy Details
- **Buy Signal**: Price below 20-day MA AND RSI (14) < 30
- **Sell Signal**: 
  - Profit reaches 5% OR
  - Loss exceeds 3% OR
  - Holding period reaches 20 trading days (~1 month)
- Uses whole share lots for realistic trading simulation

## Installation and Usage
1. Install Python 3.8 or higher.
2. Create and activate a virtual environment:
3. Execute the main.py with stock code as the first argument
4. Check the generated file in output folder

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
# Install dependency
pip install -r requirements.txt
# Execution
python main.py {stock_code}
```