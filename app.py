import requests
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, render_template
import sqlite3
from threading import Thread
import time

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('crypto_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS kline_data
                 (timestamp INTEGER PRIMARY KEY,
                  open REAL,
                  high REAL,
                  low REAL,
                  close REAL,
                  volume REAL,
                  interval TEXT)''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_interval ON kline_data(interval)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON kline_data(timestamp)')
    conn.commit()
    conn.close()

# Implement data retention policy
def cleanup_old_data():
    conn = sqlite3.connect('crypto_data.db')
    c = conn.cursor()
    # Keep only last 30 days of data
    c.execute('''DELETE FROM kline_data 
                 WHERE timestamp < (SELECT MAX(timestamp) FROM kline_data) - (30 * 24 * 60 * 60 * 1000)''')
    conn.commit()
    conn.close()

def fetch_and_store_kline_data(symbol='BTCUSDT', interval='1m'):
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': 1000
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        conn = sqlite3.connect('crypto_data.db')
        c = conn.cursor()
        
        for candle in data:
            c.execute('''INSERT OR REPLACE INTO kline_data 
                        (timestamp, open, high, low, close, volume, interval)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (int(candle[0]), float(candle[1]), float(candle[2]),
                      float(candle[3]), float(candle[4]), float(candle[5]), interval))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error fetching data: {e}")

def background_updater():
    intervals = ['1m', '5m', '1h']
    while True:
        for interval in intervals:
            fetch_and_store_kline_data(interval=interval)
        time.sleep(60)

def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    df = df.copy()
    df['ema_short'] = df['close'].ewm(span=short_window, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_window, adjust=False).mean()
    df['macd'] = df['ema_short'] - df['ema_long']
    df['macd_signal'] = df['macd'].ewm(span=signal_window, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    return df[['timestamp', 'close', 'macd', 'macd_signal', 'macd_histogram']]

def calculate_rsi(df, period=14):
    df = df.copy()
    df = df.sort_values('timestamp')
    delta = df['close'].astype(float).diff()
    
    gains = delta.copy()
    losses = delta.copy()
    
    gains[gains < 0] = 0
    losses[losses > 0] = 0
    losses = abs(losses)
    
    avg_gain = gains.rolling(window=period, min_periods=1).mean()
    avg_loss = losses.rolling(window=period, min_periods=1).mean()
    
    rs = np.where(avg_loss == 0, 100, avg_gain / avg_loss)
    rsi = 100 - (100 / (1 + rs))
    
    rsi = np.where(np.isnan(rsi), 50, rsi)
    rsi = np.clip(rsi, 0, 100)
    
    df['rsi'] = rsi
    
    result = df[['timestamp', 'close', 'rsi']].copy()
    result['rsi'] = result['rsi'].round(2)
    
    return result.to_dict(orient='records')

@app.route('/kline/<interval>', methods=['GET'])
def get_kline_endpoint(interval):
    if interval not in ['1m', '5m', '1h']:
        return jsonify({'error': 'Invalid interval'}), 400
    
    limit = request.args.get('limit')
    if limit:
        try:
            limit = int(limit)
            if limit not in [50, 100, 200]:
                return jsonify({'error': 'Invalid limit. Must be 50, 100, or 200'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid limit format. Must be an integer.'}), 400
    
    conn = sqlite3.connect('crypto_data.db')
    query = ''' 
        SELECT timestamp, open, high, low, close, volume 
        FROM kline_data 
        WHERE interval = ? 
        ORDER BY timestamp DESC
    '''
    
    if limit:
        query += f' LIMIT {limit}'
    
    df = pd.read_sql_query(query, conn, params=(interval,))
    conn.close()
    
    result = df[['timestamp', 'open', 'high', 'low', 'close']].to_dict(orient='records')
    return jsonify(result)

@app.route('/indicators/macd/<interval>', methods=['GET'])
def get_macd_endpoint(interval):
    if interval not in ['1m', '5m', '1h']:
        return jsonify({'error': 'Invalid interval'}), 400
    
    limit = request.args.get('limit')
    if limit:
        try:
            limit = int(limit)
            if limit not in [50, 100, 200]:
                return jsonify({'error': 'Invalid limit. Must be 50, 100, or 200'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid limit format. Must be an integer.'}), 400
    
    conn = sqlite3.connect('crypto_data.db')
    extra_data = 26
    query = ''' 
        SELECT timestamp, close 
        FROM kline_data 
        WHERE interval = ? 
        ORDER BY timestamp DESC
    '''
    
    if limit:
        query += f' LIMIT {limit + extra_data}'
    
    df = pd.read_sql_query(query, conn, params=(interval,))
    conn.close()
    
    if len(df) < 26:
        return jsonify({'error': 'Insufficient data for MACD calculation'}), 400
    
    macd_df = calculate_macd(df)
    if limit:
        macd_df = macd_df.head(limit)
    
    return jsonify(macd_df.to_dict(orient='records'))

@app.route('/indicators/rsi/<interval>', methods=['GET'])
def get_rsi_endpoint(interval):
    if interval not in ['1m', '5m', '1h']:
        return jsonify({'error': 'Invalid interval'}), 400
    
    limit = request.args.get('limit')
    if limit:
        try:
            limit = int(limit)
            if limit not in [50, 100, 200]:
                return jsonify({'error': 'Invalid limit. Must be 50, 100, or 200'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid limit format. Must be an integer.'}), 400
    
    try:
        conn = sqlite3.connect('crypto_data.db')
        extra_data = 14
        query = ''' 
            SELECT timestamp, close 
            FROM kline_data 
            WHERE interval = ? 
            ORDER BY timestamp DESC
        '''
        
        if limit:
            query += f' LIMIT {limit + extra_data}'
        
        df = pd.read_sql_query(query, conn, params=(interval,))
        conn.close()
        
        if len(df) < 14:
            return jsonify({'error': 'Insufficient data for RSI calculation'}), 400
        
        rsi_data = calculate_rsi(df, period=14)
        
        if limit:
            rsi_data = rsi_data[:limit]
        
        return jsonify(rsi_data)
        
    except Exception as e:
        print(f"RSI calculation error: {str(e)}")
        return jsonify({'error': 'Error calculating RSI'}), 500

@app.route('/')
def chart():
    return render_template('index.html')

if __name__ == '__main__':
    init_db()
    updater_thread = Thread(target=background_updater, daemon=True)
    updater_thread.start()
    app.run(debug=True)
