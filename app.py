from flask import Flask, request, jsonify
import ccxt
import os
import sys
import traceback

app = Flask(__name__)

API_KEY = os.getenv('BINGX_API_KEY')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY')

exchange = ccxt.bingx({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # Perpetual Futures
        'adjustForTimeDifference': True
    }
})

# DEMO / SANDBOX MODE
exchange.set_sandbox_mode(True)

@app.route('/')
def home():
    return "BingX Demo Bot with Hedge Mode is Active!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    
    action = data.get('action', '').lower()      
    if action not in ['buy', 'sell']:
        return jsonify({"status": "error", "message": f"Invalid action '{action}'"}), 400
        
    raw_symbol = data.get('symbol', 'BTCUSDT').upper().replace('.P', '')
    
    try:
        markets = exchange.load_markets()
        
        base = raw_symbol.replace('USDT', '')
        symbol = f"{base}/USDT"
        
        if symbol not in markets:
            alternative_symbols = [m for m in markets if base in m]
            if alternative_symbols:
                symbol = alternative_symbols[0]

        amount_usd = float(data.get('amount_usd', 50))
        leverage = int(data.get('leverage', 10))

        # Set Leverage safely
        try: 
            exchange.set_leverage(leverage, symbol)
        except Exception:
            pass

        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']

        raw_amount = (amount_usd * leverage) / price
        coin_amount = float(exchange.amount_to_precision(symbol, raw_amount))

        # FIX: Side and PositionSide allocation for Hedge Mode
        if action == 'buy':
            side = 'BUY'
            position_side = 'LONG'
        else:
            side = 'SELL'
            position_side = 'SHORT'

        # HEDGE MODE REQUIRED PARAMETERS
        params = {
            'positionSide': position_side
        }

        # Order Execution
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=coin_amount,
            params=params
        )

        return jsonify({
            "status": "success", 
            "message": f"Demo Order placed on {symbol} with positionSide: {position_side}!", 
            "order_id": order.get('id')
        }), 200
        
    except Exception as e:
        print("--- BINGX SANDBOX ERROR TRACEBACK ---", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("---------------------------------------", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
