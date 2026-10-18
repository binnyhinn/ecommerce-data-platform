import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import psycopg2
import streamlit as st

from src.config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB,
)

st.set_page_config(page_title="E-Commerce Live Dashboard", layout="wide")
st.title("Real-Time E-Commerce Dashboard")


def query(sql):
    conn = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, user=POSTGRES_USER,
        password=POSTGRES_PASSWORD, dbname=POSTGRES_DB,
    )
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


totals = query("SELECT COUNT(*) AS orders, COALESCE(SUM(amount), 0)::float AS revenue FROM orders")
events = query("SELECT COUNT(*) AS n FROM raw_events")
c1, c2, c3 = st.columns(3)
c1.metric("Total events", int(events["n"][0]))
c2.metric("Total orders", int(totals["orders"][0]))
c3.metric("Total revenue", f"{float(totals['revenue'][0]):,.2f}")

st.subheader("Revenue per minute (UTC)")
rev = query("SELECT minute, revenue::float AS revenue FROM revenue_per_minute ORDER BY minute DESC LIMIT 30")
if not rev.empty:
    st.bar_chart(rev.sort_values("minute").set_index("minute"))

st.subheader("Top products by revenue")
top = query("SELECT product_id, SUM(amount)::float AS revenue, SUM(quantity)::int AS units FROM orders GROUP BY product_id ORDER BY revenue DESC")
st.dataframe(top, use_container_width=True)

st.subheader("Events by type")
types = query("SELECT event_type, COUNT(*)::int AS n FROM raw_events GROUP BY event_type")
if not types.empty:
    st.bar_chart(types.set_index("event_type"))

time.sleep(5)
st.rerun()
