"""
Streamlit dashboard — 5 pages.
Port 8501. Timezone: Asia/Jakarta.
"""
import asyncio
import os
from datetime import datetime

import asyncpg
import pandas as pd
import streamlit as st

from analytics import queries

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dropship:dropship123@db:5432/dropship")
TZ_DISPLAY = "Asia/Jakarta"


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@st.cache_resource
def get_conn_pool():
    async def _create():
        return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
    return run_async(_create())


def get_conn():
    return get_conn_pool().acquire()


# ============================================================
# Page: Overview
# ============================================================
def page_overview():
    st.title("Overview")

    async def _load():
        async with get_conn_pool().acquire() as conn:
            rev_today = await queries.get_today_revenue(conn)
            rev_yesterday = await queries.get_yesterday_revenue(conn)
            orders_today = await queries.get_today_orders(conn)
            orders_yesterday = await queries.get_yesterday_orders(conn)
            margin_7d = await queries.get_avg_margin_7d(conn)
            margin_prev = await queries.get_avg_margin_prev_7d(conn)
            critical = await queries.get_critical_stock_count(conn)
            rev_30d = await queries.get_revenue_30d(conn)
            recent = await queries.get_recent_orders(conn)
        return rev_today, rev_yesterday, orders_today, orders_yesterday, margin_7d, margin_prev, critical, rev_30d, recent

    data = run_async(_load())
    rev_today, rev_yesterday, orders_today, orders_yesterday, margin_7d, margin_prev, critical, rev_30d, recent = data

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    rev_delta = ((rev_today - rev_yesterday) / rev_yesterday * 100) if rev_yesterday > 0 else 0
    c1.metric("Revenue Hari Ini", f"Rp {rev_today:,}", f"{rev_delta:+.1f}%")
    ord_delta = orders_today - orders_yesterday
    c2.metric("Order Masuk", orders_today, f"{ord_delta:+d}")
    margin_delta = (margin_7d - margin_prev) * 100
    c3.metric("Margin Rata-rata 7d", f"{margin_7d:.1%}", f"{margin_delta:+.1f}pp")
    c4.metric("Stok Kritis", critical, delta=None, delta_color="inverse" if critical > 0 else "off")

    # Alerts
    if critical > 0:
        st.error(f"⚠️ {critical} produk stok kritis (≤5 unit)")

    # Revenue chart
    if not rev_30d.empty:
        st.subheader("Revenue & Profit 30 Hari")
        chart_df = rev_30d.set_index("date")
        st.line_chart(chart_df)

    # Recent orders
    if not recent.empty:
        st.subheader("Order Terbaru")

        def _status_color(s):
            colors = {"new": "🔵", "sent_to_supplier": "🟡", "shipped": "🟢", "delivered": "✅", "returned": "🔴"}
            return colors.get(s, s)

        recent["status"] = recent["status"].apply(_status_color)
        st.dataframe(recent, use_container_width=True, hide_index=True)


