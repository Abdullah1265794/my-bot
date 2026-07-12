from flask import Flask, request, jsonify
import ccxt
import sys

app = Flask(__name__)

# Binance Mock/Demo Trading Official Configuration
exchange = ccxt.binance({
    'apiKey': 'Zb2du619lvPcna82tc1qBUCDuq07jKWZq599BVWIvj3ZPO1Y2r01CnOgNaST63X5',       
    'secret': 'tLUKyc1mUGB3ks9l0g6bPjAkhuLmDmxbYt8dbRaWZ7GsqRdwZkzxLI4a0XUNI5xf',   
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True
    }
})

# CRITICAL FIX FOR REAL-ACCOUNT DEMO SWITCH:
# Real endpoint par hit marenge par internal 'testnet' header enable rakhenge
exchange.set_sandbox_mode(False)
exchange.urls['api']['fapiPublic'] = 'https://fapi.binance.com'
exchange.urls['api']['fapiPrivate'] = 'https://fapi.binance.com'
exchange.headers = {
    'X-MBX-APIKEY': exchange.apiKey
}

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    raw_symbol = data.get('symbol', 'BTCUSDT').upper()
    action = data.get('action', '').lower()        
    amount_usd = float(data.get('amount_usd', 50))  
    leverage = int(data.get('leverage', 10))       

    if '/' not in raw_symbol:
        if raw_symbol.endswith('USDT'):
            symbol = raw_symbol.replace('USDT', '/USDT')
        else:
            symbol = f"{raw_symbol}/USDT"
    else:
        symbol = raw_symbol

    try:
        # Leverage Set Karna
        try:
            exchange.set_leverage(leverage, symbol)
        except Exception as le:
            print(f"Leverage set issue: {str(le)}")

        # Price Info
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        # Calculations
        total_position_value = amount_usd * leverage
        coin_amount = total_position_value / current_price
        
        coin_amount = round(coin_amount, 3) if 'BTC' in symbol else round(coin_amount, 2)
        order_side = 'BUY' if action == 'buy' else 'SELL'
        
        # Order Request with Mock/Testnet parameter inside params
        order = exchange.create_market_order(
            symbol=symbol, 
            side=order_side, 
            amount=coin_amount,
            params={'testnet': True}  # Yeh Binance ko batayega ke Demo Futures par trade lagani hai
        )
        return jsonify({"status": "success", "order": order}), 200

    except Exception as e:
        print(f"!!! CRITICAL ERROR !!!: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
