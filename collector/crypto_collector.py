import json
import os
import time
from datetime import datetime, timezone

import websocket


BINANCE_WS_URL = (
    "wss://stream.binance.com:9443/ws/btcusdt@aggTrade"
)


def on_message(ws, message):
    event = json.loads(message)

    print(
        f"BTCUSDT | "
        f"price={event['p']} | "
        f"quantity={event['q']} | "
        f"trade_id={event['a']}"
    )


def on_error(ws, error):
    print(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    print(
        f"WebSocket closed: "
        f"code={close_status_code}, "
        f"message={close_msg}"
    )


def on_open(ws):
    print("Connected to Binance WebSocket.")
    print("Listening for BTCUSDT aggregate trades...")


while True:

    try:
        ws = websocket.WebSocketApp(
            BINANCE_WS_URL,
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