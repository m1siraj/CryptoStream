import os
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from databricks import sql
from databricks.sdk.core import Config


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CryptoStream",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONFIGURATION
# ============================================================

WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")

LATEST_TABLE = os.getenv(
    "LATEST_TABLE",
    "workspace.default.crypto_dashboard_latest"
)

TRADES_TABLE = os.getenv(
    "TRADES_TABLE",
    "workspace.default.crypto_dashboard_trades"
)

GOLD_1M_TABLE = os.getenv(
    "GOLD_1M_TABLE",
    "workspace.default.crypto_gold_1m"
)


# ============================================================
# STYLING
# ============================================================

st.markdown(
    """
    <style>

    .main {
        padding-top: 1rem;
    }

    .metric-card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.25);
        background-color: rgba(128, 128, 128, 0.05);
    }

    .status {
        font-size: 14px;
        color: #00a000;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABRICKS CONNECTION
# ============================================================

@st.cache_resource
def get_connection():

    cfg = Config()

    if not WAREHOUSE_ID:
        raise RuntimeError(
            "DATABRICKS_WAREHOUSE_ID is not configured."
        )

    return sql.connect(
        server_hostname=cfg.host.replace("https://", ""),
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        credentials_provider=lambda: cfg.authenticate,
    )


# ============================================================
# QUERY FUNCTION
# ============================================================

def run_query(query):

    conn = get_connection()

    cursor = conn.cursor()

    try:
        cursor.execute(query)

        columns = [
            description[0]
            for description in cursor.description
        ]

        rows = cursor.fetchall()

        return pd.DataFrame(
            rows,
            columns=columns
        )

    finally:
        cursor.close()


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data(ttl=5)
def load_latest():

    query = f"""
        SELECT
            product_id,
            window_start,
            window_end,
            open_price,
            high_price,
            low_price,
            close_price,
            volume_btc,
            volume_usd,
            trade_count,
            buy_volume_btc,
            sell_volume_btc,
            price_change,
            price_change_pct,
            volume_imbalance
        FROM {LATEST_TABLE}
        LIMIT 10
    """

    return run_query(query)


@st.cache_data(ttl=5)
def load_price_history():

    query = f"""
        SELECT
            window_start,
            open_price,
            high_price,
            low_price,
            close_price,
            volume_btc,
            trade_count
        FROM {GOLD_1M_TABLE}
        WHERE product_id = 'BTC-USD'
        ORDER BY window_start DESC
        LIMIT 60
    """

    df = run_query(query)

    if not df.empty:
        df = df.sort_values("window_start")

    return df


@st.cache_data(ttl=5)
def load_recent_trades():

    query = f"""
        SELECT
            product_id,
            trade_id,
            price,
            size,
            side,
            event_time,
            notional_usd
        FROM {TRADES_TABLE}
        WHERE product_id = 'BTC-USD'
        ORDER BY event_time DESC
        LIMIT 25
    """

    return run_query(query)


# ============================================================
# HEADER
# ============================================================

st.title("₿ CryptoStream")

st.markdown(
    """
    **Near-real-time cryptocurrency market monitor**

    Streaming market trades → Bronze → Silver → Gold → Dashboard
    """
)

st.divider()


# ============================================================
# LOAD DATA
# ============================================================

try:

    latest_df = load_latest()
    history_df = load_price_history()
    trades_df = load_recent_trades()

except Exception as e:

    st.error(
        f"Unable to load market data: {e}"
    )

    st.stop()


if latest_df.empty:

    st.warning(
        "No market data is currently available."
    )

    st.stop()


latest = latest_df.iloc[0]


# ============================================================
# MARKET STATUS
# ============================================================

col_status_1, col_status_2 = st.columns([3, 1])

with col_status_1:

    st.markdown(
        "🟢 **Market stream active**"
    )

with col_status_2:

    st.caption(
        f"Last window: {latest['window_start']}"
    )


# ============================================================
# TOP METRICS
# ============================================================

st.subheader("BTC-USD Market")

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "BTC Price",
        f"${latest['close_price']:,.2f}",
        f"{latest['price_change_pct']:+.4f}%"
    )

with c2:

    st.metric(
        "1-Min High",
        f"${latest['high_price']:,.2f}"
    )

with c3:

    st.metric(
        "1-Min Low",
        f"${latest['low_price']:,.2f}"
    )

with c4:

    st.metric(
        "Trades",
        f"{int(latest['trade_count']):,}"
    )


# ============================================================
# VOLUME METRICS
# ============================================================

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "BTC Volume",
        f"{latest['volume_btc']:,.6f}"
    )

with c2:

    st.metric(
        "USD Volume",
        f"${latest['volume_usd']:,.2f}"
    )

with c3:

    st.metric(
        "Buy Volume",
        f"{latest['buy_volume_btc']:,.6f} BTC"
    )

with c4:

    st.metric(
        "Sell Volume",
        f"{latest['sell_volume_btc']:,.6f} BTC"
    )


# ============================================================
# VOLUME IMBALANCE
# ============================================================

st.subheader("Market Pressure")

imbalance = latest["volume_imbalance"]

if imbalance > 0:

    pressure = "BUY PRESSURE"

elif imbalance < 0:

    pressure = "SELL PRESSURE"

else:

    pressure = "BALANCED"


p1, p2 = st.columns(2)

with p1:

    st.metric(
        "Volume Imbalance",
        f"{imbalance:+.6f} BTC"
    )

with p2:

    st.metric(
        "Market Pressure",
        pressure
    )


# ============================================================
# PRICE CHART
# ============================================================

st.subheader("BTC Price — Last 60 Minutes")

if not history_df.empty:

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=history_df["window_start"],
            y=history_df["close_price"],
            mode="lines",
            name="BTC Price",
            hovertemplate=(
                "%{x}<br>"
                "$%{y:,.2f}"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        height=450,
        xaxis_title="Time",
        yaxis_title="BTC Price (USD)",
        hovermode="x unified",
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.info(
        "Not enough 1-minute data to display the price chart."
    )


# ============================================================
# VOLUME CHART
# ============================================================

st.subheader("Trading Volume")

if not history_df.empty:

    volume_fig = go.Figure()

    volume_fig.add_trace(
        go.Bar(
            x=history_df["window_start"],
            y=history_df["volume_btc"],
            name="BTC Volume"
        )
    )

    volume_fig.update_layout(
        height=300,
        xaxis_title="Time",
        yaxis_title="BTC Volume",
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        )
    )

    st.plotly_chart(
        volume_fig,
        use_container_width=True
    )


# ============================================================
# RECENT TRADES
# ============================================================

st.subheader("Recent Trades")

if not trades_df.empty:

    display_df = trades_df.copy()

    display_df["price"] = display_df[
        "price"
    ].map(
        lambda x: f"${x:,.2f}"
    )

    display_df["size"] = display_df[
        "size"
    ].map(
        lambda x: f"{x:.8f}"
    )

    display_df["notional_usd"] = display_df[
        "notional_usd"
    ].map(
        lambda x: f"${x:,.2f}"
    )

    display_df = display_df.rename(
        columns={
            "product_id": "Product",
            "trade_id": "Trade ID",
            "price": "Price",
            "size": "BTC Size",
            "side": "Side",
            "event_time": "Event Time",
            "notional_usd": "USD Value"
        }
    )

    st.dataframe(
        display_df[
            [
                "Product",
                "Trade ID",
                "Price",
                "BTC Size",
                "Side",
                "Event Time",
                "USD Value"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No recent trades available."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "CryptoStream • Databricks + Delta Lake + Structured Streaming + Coinbase"
)

st.caption(
    "Dashboard refreshes automatically every 5 seconds."
)


# ============================================================
# AUTO REFRESH
# ============================================================

time.sleep(5)

st.rerun()

