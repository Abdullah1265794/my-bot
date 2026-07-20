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
    return "BingX Trading Bot is Running Successfully!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload received"}), 400

        print("Received Signal Data:", data)

        symbol = data.get('symbol', 'BNBUSDT')          
        action = data.get('action').lower()             
        amount_usd = float(data.get('amount_usd', 50))  
        leverage = int(data.get('leverage', 50))        

        roi_tp = float(data.get('tp', 100))
        roi_sl = float(data.get('sl', 100))

        ccxt_symbol = f"{symbol[:3]}/{symbol[3:]}:{symbol[3:]}"
        leverage_symbol = f"{symbol[:3]}/{symbol[3:]}"

        # 1. SET LEVERAGE (FIXED: Uses 'BOTH' as required by logs)
        try: 
            exchange.set_leverage(leverage, leverage_symbol, params={'side': 'BOTH'})
        except Exception as leverage_error:
            print(f"Leverage Set Warning: {leverage_error}", file=sys.stderr)

        ticker = exchange.fetch_ticker(ccxt_symbol)
        price = float(ticker['last'])

        raw_amount = (amount_usd * leverage) / price
        coin_amount = float(exchange.amount_to_precision(ccxt_symbol, raw_amount))

        if action == 'buy':
            side = 'BUY'
            position_side = 'LONG'
            close_side = 'SELL'
        else:
            side = 'SELL'
            position_side = 'SHORT'
            close_side = 'BUY'

        # ROI to Price conversion logic
        tp_price_change = roi_tp / leverage
        sl_price_change = roi_sl / leverage

        if position_side == 'LONG':
            tp_price = price * (1 + (tp_price_change / 100))
            sl_price = price * (1 - (sl_price_change / 100))
        else:
            tp_price = price * (1 - (tp_price_change / 100))
            sl_price = price * (1 + (sl_price_change / 100))

        tp_price = float(exchange.price_to_precision(ccxt_symbol, tp_price))
        sl_price = float(exchange.price_to_precision(ccxt_symbol, sl_price))

        # 2. PLACE CLEAN MARKET POSITION ORDER
        order_params = {'positionSide': position_side}
        main_order = exchange.create_order(
            symbol=ccxt_symbol,
            type='market',
            side=side,
            amount=coin_amount,
            params=order_params
        )
        print(f"Main Position Opened successfully: {main_order.get('id')}")

        # 3. PLACE SEPARATE TAKE PROFIT ORDER WITH REDUCE-ONLY
        try:
            tp_params = {
                'positionSide': position_side,
                'stopPrice': tp_price,
                'reduceOnly': True
            }
            exchange.create_order(
                symbol=ccxt_symbol,
                type='TAKE_PROFIT_MARKET',
                side=close_side,
                amount=coin_amount,
                params=tp_params
            )
            print(f"Separate Take Profit placed at {tp_price}")
        except Exception as tp_err:
            print(f"TP Trigger Warning: {tp_err}", file=sys.stderr)

        # 4. PLACE SEPARATE STOP LOSS ORDER WITH REDUCE-ONLY
        try:
            sl_params = {
                'positionSide': position_side,
                'stopPrice': sl_price,
                'reduceOnly': True
            }
            exchange.create_order(
                symbol=ccxt_symbol,
                type='STOP_LOSS_MARKET',
                side=close_side,
                amount=coin_amount,
                params=sl_params
            )
            print(f"Separate Stop Loss placed at {sl_price}")
        except Exception as sl_err:
            print(f"SL Trigger Warning: {sl_err}", file=sys.stderr)

        return jsonify({
            "status": "success",
            "message": "Order executed and independent SL/TP triggers set.",
            "order_id": main_order.get('id')
        }), 200

    except Exception as e:
        print("Critical Error executing order:", str(e), file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