# ============================================================
# Page: Affiliate Intelligence
# ============================================================
def page_affiliate():
    st.title("Affiliate Intelligence")

    async def _load():
        async with get_conn_pool().acquire() as conn:
            leaderboard = await queries.get_niche_leaderboard(conn)
            epc_trend = await queries.get_epc_trend_14d(conn)
        return leaderboard, epc_trend

    leaderboard, epc_trend = run_async(_load())

    # KPI row from leaderboard
    if not leaderboard.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("EPC Rata-rata", f"Rp {leaderboard['epc'].mean():,.0f}")
        c2.metric("Total Klik", f"{leaderboard['total_clicks'].sum():,}")
        c3.metric("Niche Aktif", len(leaderboard))
        flip_count = len(leaderboard[leaderboard["decision"] == "flip_to_dropship"])
        c4.metric("Siap Flip", flip_count)

    # Niche leaderboard
    st.subheader("Niche Leaderboard")
    if not leaderboard.empty:
        def _color_decision(val):
            colors = {
                "flip_to_dropship": "background-color: #1b5e20; color: white",
                "scale_affiliate": "background-color: #0d47a1; color: white",
                "optimize": "background-color: #f57f17; color: black",
                "abandon": "background-color: #b71c1c; color: white",
            }
            return colors.get(val, "")

        lb = leaderboard.copy()
        lb["trend"] = lb["trend"].map({"up": "↑", "down": "↓", "flat": "→"})
        lb["cvr"] = lb["cvr"].apply(lambda x: f"{x:.2%}")
        lb["epc"] = lb["epc"].apply(lambda x: f"Rp {x:,.0f}")
        lb["aov"] = lb["aov"].apply(lambda x: f"Rp {x:,}")

        styled = lb.style.map(_color_decision, subset=["decision"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

    # EPC trend chart
    if not epc_trend.empty:
        st.subheader("EPC Trend 14 Hari")
        top_niches = epc_trend.groupby("niche")["epc"].mean().nlargest(5).index
        filtered = epc_trend[epc_trend["niche"].isin(top_niches)]
        pivot = filtered.pivot_table(index="date", columns="niche", values="epc", aggfunc="mean")
        st.line_chart(pivot)


# ============================================================
# Page: Orders & Fulfillment
# ============================================================
def page_orders():
    st.title("Orders & Fulfillment")

    async def _load():
        async with get_conn_pool().acquire() as conn:
            orders_today = await queries.get_today_orders(conn)
            active = await queries.get_active_orders(conn)
            supplier_perf = await queries.get_supplier_performance(conn)
        return orders_today, active, supplier_perf

    orders_today, active, supplier_perf = run_async(_load())

    # KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Order Hari Ini", orders_today)
    pending = len(active[active["status"] == "new"]) if not active.empty else 0
    shipping = len(active[active["status"] == "shipped"]) if not active.empty else 0
    c2.metric("Pending", pending)
    c3.metric("Dalam Pengiriman", shipping)
    c4.metric("Return Rate 30d", "—")

    # Funnel
    if not active.empty:
        st.subheader("Order Funnel")
        funnel = active["status"].value_counts()
        st.bar_chart(funnel)

    # Active orders
    if not active.empty:
        st.subheader("Order Aktif")

        def _highlight_row(row):
            if row.get("status") == "sent_to_supplier" and row.get("hours_since_created", 0) > 12 and not row.get("resi"):
                return ["background-color: #b71c1c"] * len(row)
            if row.get("status") == "new" and row.get("hours_since_created", 0) > 2:
                return ["background-color: #f57f17"] * len(row)
            return [""] * len(row)

        display = active[["id", "platform", "product", "buyer_name", "city", "courier", "status"]].copy()
        st.dataframe(display, use_container_width=True, hide_index=True)

    # Supplier performance
    if not supplier_perf.empty:
        st.subheader("Supplier Performance")
        st.dataframe(supplier_perf, use_container_width=True, hide_index=True)


# ============================================================
# Page: Products & Inventory
# ============================================================
def page_products():
    st.title("Products & Inventory")

    # Filters
    c1, c2 = st.columns(2)
    niche_filter = c1.selectbox("Niche", ["Semua"] + ["skincare", "aksesori hp", "peralatan dapur", "fashion wanita", "suplemen"])
    active_only = c2.checkbox("Aktif saja", value=True)

    niche_val = None if niche_filter == "Semua" else niche_filter

    async def _load():
        async with get_conn_pool().acquire() as conn:
            products = await queries.get_product_table(conn, niche=niche_val, active_only=active_only)
            top_rev = await queries.get_top_products_revenue(conn)
        return products, top_rev

    products, top_rev = run_async(_load())

    if not products.empty:
        def _highlight_product(row):
            styles = [""] * len(row)
            if row.get("stock", 999) <= 5:
                styles = ["background-color: #b71c1c"] * len(row)
            elif row.get("margin_pct", 100) < 20:
                styles = ["background-color: #f57f17"] * len(row)
            elif row.get("sold_30d", 0) > 50:
                styles = ["background-color: #1b5e20"] * len(row)
            return styles

        products["margin_pct"] = products["margin_pct"].apply(lambda x: f"{x:.1f}%")
        products["price"] = products["price"].apply(lambda x: f"Rp {x:,}")
        products["cogs"] = products["cogs"].apply(lambda x: f"Rp {x:,}")
        products["revenue_30d"] = products["revenue_30d"].apply(lambda x: f"Rp {x:,}")

        st.dataframe(products, use_container_width=True, hide_index=True)

    if not top_rev.empty:
        st.subheader("Top 10 Produk by Revenue (30 hari)")
        chart_df = top_rev.set_index("name")
        st.bar_chart(chart_df)


# ============================================================
# Page: CS Bot Analytics
# ============================================================
def page_cs():
    st.title("CS Bot Analytics")

    async def _load():
        async with get_conn_pool().acquire() as conn:
            stats = await queries.get_cs_stats_today(conn)
            escalations = await queries.get_escalations_recent(conn)
            intents = await queries.get_intent_distribution(conn)
        return stats, escalations, intents

    stats, escalations, intents = run_async(_load())

    # KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pesan Hari Ini", stats["total_messages"])
    c2.metric("Customer Unik", stats["unique_customers"])
    c3.metric("Resolution Rate", f"{stats['resolution_rate']}%")
    c4.metric("Eskalasi", stats["escalated"])

    # Intent distribution
    if not intents.empty:
        st.subheader("Distribusi Intent (7 hari)")
        chart_df = intents.set_index("intent")
        st.bar_chart(chart_df)

    # Escalations
    if not escalations.empty:
        st.subheader("Eskalasi Terbaru")
        st.dataframe(escalations, use_container_width=True, hide_index=True)


# ============================================================
# Main
# ============================================================
def main():
    st.set_page_config(
        page_title="Dropship Dashboard",
        page_icon="📦",
        layout="wide",
    )

    # Sidebar
    st.sidebar.title("Dropship Dashboard")
    page = st.sidebar.radio("Navigasi", [
        "Overview",
        "Affiliate Intelligence",
        "Orders & Fulfillment",
        "Products & Inventory",
        "CS Bot Analytics",
    ])
    st.sidebar.divider()
    st.sidebar.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S WIB')}")
    st.sidebar.caption(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")

    if st.sidebar.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

    pages = {
        "Overview": page_overview,
        "Affiliate Intelligence": page_affiliate,
        "Orders & Fulfillment": page_orders,
        "Products & Inventory": page_products,
        "CS Bot Analytics": page_cs,
    }

    pages[page]()


if __name__ == "__main__":
    main()
