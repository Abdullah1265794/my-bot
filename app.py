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
        price = ticker['last']

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

        # HEDGE MODE REQUIRED PARAMETERS
        params = {
            'positionSide': position_side
        }
