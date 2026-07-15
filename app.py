from flask import Flask, request, jsonify
import ccxt
import os

app = Flask(__name__)

API_KEY = os.getenv('BINANCE_API_KEY', 'Zb2du619lvPcna82tc1qBUCDuq07jKWZq599BVWIvj3ZPO1Y2r01CnOgNaST63X5')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', 'tLUKyc1mUGB3ks9l0g6bPjAkhuLmDmxbYt8dbRaWZ7GsqRdwZkzxLI4a0XUNI5xf')

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'future', 'adjustForTimeDifference': True}
})
exchange.enable_demo_trading(True)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    raw_symbol = data.get('symbol', 'BTCUSDT').upper().replace('.P', '')
    symbol = raw_symbol if '/' in raw_symbol else f"{raw_symbol.replace('USDT', '')}/USDT"
    action = data.get('action', '').lower()
    amount_usd = float(data.get('amount_usd', 50))
    leverage = int(data.get('leverage', 10))

    try:
        # Load markets for exact price/amount precision
        exchange.load_markets()

        # 1. Set Leverage
        try: exchange.set_leverage(leverage, symbol)
        except: pass

        # 2. Get Price and Calculate Size with Binance Precision
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        
        raw_amount = (amount_usd * leverage) / price
        coin_amount = float(exchange.amount_to_precision(symbol, raw_amount))

        position_side = 'LONG' if action == 'buy' else 'SHORT'
        order_side = 'BUY' if action == 'buy' else 'SELL'

        # 3. Open Market Position (Hedge Mode)
        order = exchange.create_market_order(
            symbol=symbol,
            side=order_side,
            amount=coin_amount,
            params={'positionSide': position_side}
        )

        # 4. Handle TP/SL with Binance Price Precision
        tp_pct = float(data.get('tp', 1.0)) / 100.0  
        sl_pct = float(data.get('sl', 1.0)) / 100.0  

        raw_tp = price * (1 + tp_pct) if action == 'buy' else price * (1 - tp_pct)
        raw_sl = price * (1 - sl_pct) if action == 'buy' else price * (1 + sl_pct)
        
        tp_price = float(exchange.price_to_precision(symbol, raw_tp))
        sl_price = float(exchange.price_to_precision(symbol, raw_sl))

        # Place TP/SL Orders
        opp_side = 'SELL' if action == 'buy' else 'BUY'
        
        # Take Profit (Limit Order)
        exchange.create_order(symbol, 'limit', opp_side, coin_amount, tp_price, {'positionSide': position_side, 'reduceOnly': True})
        
        # Stop Loss (Stop Market Order - Price passed as None, stopPrice in params)
        exchange.create_order(symbol, 'stop_market', opp_side, coin_amount, None, {'stopPrice': sl_price, 'positionSide': position_side, 'reduceOnly': True})

        return jsonify({"status": "success", "message": "Hedge trade and TP/SL set!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
