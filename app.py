from flask import Flask, request, jsonify
import ccxt
import os

app = Flask(__name__)

# BingX Keys Jo Aapne Share Kin
API_KEY = os.getenv('BINGX_API_KEY', 'IUjJvoTXTjipuk3u5fh7lEoDPwpXhKfWAW0DJ0CAiXnA9jxkv78u6fiwC3vm3zyFciFCHgEy0x6tM6xGbmpjg')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY', 'lbsqpPVBDndTF841QJgLYuY4IaybjnPH5K0UBS2id81WanPjDS1rYYA7v2ol6SJXW5yQUlHoOKc5hGkj3l7A')

# BingX Exchange Setup with Sandbox (Demo/VST) active
exchange = ccxt.bingx({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap',  # Perpetual Futures ko BingX par swap bolte hain
    }
})
exchange.set_sandbox_mode(True)  # Strictly routes all trades to Virtual USDT (Demo Account)

# Startup par markets load karein taake webhook fast chale
try:
    exchange.load_markets()
except Exception as e:
    print(f"Initial market load failed: {str(e)}")

# UptimeRobot / Render Health Check
@app.route('/')
def home():
    return "BingX Bot is Active!", 200

# TradingView Webhook Route
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    
    # Format symbol according to BingX standards (e.g., BTC/USDT)
    raw_symbol = data.get('symbol', 'BTCUSDT').upper().replace('.P', '')
    symbol = raw_symbol if '/' in raw_symbol else f"{raw_symbol.replace('USDT', '')}/USDT"
    
    action = data.get('action', '').lower()      # 'buy' ya 'sell'
    amount_usd = float(data.get('amount_usd', 50))
    leverage = int(data.get('leverage', 10))

    try:
        # 1. Set Leverage
        try: 
            exchange.set_leverage(leverage, symbol)
        except Exception as lev_err:
            print(f"Leverage setting error: {str(lev_err)}")

        # 2. Market Execution Parameters
        side = 'BUY' if action == 'buy' else 'SELL'
        
        # 3. Handle TP/SL Percentages (Default 1% if not specified in signal)
        tp_pct = float(data.get('tp', 1.0))
        sl_pct = float(data.get('sl', 1.0))

        # FIXED SOLUTION: BingX bracket order parameter jo TP aur SL ko entry ke sath hi LIVE active kar deta hai
        params = {
            'takeProfit': {'triggerPrice': f"{tp_pct}%"},
            'stopLoss': {'triggerPrice': f"{sl_pct}%"}
        }

        # 4. Open Order (BingX directly handles margin in USD amount)
        order = exchange.create_market_order(
            symbol=symbol,
            side=side,
            amount=amount_usd,
            params=params
        )

        return jsonify({"status": "success", "message": "BingX trade placed and TP/SL activated successfully!"}), 200
    except Exception as e:
        print(f"Trading Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
