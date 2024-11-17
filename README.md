# K-line-Data-Analysis

This project provides a Flask-based web service to retrieve cryptocurrency data from Binance API and calculate technical indicators such as MACD and RSI. The service stores the data in an SQLite database and offers API endpoints to access the data and indicators.

## Prerequisites

- Python 3.7 or higher
- Required Python libraries (listed below)

## Libraries

This project uses the following libraries:

- `Flask`: A lightweight Python web framework.
- `requests`: To fetch data from the Binance API.
- `pandas`: For data manipulation and analysis.
- `numpy`: For numerical calculations.
- `sqlite3`: To interact with the SQLite database.
- `threading`: For running background tasks.
- `time`: To manage sleep intervals in background tasks.

You can install the required dependencies using the following command:

 ''' pip install -r requirements.txt '''


How code works:

The Flask web service retrieves cryptocurrency data from the Binance API, calculates technical indicators such as MACD (Moving Average Convergence Divergence) and RSI (Relative Strength Index), and stores the results in an SQLite database. Users can request this data and the calculated indicators via various API endpoints.


Core Flow:

Data Retrieval: The service fetches Kline data from the Binance API for specified cryptocurrency pairs (e.g., BTC/USDT).
Indicator Calculation: It calculates technical indicators (MACD, RSI) based on the fetched data.
Database Storage: The fetched data and the calculated indicators are stored in an SQLite database.
API Endpoints: API endpoints allow users to fetch both the raw Kline data and the calculated indicators.


API Data Sources

The cryptocurrency data used in this project is fetched from the Binance API, specifically the Kline (Candlestick) data for various intervals (1 minute, 5 minutes, 1 hour, etc.). The Kline data includes open, high, low, close prices, and volume for a given time interval.


Example endpoint for fetching 1-hour Kline data for BTC/USDT: 

https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h
by changing symbol and interval we can get different data. More about this you can read on the following page:
https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/Kline-Candlestick-Data
