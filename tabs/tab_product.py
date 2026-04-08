# pages/tab_product.py — Tab Sản phẩm & SKU
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import NARROW_DIST_OUTLETS, COLOR_SEQ
from utils.helpers import (kpi_card, section_header, alert_box, update_fig,
                           fmt_vnd, chart_with_data, download_button)
from queries.sales import (get_product_summary, get_sku_summary,
                           get_category_weekly, get_product_daily, get_store_list)


def render(filters: dict):
    s, e = filters["start"], filters["end"]
    a, z, sc = filters["area"], filters["zone"], filters["store_codes"]
    top_n = filters["top_n"]

    prod = get_product_summary(s, e, a, z, sc)
    sku = get_sku_summary(s, e, a, z, sc)

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

    # ── Cảnh báo sản phẩm ────────────────────────────────────────────────────
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

    # ── Danh mục ─────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("🏷️ Phân tích danh mục sản phẩm")

    cat_raw = get_category_weekly(s, e, a, z, sc)
    cat = (cat_raw.groupby("category")
           .agg(revenue=("revenue", "sum"), qty=("qty", "sum"),
                outlets=("outlets", "max"), products=("products", "max"), skus=("skus", "max"))
           .reset_index().sort_values("revenue", ascending=False))
    cat["share_pct"] = cat["revenue"] / cat["revenue"].sum() * 100

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
        fig_pie = px.pie(cat, names="category", values="revenue",
                         color_discrete_sequence=COLOR_SEQ, hole=.4)
        fig_pie.update_traces(textfont_color="#fff")
        chart_with_data(
            fig=fig_pie, df=cat, filename="category_share",
            title="Tỷ trọng DS theo danh mục", height=300,
            display_cols={"category": "Danh mục",
                          "revenue": "Doanh số (VND)", "share_pct": "Tỷ trọng (%)"},
            format_cols={"revenue": "vnd", "share_pct": "float"},
        )

    with col2:
        fig_cat = go.Figure(go.Bar(
            x=cat["category"], y=cat["revenue"],
            marker=dict(color=COLOR_SEQ[:len(cat)]),
            text=cat["share_pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig_cat, df=cat, filename="category_revenue",
            title="Doanh số & tỷ trọng danh mục", height=300,
            display_cols={"category": "Danh mục", "revenue": "Doanh số (VND)",
                          "qty": "SL", "outlets": "# SM", "skus": "# SKU", "share_pct": "Tỷ trọng (%)"},
            format_cols={"revenue": "vnd", "share_pct": "float"},
        )

    fig_trend = px.line(cat_raw, x="week", y="revenue", color="category",
                        color_discrete_sequence=COLOR_SEQ, markers=True,
                        labels={"week": "Tuần", "revenue": "Doanh số (VND)"})
    chart_with_data(
        fig=fig_trend, df=cat_raw, filename="category_weekly_trend",
        title="Xu hướng DS theo tuần — từng danh mục", height=320,
        display_cols={"category": "Danh mục", "week": "Tuần",
                      "revenue": "Doanh số (VND)", "qty": "SL"},
        format_cols={"revenue": "vnd"},
    )

    # Cảnh báo danh mục
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

    fig_bubble = px.scatter(cat, x="outlets", y="revenue", size="skus", color="category",
                            color_discrete_sequence=COLOR_SEQ, text="category",
                            labels={"outlets": "# Điểm bán", "revenue": "Tổng DS (VND)"})
    fig_bubble.update_traces(textposition="top center",
                             textfont=dict(color="#fff", size=10))
    chart_with_data(
        fig=fig_bubble, df=cat, filename="category_bubble",
        title="Phân phối vs Doanh số  (bong bóng = số SKU)", height=320,
        display_cols={"category": "Danh mục", "outlets": "# SM", "revenue": "Doanh số (VND)",
                      "skus": "# SKU", "products": "# SP"},
        format_cols={"revenue": "vnd"},
    )

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

    # ── Drill-down DS theo ngày — theo sản phẩm ───────────────────────────────
    st.markdown("---")
    section_header("🔍 Drill-down — DS theo ngày từng sản phẩm")

    stores_df2 = get_store_list(a, z)
    store_opts2 = ["Tất cả siêu thị"] + [
        f"{r['supermarket_code']} — {r['supermarket_name']}"
        for _, r in stores_df2.iterrows()
    ]
    sel_store2 = st.selectbox("🏪 Lọc theo siêu thị", store_opts2,
                              key="prod_drilldown_store")

    store_code2 = ("Tất cả" if sel_store2 == "Tất cả siêu thị"
                   else sel_store2.split(" — ")[0])

    with st.spinner("Đang query..."):
        prod_daily = get_product_daily(s, e, a, z, sc, store_code2)

    if prod_daily.empty:
        st.warning("Không có dữ liệu sản phẩm.")
        return

    top_prods = (prod_daily.groupby("product_name")["revenue"]
                 .sum().nlargest(top_n).index.tolist())
    prod_top = prod_daily[prod_daily["product_name"].isin(top_prods)]

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("📦 Tổng SP", str(prod_daily["product_name"].nunique()))
    with c2:
        kpi_card("💰 Tổng DS", fmt_vnd(prod_daily["revenue"].sum())+" VND")
    with c3:
        kpi_card("🏆 SP #1",
                 prod_daily.groupby("product_name")["revenue"].sum().idxmax())

    st.markdown("<br>", unsafe_allow_html=True)

    # Heatmap SP × ngày
    heat_df = prod_top.groupby(
        ["product_name", "report_date"])["revenue"].sum().reset_index()
    heat_pivot = heat_df.pivot(
        index="product_name", columns="report_date", values="revenue").fillna(0)

    fig_heat = go.Figure(go.Heatmap(
        z=heat_pivot.values,
        x=[d.strftime("%d/%m") for d in heat_pivot.columns],
        y=heat_pivot.index.tolist(),
        colorscale=[[0, "#1a1d29"], [0.5, "#4c6ef5"], [1, "#00c48c"]],
        hoverongaps=False,
        hovertemplate="<b>%{y}</b><br>%{x}<br>DS: %{z:,.0f} VND<extra></extra>",
    ))
    update_fig(fig_heat,
               max(300, len(heat_pivot) * 28),
               f"Heatmap DS sản phẩm × ngày (Top {top_n} SP)")
    st.plotly_chart(fig_heat, width="stretch")

    # Line chart trend từng SP
    fig_line = px.line(
        prod_top.groupby(["product_name", "report_date"])["revenue"]
                .sum().reset_index(),
        x="report_date", y="revenue", color="product_name",
        color_discrete_sequence=COLOR_SEQ,
        labels={"report_date": "Ngày", "revenue": "DS (VND)",
                "product_name": "Sản phẩm"},
    )
    fig_line.update_traces(mode="lines+markers", marker=dict(size=4))
    chart_with_data(
        fig=fig_line,
        df=prod_top.groupby(["product_name", "report_date"])["revenue"]
        .sum().reset_index(),
        filename="product_daily_trend",
        title=f"Xu hướng DS theo ngày — Top {top_n} sản phẩm",
        height=380,
        display_cols={"product_name": "Sản phẩm",
                      "report_date": "Ngày", "revenue": "DS (VND)"},
        format_cols={"revenue": "vnd"},
    )

    # Bảng raw data
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋 Bảng DS sản phẩm theo ngày")

    prod_tbl = prod_daily.copy()
    prod_tbl["report_date"] = prod_tbl["report_date"].dt.strftime("%d/%m/%Y")
    prod_tbl = prod_tbl.rename(columns={
        "product_name": "Sản phẩm", "category": "Danh mục",
        "report_date": "Ngày", "revenue": "DS (VND)", "qty": "Sản lượng"
    })
    prod_tbl["DS (VND)"] = prod_tbl["DS (VND)"].apply(lambda x: f"{x:,.0f}")

    col_tbl, col_btn = st.columns([5, 1])
    with col_tbl:
        st.dataframe(prod_tbl, width="stretch", hide_index=True)
    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        download_button(prod_tbl, f"product_daily_{store_code2}", "⬇️ Tải CSV")
