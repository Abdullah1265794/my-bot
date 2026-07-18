from flask import Flask, request, jsonify
import ccxt
import os
import sys

app = Flask(__name__)

API_KEY = os.getenv('BINGX_API_KEY', 'IUjJvoTXTjipuk3u5fh7lEoDPwpXhKfWAW0DJ0CAiXnA9jxkv78u6fiwC3vm3zyFciFCHgEy0x6tM6xGbmpjg')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY', 'lbsqpPVBDndTF841QJgLYuY4IaybjnPH5K0UBS2id81WanPjDS1rYYA7v2ol6SJXW5yQUlHoOKc5hGkj3l7A')

# BingX Custom Endpoint Connection
exchange = ccxt.bingx({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap'
    }
})

@app.route('/')
def home():
    return "BingX Bot is Active!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    
    # Currency formatting for BingX
    raw_symbol = data.get('symbol', 'BTCUSDT').upper().replace('.P', '')
    symbol = raw_symbol if '/' in raw_symbol else f"{raw_symbol.replace('USDT', '')}/USDT"
    
    action = data.get('action', '').lower()      
    amount_usd = float(data.get('amount_usd', 50))
    leverage = int(data.get('leverage', 10))

    try:
        exchange.load_markets()

        # Set Leverage safely
        try: 
            exchange.set_leverage(leverage, symbol)
        except Exception as lev_err:
            pass

        # Get current entry price
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']

        # Calculate exact contract/coin units
        raw_amount = (amount_usd * leverage) / price
        coin_amount = float(exchange.amount_to_precision(symbol, raw_amount))

        side = 'BUY' if action == 'buy' else 'SELL'

        # Target Percentage Calculations
        tp_pct = float(data.get('tp', 1.0)) / 100.0
        sl_pct = float(data.get('sl', 1.0)) / 100.0

        if action == 'buy':
            tp_price = price * (1 + tp_pct)
            sl_price = price * (1 - sl_pct)
        else:
            tp_price = price * (1 - tp_pct)
            sl_price = price * (1 + sl_pct)

        tp_str = exchange.price_to_precision(symbol, tp_price)
        sl_str = exchange.price_to_precision(symbol, sl_price)

        # Simplified bracket param to prevent 500 rejection
        params = {
            'stopLossPrice': float(sl_str),
            'takeProfitPrice': float(tp_str)
        }

        # Market Entry Execution
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=coin_amount,
            params=params
        )

        return jsonify({"status": "success", "message": "Order processed successfully!"}), 200
        
    except Exception as e:
        print(f"BINGX EXECUTION ERROR: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
