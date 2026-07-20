# SET LEVERAGE SAFELY FOR BINGX FUTURES
        try: 
            # BingX perpetual futures ke liye leverage params ke sath set hoti hai
            exchange.set_leverage(leverage, symbol, params={'side': 'BOTH'})
        except Exception as leverage_error:
            print(f"Leverage Set Warning: {leverage_error}", file=sys.stderr)
            # Agar exchange par leverage change nahi ho saki, toh hum default select shuda leverage (20x) ko fetch kar lete hain
            try:
                position_risk = exchange.fetch_position_risk([symbol])
                if position_risk:
                    leverage = int(position_risk[0].get('leverage', leverage))
            except Exception:
                pass

        ticker = exchange.fetch_ticker(symbol)
        price = float(ticker['last'])

        # Volume Calculation based on verified leverage
        raw_amount = (amount_usd * leverage) / price
        coin_amount = float(exchange.amount_to_precision(symbol, raw_amount))

        # FIX: Side and PositionSide allocation for Hedge Mode
        if action == 'buy':
            side = 'BUY'
            position_side = 'LONG'
        else:
            side = 'SELL'
            position_side = 'SHORT'

        # ==========================================
        # NEW FIX: ROI LOGIC & SL/TP TRIGGER CALCULATION
        # ==========================================
        # TradingView JSON payload se direct ROI % lena (e.g., tp: 100, sl: 100)
        roi_tp = float(data.get('tp', 100))
        roi_sl = float(data.get('sl', 100))

        # Formula: Price Change % = ROI % / Leverage
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
        tp_price = float(exchange.price_to_precision(symbol, tp_price))
        sl_price = float(exchange.price_to_precision(symbol, sl_price))

        # HEDGE MODE REQUIRED PARAMETERS ATTACHED WITH SL/TP
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
        # ==========================================
