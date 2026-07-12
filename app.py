from flask import Flask, request, jsonify
import ccxt
import sys
import os

app = Flask(__name__)

# Environment variables se keys uthayenge (Hardcode nahi karenge)
API_KEY = os.getenv('BINANCE_API_KEY', 'Zb2du619lvPcna82tc1qBUCDuq07jKWZq599BVWIvj3ZPO1Y2r01CnOgNaST63X5')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', 'tLUKyc1mUGB3ks9l0g6bPjAkhuLmDmxbYt8dbRaWZ7GsqRdwZkzxLI4a0XUNI5xf')

# CCXT Binance Setup
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True
    }
})

# DEMO TRADING ENABLING:
# CCXT auto-configures the correct endpoints when sandbox mode is True
exchange.set_sandbox_mode(True)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    print(f"Payload Received: {data}")  # Logs check karne ke liye

    raw_symbol = data.get('symbol', 'BTCUSDT').upper()
    action = data.get('action', '').lower()        
    amount_usd = float(data.get('amount_usd', 50))  
    leverage = int(data.get('leverage', 10))       

    # Symbol Conversion (e.g., BTCUSDT ya BTCUSDT.P -> BTC/USDT)
    clean_symbol = raw_symbol.replace('.P', '')
    if '/' not in clean_symbol:
        if clean_symbol.endswith('USDT'):
            symbol = clean_symbol.replace('USDT', '/USDT')
        else:
            symbol = f"{clean_symbol}/USDT"
    else:
        symbol = clean_symbol

    try:
        # 1. Set Leverage
        try:
            exchange.set_leverage(leverage, symbol)
        except Exception as le:
            print(f"Leverage set notice (might already be set): {str(le)}")

        # 2. Fetch Live Price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        # 3. Calculate Position Size
        total_position_value = amount_usd * leverage
        coin_amount = total_position_value / current_price
        
        # Safe rounding based on standard coin step sizes
        if 'BTC' in symbol:
            coin_amount = round(coin_amount, 3)
        elif 'ETH' in symbol:
            coin_amount = round(coin_amount, 3)
        else:
            coin_amount = round(coin_amount, 2)

        order_side = 'BUY' if action == 'buy' else 'SELL'
        
        # 4. Execute Order on Demo Network
        order = exchange.create_market_order(
            symbol=symbol, 
            side=order_side, 
            amount=coin_amount
        )
        
        return jsonify({"status": "success", "order": order}), 200

    except Exception as e:
        print(f"!!! CRITICAL ERROR !!!: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
