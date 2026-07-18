from flask import Flask, request, jsonify
import ccxt
import os
import sys
import traceback

app = Flask(__name__)

# SECURITY FIX: Hardcoded keys ko remove kar diya hai. 
# Ab ye Render ke Environment Variables se automatically keys uthaega.
API_KEY = os.getenv('BINGX_API_KEY')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY')

# BingX Connection Setup
exchange = ccxt.bingx({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap'  # Futures/Swap ke liye
    }
})

@app.route('/')
def home():
    return "BingX Bot is Active!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    
    # 1. Action Validation (Agar 'buy' ya 'sell' ke ilawa kuch aya to error handle hoga)
    action = data.get('action', '').lower()      
    if action not in ['buy', 'sell']:
        return jsonify({"status": "error", "message": f"Invalid action '{action}'. Must be 'buy' or 'sell'."}), 400
        
    # Currency formatting for BingX
    raw_symbol = data.get('symbol', 'BTCUSDT').upper().replace('.P', '')
    symbol = raw_symbol if '/' in raw_symbol else f"{raw_symbol.replace('USDT', '')}/USDT"
    
    amount_usd = float(data.get('amount_usd', 50))
    leverage = int(data.get('leverage', 10))

    try:
        # Markets load karna zaroori hai precision check karne ke liye
        exchange.load_markets()

        # Set Leverage safely
        try: 
            exchange.set_leverage(leverage, symbol)
        except Exception:
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

        # Bracket parameters for Take Profit & Stop Loss
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

        return jsonify({"status": "success", "message": "Order processed successfully!", "order_id": order.get('id')}), 200
        
    except Exception as e:
        # BETTER LOGGING: Ab Render logs me exact line aur error poora nazar aayega
        print("--- BINGX EXECUTION ERROR TRACEBACK ---", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("---------------------------------------", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
