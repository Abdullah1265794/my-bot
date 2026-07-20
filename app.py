import os
import sys
from flask import Flask, request, jsonify
import ccxt

app = Flask(__name__)

# BingX API Configuration (Apni API keys Render ke Environment Variables mein lazmi dalein)
API_KEY = os.getenv('BINGX_API_KEY', 'YOUR_API_KEY')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY', 'YOUR_SECRET_KEY')

# BingX Exchange Setup (Perpetual Futures/Swap Mode)
exchange = ccxt.bingx({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'options': {
        'defaultType': 'swap',  # Perpetual Futures trade ke liye zaroori ha
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

        # 1. TradingView Payload se data extract karna
        symbol = data.get('symbol', 'BNBUSDT')          # E.g., BNBUSDT
        action = data.get('action').lower()             # buy ya sell
        amount_usd = float(data.get('amount_usd', 50))  # Margin USD mein
        leverage = int(data.get('leverage', 50))        # Leverage value

        # Direct ROI Input (E.g., tp: 100, sl: 100)
        roi_tp = float(data.get('tp', 100))
        roi_sl = float(data.get('sl', 100))

        # CCXT ke liye symbol format convert karna (BNBUSDT -> BNB/USDT:USDT)
        ccxt_symbol = f"{symbol[:3]}/{symbol[3:]}:{symbol[3:]}"

        # 2. SET LEVERAGE SAFELY FOR BINGX FUTURES
        try: 
            exchange.set_leverage(leverage, ccxt_symbol, params={'side': 'BOTH'})
        except Exception as leverage_error:
            print(f"Leverage Set Warning: {leverage_error}", file=sys.stderr)
            try:
                position_risk = exchange.fetch_position_risk([ccxt_symbol])
                if position_risk:
                    leverage = int(position_risk[0].get('leverage', leverage))
            except Exception:
                pass

        # Market price fetch karna targets calculate karne ke liye
        ticker = exchange.fetch_ticker(ccxt_symbol)
        price = float(ticker['last'])

        # 3. Volume Calculation (Margin * Leverage / Price)
        raw_amount = (amount_usd * leverage) / price
        coin_amount = float(exchange.amount_to_precision(ccxt_symbol, raw_amount))

        # 4. Side and PositionSide allocation for Hedge Mode
        if action == 'buy':
            side = 'BUY'
            position_side = 'LONG'
        else:
            side = 'SELL'
            position_side = 'SHORT'

        # 5. ROI Formula: Price Change % = ROI % / Leverage
        tp_price_change = roi_tp / leverage
        sl_price_change = roi_sl / leverage

        # Exact SL and TP prices calculate karna (Jaisa exchange screen par hota ha)
        if position_side == 'LONG':
            tp_price = price * (1 + (tp_price_change / 100))
            sl_price = price * (1 - (sl_price_change / 100))
        else:  # SHORT
            tp_price = price * (1 - (tp_price_change / 100))
            sl_price = price * (1 + (sl_price_change / 100))

        # Price ko precision ke mutabiq round karna
        tp_price = float(exchange.price_to_precision(ccxt_symbol, tp_price))
        sl_price = float(exchange.price_to_precision(ccxt_symbol, sl_price))

        print(f"Final Execution -> Side: {side}, Size: {coin_amount}, TP: {tp_price}, SL: {sl_price}")

        # 6. HEDGE MODE & SL/TP PARAMETERS ATTACHMENT
        params = {
            'positionSide': position_side,
            'stopLoss': {
                'triggerPrice': sl_price,
                'type': 'market'   # SL hit hotay hi market par trade close
            },
            'takeProfit': {
                'triggerPrice': tp_price,
                'type': 'market'   # TP hit hotay hi market par trade close
            }
        }

        # 7. Final Order Execution
        order = exchange.create_order(
            symbol=ccxt_symbol,
            type='market',
            side=side,
            amount=coin_amount,
            params=params
        )

        return jsonify({
            "status": "success",
            "message": "Order placed successfully with SL/TP",
            "order_id": order.get('id')
        }), 200

    except Exception as e:
        print("Critical Error executing order:", str(e), file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
