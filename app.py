from flask import Flask, request, jsonify
import ccxt
import sys

app = Flask(__name__)

# Binance Demo Connection (Nayi Keys Ke Saath)
exchange = ccxt.binance({
    'apiKey': 'Zb2du619lvPcna82tc1qBUCDuq07jKWZq599BVWIvj3ZPO1Y2r01CnOgNaST63X5',       
    'secret': 'tLUKyc1mUGB3ks9l0g6bPjAkhuLmDmxbYt8dbRaWZ7GsqRdwZkzxLI4a0XUNI5xf',   
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
    'urls': {
        'api': {
            'fapiPublic': 'https://fapi.binancefuture.com',
            'fapiPrivate': 'https://fapi.binancefuture.com',
        }
    }
})

# Naye Demo network ke liye sandbox mode False rahega
exchange.set_sandbox_mode(False) 

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    # TradingView se data lena
    raw_symbol = data.get('symbol', 'BTCUSDT').upper()
    action = data.get('action', '').lower()        
    amount_usd = float(data.get('amount_usd', 50))  
    leverage = int(data.get('leverage', 10))       

    # AUTOMATIC SYMBOL FIX (ETHUSDT -> ETH/USDT)
    if '/' not in raw_symbol:
        if raw_symbol.endswith('USDT'):
            symbol = raw_symbol.replace('USDT', '/USDT')
        else:
            symbol = f"{raw_symbol}/USDT"
    else:
        symbol = raw_symbol

    try:
        # 1. Leverage Set Karna
        try:
            exchange.set_leverage(leverage, symbol)
        except Exception as le:
            print(f"Leverage set karne mein masla (Ignored): {str(le)}")

        # 2. Market Price Fetch Karna
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        # Normal Calculation
        total_position_value = amount_usd * leverage
        coin_amount = total_position_value / current_price
        
        # Safe Rounding
        coin_amount = round(coin_amount, 3) if 'BTC' in symbol else round(coin_amount, 2)

        order_side = 'BUY' if action == 'buy' else 'SELL'
        
        # 3. Order Place Karna
        order = exchange.create_market_order(symbol=symbol, side=order_side, amount=coin_amount)
        return jsonify({"status": "success", "order": order}), 200

    except Exception as e:
        # ERROR LOGS MEIN PRINT KARNE KE LIYE
        print(f"!!! CRITICAL ERROR !!!: {str(e)}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
