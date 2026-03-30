# pages/tab_product.py — Tab Sản phẩm & SKU
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import NARROW_DIST_OUTLETS
from utils.helpers import (kpi_card, section_header, alert_box, update_fig,
                           fmt_vnd, chart_with_data, download_button)
from queries.sales import get_product_summary, get_sku_summary


def render(filters: dict):
    s, e = filters["start"], filters["end"]
    a, z, c = filters["area"], filters["zone"], filters["category"]
    top_n = filters["top_n"]

    prod = get_product_summary(s, e, a, z, c)
    sku = get_sku_summary(s, e, a, z, c)

    section_header("📦 Hiệu quả sản phẩm")
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("📦 Tổng sản phẩm", str(len(prod)))
    with c2:
        kpi_card("💰 DS TB / SP",    fmt_vnd(prod["revenue"].mean()) + " VND")
    with c3:
        kpi_card("🏆 DS Top 1",      fmt_vnd(prod["revenue"].max()) + " VND")
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        tp = prod.nlargest(top_n, "revenue").sort_values("revenue")
        fig = go.Figure(go.Bar(
            x=tp["revenue"], y=tp["product_name"], orientation="h",
            marker=dict(color=tp["revenue"],
                        colorscale=[[0, "#1a3a6e"], [1, "#4c6ef5"]], showscale=False),
            text=tp["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig, df=tp, filename="top_products",
            title=f"Top {top_n} sản phẩm", height=max(320, top_n*28),
            display_cols={"product_name": "Sản phẩm", "category": "Danh mục",
                          "revenue": "Doanh số (VND)", "qty": "SL", "outlets": "# SM", "days": "Ngày"},
            format_cols={"revenue": "vnd"},
        )
    with col2:
        bp = prod.nsmallest(top_n, "revenue").sort_values(
            "revenue", ascending=False)
        fig2 = go.Figure(go.Bar(
            x=bp["revenue"], y=bp["product_name"], orientation="h",
            marker_color="#ff5b5b",
            text=bp["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig2, df=bp, filename="bottom_products",
            title=f"Bottom {top_n} sản phẩm", height=max(320, top_n*28),
            display_cols={"product_name": "Sản phẩm", "category": "Danh mục",
                          "revenue": "Doanh số (VND)", "qty": "SL", "outlets": "# SM"},
            format_cols={"revenue": "vnd"},
        )
    # Treemap
    fig3 = px.treemap(prod, path=["category", "product_name"], values="revenue",
                      color="revenue",
                      color_continuous_scale=["#1a1d29", "#4c6ef5", "#00c48c"])
    fig3.update_traces(textfont=dict(color="#fff"))
    chart_with_data(
        fig=fig3, df=prod, filename="product_treemap",
        title="Treemap DS: Danh mục → Sản phẩm", height=380,
        display_cols={"category": "Danh mục", "product_name": "Sản phẩm",
                      "revenue": "Doanh số (VND)", "qty": "SL", "outlets": "# SM"},
        format_cols={"revenue": "vnd"},
    )
    fig3.update_layout(coloraxis_showscale=False)

    # ── SKU ───────────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("🔖 Phân tích SKU")

    col1, col2 = st.columns(2)
    with col1:
        ts = sku.head(top_n).sort_values("revenue")
        fig4 = go.Figure(go.Bar(
            x=ts["revenue"], y=ts["sku_name"], orientation="h",
            marker_color="#00c48c",
            text=ts["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=9),
        ))
        chart_with_data(
            fig=fig4, df=ts, filename="top_skus",
            title=f"Top {top_n} SKU", height=max(320, top_n*28),
            display_cols={"sku_name": "SKU", "product_name": "Sản phẩm",
                          "category": "DM", "revenue": "Doanh số (VND)", "qty": "SL", "outlets": "# SM"},
            format_cols={"revenue": "vnd"},
        )

    with col2:
        bs = sku.tail(top_n).sort_values("revenue", ascending=False)
        fig5 = go.Figure(go.Bar(
            x=bs["revenue"], y=bs["sku_name"], orientation="h",
            marker_color="#f03e3e",
            text=bs["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=9),
        ))
        chart_with_data(
            fig=fig5, df=bs, filename="bottom_skus",
            title=f"Bottom {top_n} SKU", height=max(320, top_n*28),
            display_cols={"sku_name": "SKU", "product_name": "Sản phẩm",
                          "category": "DM", "revenue": "Doanh số (VND)", "qty": "SL", "outlets": "# SM"},
            format_cols={"revenue": "vnd"},
        )

    # ── Cảnh báo ─────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("🚨 Cảnh báo sản phẩm / SKU")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"**🔴 SKU phân phối hẹp (≤ {NARROW_DIST_OUTLETS} điểm bán)**")
        narrow = sku[sku["outlets"] <= NARROW_DIST_OUTLETS].sort_values(
            "revenue", ascending=False)
        if narrow.empty:
            alert_box("✅ Tất cả SKU có phân phối rộng", "g")
        for _, r in narrow.head(8).iterrows():
            alert_box(f"📌 <b>{r['sku_name']}</b> ({r['category']}) — "
                      f"{r['outlets']} SM, DS = {fmt_vnd(r['revenue'])} VND", "w")

    with col2:
        st.markdown("**🔴 SKU doanh số đáy 10%**")
        low_rev = sku[sku["revenue"] < sku["revenue"].quantile(0.1)].head(8)
        if low_rev.empty:
            alert_box("✅ Không có SKU hiệu quả đặc biệt thấp", "g")
        for _, r in low_rev.iterrows():
            alert_box(f"⚠️ <b>{r['sku_name']}</b> — "
                      f"DS = {fmt_vnd(r['revenue'])} VND | {r['qty']} units | {r['outlets']} SM", "r")

    # ── Bảng SKU đầy đủ ───────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋 Bảng chi tiết SKU")
    sku_tbl = sku.rename(columns={
        "sku_code": "Mã SKU", "sku_name": "Tên SKU", "product_name": "Sản phẩm",
        "category": "Danh mục", "revenue": "Doanh số", "qty": "SL", "outlets": "# SM"
    })
    sku_tbl["Doanh số"] = sku_tbl["Doanh số"].apply(lambda x: f"{x:,.0f}")
    st.dataframe(sku_tbl, width="stretch", hide_index=True)
