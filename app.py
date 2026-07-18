from flask import Flask, request, jsonify
import ccxt
import os
import sys
import traceback

app = Flask(__name__)

# Render Environment Variables
API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise Exception("BINGX_API_KEY or BINGX_SECRET_KEY not found in Render Environment Variables")

# BingX Futures
exchange = ccxt.bingx({
    "apiKey": API_KEY,
    "secret": SECRET_KEY,
    "enableRateLimit": True,
    "options": {
        "defaultType": "swap",
        "adjustForTimeDifference": True
    }
})

@app.route("/")
def home():
    return "BingX Bot Running Successfully!", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)

        action = str(data.get("action", "")).lower()

        if action not in ["buy", "sell"]:
            return jsonify({
                "status": "error",
                "message": "Action must be buy or sell"
            }), 400

        raw_symbol = str(data.get("symbol", "BTCUSDT")).upper().replace(".P", "")

        if "/" not in raw_symbol:
            symbol = raw_symbol.replace("USDT", "") + "/USDT"
        else:
            symbol = raw_symbol

        amount_usd = float(data.get("amount_usd", 50))
        leverage = int(data.get("leverage", 10))

        exchange.load_markets()

        try:
            exchange.set_leverage(leverage, symbol)
        except Exception as e:
            print("Leverage Warning:", e)

        ticker = exchange.fetch_ticker(symbol)
        price = ticker["last"]

        amount = (amount_usd * leverage) / price
        amount = float(exchange.amount_to_precision(symbol, amount))

        order = exchange.create_order(
            symbol=symbol,
            type="market",
            side=action,
            amount=amount
        )

        return jsonify({
            "status": "success",
            "order": order
        }), 200

    except Exception as e:
        print("========== ERROR ==========", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("===========================", file=sys.stderr)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
