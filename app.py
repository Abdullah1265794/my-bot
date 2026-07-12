from flask import Flask, request, jsonify
import ccxt
import sys

app = Flask(__name__)

# Binance Official Fix for New Demo Trading Accounts
exchange = ccxt.binance({
    'apiKey': 'Zb2du619lvPcna82tc1qBUCDuq07jKWZq599BVWIvj3ZPO1Y2r01CnOgNaST63X5',       
    'secret': 'tLUKyc1mUGB3ks9l0g6bPjAkhuLmDmxbYt8dbRaWZ7GsqRdwZkzxLI4a0XUNI5xf',   
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True
    }
})

# Binance naye demo accounts ko real endpoints par testnet header ke sath chalata hai
exchange.set_sandbox_mode(False) 

# Force routing to Binance Futures Real/Demo URLs
exchange.urls['api']['fapiPublic'] = 'https://fapi.binance.com'
exchange.urls['api']['fapiPrivate'] = 'https://fapi.binance.com'

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
        try:
            exchange.set_leverage(leverage, symbol)
        except Exception as le:
            print(f"Leverage set issue (Ignored): {str(le)}")

        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        total_position_value = amount_usd * leverage
        coin_amount = total_position_value / current_price
        
        coin_amount = round(coin_amount, 3) if 'BTC' in symbol else round(coin_amount, 2)
        order_side = 'BUY' if action == 'buy' else 'SELL'
        
        order = exchange.create_market_order(symbol=symbol, side=order_side, amount=coin_amount)
        return jsonify({"status": "success", "order": order}), 200

    except Exception as e:
        print(f"!!! CRITICAL ERROR !!!: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
