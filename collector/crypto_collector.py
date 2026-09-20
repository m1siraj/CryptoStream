import json
import time
from datetime import datetime, timezone

import websocket


COINBASE_WS_URL = "wss://advanced-trade-ws.coinbase.com"

# Keep trades in memory briefly, then write them as one batch.
BATCH_SIZE = 100


trade_buffer = []


def write_batch():
    global trade_buffer

    if not trade_buffer:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")

    filename = f"trades_{timestamp}.ndjson"

    with open(filename, "w") as f:
        for trade in trade_buffer:
            f.write(json.dumps(trade) + "\n")

    print(f"Wrote {len(trade_buffer)} trades to {filename}")

    trade_buffer = []


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
    global trade_buffer

    event = json.loads(message)

    if event.get("channel") != "market_trades":
        return

    for event_group in event.get("events", []):

        for trade in event_group.get("trades", []):

            record = {
                "product_id": trade["product_id"],
                "trade_id": trade["trade_id"],
                "price": float(trade["price"]),
                "size": float(trade["size"]),
                "time": trade["time"],
                "side": trade["side"],
                "ingested_at": datetime.now(timezone.utc).isoformat()
            }

            trade_buffer.append(record)

            if len(trade_buffer) >= BATCH_SIZE:
                write_batch()


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

    write_batch()

    print("Reconnecting in 5 seconds...")

    time.sleep(5)