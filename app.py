from flask import Flask, request, jsonify
import ccxt

app = Flask(__name__)

# Binance Demo Connection
exchange = ccxt.binance({
    'apiKey': 'TuDUSjBSxDCULlcDu8DBmAhcwJfYQRDqGdG6E74Mo8Vja13glFAkiXUZiUDIaZvP',       
    'secret': '9VvaAKUhYVM8h8aVuWz7yF0CnLs6oRq5cn4F9kmHSa8Uj48YwNDXSFUgAfMpiFJf',   
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})
exchange.set_sandbox_mode(True) 

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    # TradingView message se values uthana
    symbol = data.get('symbol', 'BTCUSDT')
    action = data.get('action', '').lower()        # buy ya sell
    amount_usd = float(data.get('amount_usd', 50))  # Jeb se lagne wale dollar ($50)
    leverage = int(data.get('leverage', 10))       # Leverage (10x)

    try:
        # 1. Leverage Set Karna
        try:
            exchange.set_leverage(leverage, symbol)
        except Exception as lev_err:
            print(f"Leverage error (ignored if already set): {lev_err}")

        # 2. Market Price Fetch Karna
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        # NORMAL TRADING CALCULATION:
        # (Jeb ke dollar * Leverage) = Total Trade Value. Phir usko price se divide kar ke coin quantity nikalna.
        total_position_value = amount_usd * leverage
        coin_amount = total_position_value / current_price
        
        # Har coin ke market precision ke mutabiq automatically round karna
        market = exchange.market(symbol)
        coin_amount = exchange.amount_to_precision(symbol, coin_amount)

        order_side = 'BUY' if action == 'buy' else 'SELL'
        
        # 3. Order Place Karna
        order = exchange.create_market_order(symbol=symbol, side=order_side, amount=float(coin_amount))
        return jsonify({"status": "success", "order": order}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
