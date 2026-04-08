# pages/tab_category.py — Tab Danh mục
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import COLOR_SEQ
from utils.helpers import (kpi_card, section_header, alert_box, update_fig,
                           fmt_vnd, chart_with_data, download_button)
from queries.sales import get_category_weekly


def render(filters: dict):
    s, e = filters["start"], filters["end"]
    a, z, sc = filters["area"], filters["zone"], filters["store_codes"]

    cat_raw = get_category_weekly(s, e, a, z, sc)
    cat = (cat_raw.groupby("category")
           .agg(revenue=("revenue", "sum"), qty=("qty", "sum"),
                outlets=("outlets", "max"), products=("products", "max"), skus=("skus", "max"))
           .reset_index().sort_values("revenue", ascending=False))
    cat["share_pct"] = cat["revenue"] / cat["revenue"].sum() * 100

    section_header("🏷️ Phân tích danh mục sản phẩm")
    top_cat = cat.iloc[0]
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("📦 Danh mục #1", top_cat["category"],
                 f"DS: {fmt_vnd(top_cat['revenue'])} ({top_cat['share_pct']:.1f}%)", "pos")
    with c2:
        kpi_card("📊 Số danh mục",       str(len(cat)))
    with c3:
        kpi_card("🔖 SKU TB / danh mục", f"{cat['skus'].mean():.0f}")
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(cat, names="category", values="revenue",
                     color_discrete_sequence=COLOR_SEQ, hole=.4)
        fig.update_traces(textfont_color="#fff")
        chart_with_data(
            fig=fig, df=cat, filename="category_share",
            title="Tỷ trọng DS theo danh mục", height=300,
            display_cols={"category": "Danh mục",
                          "revenue": "Doanh số (VND)", "share_pct": "Tỷ trọng (%)"},
            format_cols={"revenue": "vnd", "share_pct": "float"},
        )

    with col2:
        fig2 = go.Figure(go.Bar(
            x=cat["category"], y=cat["revenue"],
            marker=dict(color=COLOR_SEQ[:len(cat)]),
            text=cat["share_pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig2, df=cat, filename="category_revenue",
            title="Doanh số & tỷ trọng danh mục", height=300,
            display_cols={"category": "Danh mục", "revenue": "Doanh số (VND)",
                          "qty": "SL", "outlets": "# SM", "skus": "# SKU", "share_pct": "Tỷ trọng (%)"},
            format_cols={"revenue": "vnd", "share_pct": "float"},
        )

    # Trend theo tuần
    fig3 = px.line(cat_raw, x="week", y="revenue", color="category",
                   color_discrete_sequence=COLOR_SEQ, markers=True,
                   labels={"week": "Tuần", "revenue": "Doanh số (VND)"})
    chart_with_data(
        fig=fig3, df=cat_raw, filename="category_weekly_trend",
        title="Xu hướng DS theo tuần — từng danh mục", height=320,
        display_cols={"category": "Danh mục", "week": "Tuần",
                      "revenue": "Doanh số (VND)", "qty": "SL"},
        format_cols={"revenue": "vnd"},
    )

    # ── Cảnh báo ─────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("🚨 Cảnh báo danh mục")
    weeks_avail = sorted(cat_raw["week"].unique())
    if len(weeks_avail) >= 2:
        w_first, w_last = weeks_avail[0], weeks_avail[-1]
        cat_piv = cat_raw.pivot_table(index="category", columns="week",
                                      values="revenue", aggfunc="sum", fill_value=0)
        cat_piv["growth"] = (cat_piv[w_last] - cat_piv[w_first]
                             ) / (cat_piv[w_first] + 1) * 100
        cat_piv = cat_piv.reset_index()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📉 Danh mục tăng trưởng âm**")
            bad = cat_piv[cat_piv["growth"] < 0].sort_values("growth")
            if bad.empty:
                alert_box("✅ Tất cả danh mục đều tăng trưởng dương", "g")
            for _, r in bad.iterrows():
                alert_box(f"📉 <b>{r['category']}</b> — giảm {abs(r['growth']):.1f}% "
                          f"(tuần {w_first}→{w_last})", "r")
        with col2:
            st.markdown("**🚀 Danh mục tăng trưởng tốt (>30%)**")
            good = cat_piv[cat_piv["growth"] >= 30].sort_values(
                "growth", ascending=False)
            if good.empty:
                alert_box("ℹ️ Không có danh mục tăng mạnh >30%", "w")
            for _, r in good.iterrows():
                alert_box(f"🚀 <b>{r['category']}</b> — tăng {r['growth']:.1f}% "
                          f"(tuần {w_first}→{w_last})", "g")
    else:
        alert_box("ℹ️ Chưa đủ dữ liệu đa tuần để tính tăng trưởng", "w")

    # Bubble chart
    fig4 = px.scatter(cat, x="outlets", y="revenue", size="skus", color="category",
                      color_discrete_sequence=COLOR_SEQ, text="category",
                      labels={"outlets": "# Điểm bán", "revenue": "Tổng DS (VND)"})
    fig4.update_traces(textposition="top center",
                       textfont=dict(color="#fff", size=10))
    chart_with_data(
        fig=fig4, df=cat, filename="category_bubble",
        title="Phân phối vs Doanh số  (bong bóng = số SKU)", height=320,
        display_cols={"category": "Danh mục", "outlets": "# SM", "revenue": "Doanh số (VND)",
                      "skus": "# SKU", "products": "# SP"},
        format_cols={"revenue": "vnd"},
    )

    # Bảng tổng hợp
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋 Bảng tổng hợp danh mục")
    cat_tbl = cat.copy()
    cat_tbl["revenue"] = cat_tbl["revenue"].apply(lambda x: f"{x:,.0f}")
    cat_tbl["share_pct"] = cat_tbl["share_pct"].apply(lambda x: f"{x:.1f}%")
    cat_tbl = cat_tbl.rename(columns={"category": "Danh mục", "revenue": "Doanh số",
                                      "qty": "SL", "outlets": "# SM", "products": "# SP",
                                      "skus": "# SKU", "share_pct": "Tỷ trọng"})
    col_tbl, col_btn = st.columns([5, 1])
    with col_tbl:
        st.dataframe(cat_tbl, width="stretch", hide_index=True)
    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        download_button(cat_tbl, "category_summary", "⬇️ Tải CSV")
