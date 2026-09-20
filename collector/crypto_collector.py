import json
import time

import websocket


COINBASE_WS_URL = (
    "wss://advanced-trade-ws.coinbase.com"
)


def on_open(ws):
    print("Connected to Coinbase WebSocket.")

    subscribe_message = {
        "type": "subscribe",
        "product_ids": [
            "BTC-USD"
        ],
        "channel": "market_trades"
    }

    ws.send(json.dumps(subscribe_message))

    print("Subscribed to BTC-USD market trades.")


def on_message(ws, message):
    event = json.loads(message)

    print(json.dumps(event))


def on_error(ws, error):
    print(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    print(
        f"WebSocket closed: "
        f"code={close_status_code}, "
        f"message={close_msg}"
    )


while True:

    try:
        ws = websocket.WebSocketApp(
            COINBASE_WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        ws.run_forever(
            ping_interval=20,
            ping_timeout=10
        )

    except Exception as e:
        print(f"Connection failure: {e}")

    print("Reconnecting in 5 seconds...")
    time.sleep(5)