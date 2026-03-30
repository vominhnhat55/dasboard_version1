# pages/tab_outlet.py — Tab Điểm bán
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import LOW_COVERAGE_DAYS, SURGE_THRESHOLD
from utils.helpers import (kpi_card, section_header, alert_box, update_fig,
                           fmt_vnd, chart_with_data, download_button)
from queries.sales import get_outlet_summary, get_outlet_half_trend


def render(filters: dict):
    s, e = filters["start"], filters["end"]
    a, z, c = filters["area"], filters["zone"], filters["category"]
    top_n = filters["top_n"]
    alert_pct = filters["alert_pct"]

    outlet = get_outlet_summary(s, e, a, z, c)
    outlet_tr = get_outlet_half_trend(s, e, a, z, c)
    outlet["rank"] = outlet["revenue"].rank(ascending=False).astype(int)

    avg_rev = outlet["revenue"].mean()
    q20 = outlet["revenue"].quantile(0.2)
    q80 = outlet["revenue"].quantile(0.8)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    section_header("🏪 Hiệu quả điểm bán")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("🏪 Tổng điểm bán",     str(len(outlet)))
    with c2:
        kpi_card("💰 DS TB / điểm bán",  fmt_vnd(avg_rev) + " VND")
    with c3:
        kpi_card("⭐ Ngưỡng Top 20%",     fmt_vnd(q80) + " VND")
    with c4:
        kpi_card("⚠️ Ngưỡng Bot 20%",    fmt_vnd(q20) + " VND")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Top & Bottom ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        top = outlet.nlargest(top_n, "revenue").sort_values("revenue")
        fig = go.Figure(go.Bar(
            x=top["revenue"], y=top["supermarket_name"], orientation="h",
            marker_color="#4c6ef5",
            text=top["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig, df=top, filename="top_outlets",
            title=f"Top {top_n} điểm bán cao nhất", height=max(320, top_n*28),
            display_cols={"rank": "Rank", "supermarket_name": "Tên SM", "area": "KV",
                          "zone": "Zone", "revenue": "Doanh số (VND)",
                          "rev_per_day": "DS/ngày", "active_days": "Ngày HĐ"},
            format_cols={"revenue": "vnd", "rev_per_day": "vnd"},
        )

    with col2:
        bot = outlet.nsmallest(top_n, "revenue").sort_values(
            "revenue", ascending=False)
        fig2 = go.Figure(go.Bar(
            x=bot["revenue"], y=bot["supermarket_name"], orientation="h",
            marker_color="#ff5b5b",
            text=bot["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig2, df=bot, filename="bottom_outlets",
            title=f"Bottom {top_n} điểm bán thấp nhất", height=max(320, top_n*28),
            display_cols={"rank": "Rank", "supermarket_name": "Tên SM", "area": "KV",
                          "zone": "Zone", "revenue": "Doanh số (VND)",
                          "rev_per_day": "DS/ngày", "active_days": "Ngày HĐ"},
            format_cols={"revenue": "vnd", "rev_per_day": "vnd"},
        )

    # ── Scatter ───────────────────────────────────────────────────────────────
    fig3 = px.scatter(
        outlet, x="active_days", y="rev_per_day", size="revenue", color="area",
        hover_data={"supermarket_name": True, "revenue": True},
        color_discrete_map={"KV1": "#4c6ef5", "KV2": "#00c48c"},
        labels={"active_days": "Ngày hoạt động",
                "rev_per_day": "DS/ngày (VND)"},
    )
    fig3.update_traces(marker=dict(opacity=.75, line=dict(width=0)))
    chart_with_data(
        fig=fig3,
        df=outlet[["supermarket_name", "area", "zone",
                   "active_days", "rev_per_day", "revenue", "sku_count"]],
        filename="outlet_scatter",
        title="Ngày hoạt động vs Hiệu suất/ngày  (bong bóng = tổng DS)", height=320,
        display_cols={"supermarket_name": "Tên SM", "area": "KV", "zone": "Zone",
                      "active_days": "Ngày HĐ", "rev_per_day": "DS/ngày (VND)",
                      "revenue": "Tổng DS (VND)", "sku_count": "# SKU"},
        format_cols={"rev_per_day": "vnd", "revenue": "vnd"},
    )

    # ── Cảnh báo ─────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("🚨 Cảnh báo điểm bán")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**⬇️ Sụt giảm mạnh (nửa sau so nửa đầu tháng)**")
        declining = outlet_tr[outlet_tr["chg"] <
                              alert_pct].sort_values("chg").head(10)
        if declining.empty:
            alert_box("✅ Không có điểm bán sụt giảm vượt ngưỡng", "g")
        for _, r in declining.iterrows():
            alert_box(f"📉 <b>{r['supermarket_name']}</b> — giảm {abs(r['chg']):.1f}%  "
                      f"({fmt_vnd(r['first'])} → {fmt_vnd(r['second'])} VND)", "r")

    with col2:
        st.markdown(f"**⬆️ Tăng trưởng tốt (>{SURGE_THRESHOLD}%)**")
        surging = outlet_tr[outlet_tr["chg"] > SURGE_THRESHOLD].sort_values(
            "chg", ascending=False).head(10)
        if surging.empty:
            alert_box(
                f"ℹ️ Không có điểm bán tăng mạnh >{SURGE_THRESHOLD}%", "w")
        for _, r in surging.iterrows():
            alert_box(f"🚀 <b>{r['supermarket_name']}</b> — tăng {r['chg']:.1f}%  "
                      f"({fmt_vnd(r['first'])} → {fmt_vnd(r['second'])} VND)", "g")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"**⚠️ Điểm bán coverage thấp (≤ {LOW_COVERAGE_DAYS} ngày)**")
    low_cov = outlet[outlet["active_days"] <=
                     LOW_COVERAGE_DAYS].sort_values("active_days")
    if low_cov.empty:
        alert_box("✅ Tất cả điểm bán có coverage ổn", "g")
    for _, r in low_cov.head(10).iterrows():
        alert_box(f"🕐 <b>{r['supermarket_name']}</b> — {r['active_days']} ngày, "
                  f"DS = {fmt_vnd(r['revenue'])} VND", "w")

    # ── Bảng đầy đủ + download ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋 Bảng chi tiết tất cả điểm bán")

    tbl = outlet[["rank", "supermarket_code", "supermarket_name", "area", "zone",
                  "revenue", "rev_per_day", "qty", "active_days", "sku_count"]].copy()
    col_map = {"rank": "Rank", "supermarket_code": "Mã SM", "supermarket_name": "Tên SM",
               "area": "KV", "zone": "Zone", "revenue": "Doanh số", "rev_per_day": "DS/ngày",
               "qty": "Sản lượng", "active_days": "Ngày HĐ", "sku_count": "# SKU"}
    tbl = tbl.rename(columns=col_map).sort_values("Rank")
    tbl["Doanh số"] = tbl["Doanh số"].apply(lambda x: f"{x:,.0f}")
    tbl["DS/ngày"] = tbl["DS/ngày"].apply(lambda x: f"{x:,.0f}")

    col_tbl, col_btn = st.columns([5, 1])
    with col_tbl:
        st.dataframe(tbl, width="stretch", hide_index=True)
    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        download_button(tbl, "all_outlets", "⬇️ Tải CSV")
