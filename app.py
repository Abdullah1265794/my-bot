from flask import Flask, request, jsonify
import ccxt
import os
import sys
import traceback

app = Flask(__name__)

# SECURITY SETUP
# Render ke Environment Variables se keys load hongi
API_KEY = os.getenv('BINGX_API_KEY')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY')

# BINGX CONNECTION SETUP
exchange = ccxt.bingx({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # BingX Linear Perpetual Futures ke liye
        'adjustForTimeDifference': True
    }
})

# DEMO / SANDBOX MODE ENABLED
# Yeh line aapki same API key ko VST (Virtual Account) par redirect kar degi
exchange.set_sandbox_mode(True)

@app.route('/')
def home():
    return "BingX Demo Bot is Active!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    
    action = data.get('action', '').lower()      
    if action not in ['buy', 'sell']:
        return jsonify({"status": "error", "message": f"Invalid action '{action}'. Must be 'buy' or 'sell'."}), 400
        
    # Currency formatting for BingX Futures (e.g., BTC/USDT)
    raw_symbol = data.get('symbol', 'BTCUSDT').upper().replace('.P', '')
    symbol = raw_symbol if '/' in raw_symbol else f"{raw_symbol.replace('USDT', '')}/USDT"
    
    amount_usd = float(data.get('amount_usd', 50))
    leverage = int(data.get('leverage', 10))

    try:
        # Load exchange markets
        exchange.load_markets()

        # Set Leverage safely
        try: 
            exchange.set_leverage(leverage, symbol)
        except Exception:
            pass

        # Get current entry price from Demo Market
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']

        # Calculate exact contract/coin units
        raw_amount = (amount_usd * leverage) / price
        coin_amount = float(exchange.amount_to_precision(symbol, raw_amount))

        side = 'BUY' if action == 'buy' else 'SELL'

        # Params khali rakhe hain taake simple order testing bypass ho sake
        params = {}

        # Market Entry Execution (On Demo Account)
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=coin_amount,
            params=params
        )

        return jsonify({"status": "success", "message": "Demo Order processed successfully!", "order_id": order.get('id')}), 200
        
    except Exception as e:
        print("--- BINGX DEMO EXECUTION ERROR TRACEBACK ---", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("--------------------------------------------", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
