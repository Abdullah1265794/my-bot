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

    side = data.get('side', '').lower()
    symbol = data.get('symbol', 'BTCUSDT')
    amount = data.get('amount', 0.01)

    try:
        order_side = 'BUY' if side == 'buy' else 'SELL'
        order = exchange.create_market_order(symbol=symbol, side=order_side, amount=amount)
        return jsonify({"status": "success", "order": order}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
