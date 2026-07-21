import os
import sys
from flask import Flask, request, jsonify
import ccxt

app = Flask(__name__)

API_KEY = os.getenv('BINGX_API_KEY', 'YOUR_API_KEY')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY', 'YOUR_SECRET_KEY')

exchange = ccxt.bingx({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'options': {
        'defaultType': 'swap',
    },
    'enableRateLimit': True
})

@app.route('/')
def home():
    return "BingX Bot is Running Successfully!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload received"}), 400

        print("Received Signal Data:", data)

        symbol = data.get('symbol', 'ETHUSDT')          
        action = data.get('action').lower()             
        amount_usd = float(data.get('amount_usd', 10))   # Set safe default USDT margin
        leverage = int(data.get('leverage', 20))         
        
        # SL and TP percentage options (Optional from JSON webhook payload)
        sl_pct = float(data.get('sl_pct', 0.01))  # Default 1% Stop Loss
        tp_pct = float(data.get('tp_pct', 0.01))  # Default 1% Take Profit

        # Dynamic symbol parsing
        clean_symbol = symbol.replace('.P', '').replace('USDT', '')
        ccxt_symbol = f"{clean_symbol}/USDT:USDT"
        leverage_symbol = f"{clean_symbol}/USDT"

        if action == 'buy':
            side = 'BUY'
            position_side = 'LONG'
        else:
            side = 'SELL'
            position_side = 'SHORT'

        # 1. SET LEVERAGE SAFELY
        try: 
            exchange.set_leverage(leverage, leverage_symbol, params={'side': position_side})
        except Exception as leverage_error:
            print(f"Leverage Set Warning: {leverage_error}", file=sys.stderr)

        # 2. FETCH CURRENT PRICE & CALCULATE QUANTITY
        ticker = exchange.fetch_ticker(ccxt_symbol)
        price = float(ticker['last'])

        # Calculate coin amount based on allocated USD margin
        raw_amount = (amount_usd * leverage) / price
        coin_amount = float(exchange.amount_to_precision(ccxt_symbol, raw_amount))

        # 3. CALCULATE AUTO TP & SL PRICES
        if position_side == 'LONG':
            stop_loss_price = price * (1 - sl_pct)
            take_profit_price = price * (1 + tp_pct)
        else:
            stop_loss_price = price * (1 + sl_pct)
            take_profit_price = price * (1 - tp_pct)

        stop_loss_price = float(exchange.price_to_precision(ccxt_symbol, stop_loss_price))
        take_profit_price = float(exchange.price_to_precision(ccxt_symbol, take_profit_price))

        # 4. EXECUTE ORDER WITH AUTOMATIC TP/SL
        params = {
            'positionSide': position_side,
            'stopLoss': {
                'triggerPrice': stop_loss_price,
                'type': 'market'
            },
            'takeProfit': {
                'triggerPrice': take_profit_price,
                'type': 'market'
            }
        }

        order = exchange.create_order(
            symbol=ccxt_symbol,
            type='market',
            side=side,
            amount=coin_amount,
            params=params
        )

        return jsonify({
            "status": "success",
            "message": "Order with Auto SL/TP executed successfully!",
            "order_id": order.get('id')
        }), 200

    except Exception as e:
        print("Critical Error executing order:", str(e), file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
