# pages/tab_outlet.py — Tab Điểm bán
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import LOW_COVERAGE_DAYS, SURGE_THRESHOLD, COLOR_SEQ
from utils.helpers import (kpi_card, section_header, alert_box, update_fig,
                           fmt_vnd, chart_with_data, download_button)
from queries.sales import (get_outlet_summary, get_outlet_half_trend,
                           get_outlet_daily, get_store_list, get_forecast)


def render(filters: dict):
    s, e = filters["start"], filters["end"]
    a, z, sc = filters["area"], filters["zone"], filters["store_codes"]
    top_n = filters["top_n"]
    alert_pct = filters["alert_pct"]

    outlet = get_outlet_summary(s, e, a, z, sc)
    outlet_tr = get_outlet_half_trend(s, e, a, z, sc)
    outlet["rank"] = outlet["revenue"].rank(ascending=False).astype(int)

    avg_rev = outlet["revenue"].mean()
    q20 = outlet["revenue"].quantile(0.2)
    q80 = outlet["revenue"].quantile(0.8)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    section_header("🏪 Điểm bán")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("🏪 Số liệu từ ",     str(len(outlet))+" Điểm bán")
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

    # ── Drill-down DS theo ngày ───────────────────────────────────────────────
    st.markdown("---")
    section_header("🔍 Drill-down — DS theo ngày từng siêu thị")

    stores_df = get_store_list(a, z)
    store_options = ["Tất cả (tổng hợp)"] + [
        f"{r['supermarket_code']} — {r['supermarket_name']}"
        for _, r in stores_df.iterrows()
    ]
    sel_store_label = st.selectbox(
        "🏪 Chọn siêu thị",
        store_options,
        help="Chọn 1 SM để xem chi tiết từng ngày, hoặc 'Tất cả' để xem tổng hợp",
        key="outlet_drilldown_store",
    )

    if sel_store_label == "Tất cả (tổng hợp)":
        sel_store_code = "Tất cả"
        sel_store_name = "Tất cả siêu thị"
    else:
        sel_store_code = sel_store_label.split(" — ")[0]
        sel_store_name = sel_store_label.split(" — ")[1]

    with st.spinner("Đang query..."):
        daily = get_outlet_daily(s, e, a, z, sc, sel_store_code)
        fc_df = get_forecast(s, a, z, store_codes=sc)

    if daily.empty:
        st.warning("Không có dữ liệu cho lựa chọn này.")
        return

    daily_agg = daily.groupby("report_date").agg(
        revenue=("revenue", "sum"), qty=("qty", "sum")
    ).reset_index()
    daily_agg["ma7"] = daily_agg["revenue"].rolling(7, min_periods=1).mean()

    fc_store = None
    if sel_store_code != "Tất cả" and not fc_df.empty:
        fc_store = fc_df[fc_df["supermarket_code"] == sel_store_code]

    # KPIs
    total_rev_dd = daily_agg["revenue"].sum()
    total_qty_dd = daily_agg["qty"].sum()
    avg_day_dd = daily_agg["revenue"].mean()
    peak_day = daily_agg.loc[daily_agg["revenue"].idxmax()]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("💰 Tổng DS", fmt_vnd(total_rev_dd)+" VND")
    with c2:
        kpi_card("📊 TB / ngày", fmt_vnd(avg_day_dd)+" VND")
    with c3:
        kpi_card("📦 Sản lượng", f"{int(total_qty_dd):,}")
    with c4:
        kpi_card("🏆 Ngày đỉnh",
                 peak_day["report_date"].strftime("%d/%m"),
                 fmt_vnd(peak_day["revenue"])+" VND", "pos")

    if fc_store is not None and not fc_store.empty:
        fc_total = fc_store["fc_revenue"].sum()
        fc_pct = total_rev_dd / fc_total * 100 if fc_total > 0 else 0
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card("🎯 FC kỳ này", fmt_vnd(fc_total)+" VND")
        with c2:
            kpi_card("📊 % Đạt FC", f"{fc_pct:.1f}%", "",
                     "pos" if fc_pct >= 85 else "neg")
        with c3:
            kpi_card("💸 Còn cần",
                     fmt_vnd(max(0, fc_total - total_rev_dd))+" VND",
                     "để đạt FC", "neu")

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart DS theo ngày
    fig_dd = go.Figure()
    fig_dd.add_bar(x=daily_agg["report_date"], y=daily_agg["revenue"],
                   name="Doanh số", marker_color="#4c6ef5", opacity=.8)
    fig_dd.add_scatter(x=daily_agg["report_date"], y=daily_agg["ma7"],
                       name="MA7", line=dict(color="#00c48c", width=2))

    if fc_store is not None and not fc_store.empty:
        fc_total = fc_store["fc_revenue"].sum()
        total_days = (pd.to_datetime(e) - pd.to_datetime(s)).days + 1
        fc_per_day = fc_total / total_days
        fig_dd.add_hline(
            y=fc_per_day, line_dash="dot",
            line_color="#ffaa44", line_width=2,
            annotation_text=f"FC TB/ngày: {fmt_vnd(fc_per_day)}",
            annotation_font_color="#ffaa44",
        )

    chart_with_data(
        fig=fig_dd,
        df=daily_agg.rename(columns={"report_date": "Ngày",
                                     "revenue": "Doanh số (VND)",
                                     "qty": "Sản lượng", "ma7": "MA7"}),
        filename=f"daily_{sel_store_code}",
        title=f"DS theo ngày — {sel_store_name}", height=360,
        format_cols={"Doanh số (VND)": "vnd", "MA7": "vnd"},
    )

    # FC theo tháng nếu chọn cụ thể 1 SM
    if fc_store is not None and not fc_store.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📅 FC vs Thực tế theo tháng")

        daily_agg["month"] = daily_agg["report_date"].dt.month
        act_month = daily_agg.groupby("month")["revenue"].sum().reset_index()
        fc_month = fc_store[["month", "fc_revenue"]].copy()
        merged = act_month.merge(fc_month, on="month", how="outer").fillna(0)
        merged["month_name"] = merged["month"].apply(lambda m: f"Tháng {m}")
        merged["pct"] = (merged["revenue"] /
                         merged["fc_revenue"] * 100).round(1)

        fig_fc = go.Figure()
        fig_fc.add_bar(x=merged["month_name"], y=merged["fc_revenue"],
                       name="FC", marker_color="#2a3a6e",
                       text=merged["fc_revenue"].apply(fmt_vnd),
                       textposition="outside", textfont=dict(color="#8b8fa8", size=10))
        fig_fc.add_bar(x=merged["month_name"], y=merged["revenue"],
                       name="Thực tế", marker_color="#4c6ef5",
                       text=merged["revenue"].apply(fmt_vnd),
                       textposition="outside", textfont=dict(color="#fff", size=10))
        fig_fc.update_layout(barmode="group")
        chart_with_data(
            fig=fig_fc, df=merged,
            filename=f"fc_monthly_{sel_store_code}",
            title=f"FC vs Thực tế theo tháng — {sel_store_name}", height=300,
            display_cols={"month_name": "Tháng", "fc_revenue": "FC (VND)",
                          "revenue": "Thực tế (VND)", "pct": "% Đạt"},
            format_cols={"fc_revenue": "vnd", "revenue": "vnd"},
        )

    # So sánh nhiều SM nếu chọn "Tất cả"
    if sel_store_code == "Tất cả":
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📊 So sánh DS theo ngày — Top SM")

        top_sm = (daily.groupby(["supermarket_code", "supermarket_name"])["revenue"]
                  .sum().nlargest(top_n).reset_index())
        daily_top = daily[daily["supermarket_code"].isin(
            top_sm["supermarket_code"])]
        daily_top_agg = daily_top.groupby(
            ["supermarket_name", "report_date"])["revenue"].sum().reset_index()

        fig_top = px.line(
            daily_top_agg, x="report_date", y="revenue",
            color="supermarket_name",
            color_discrete_sequence=COLOR_SEQ,
            labels={"report_date": "Ngày", "revenue": "Doanh số (VND)",
                    "supermarket_name": "Siêu thị"},
        )
        fig_top.update_traces(mode="lines+markers", marker=dict(size=4))
        chart_with_data(
            fig=fig_top, df=daily_top_agg,
            filename="top_outlets_daily_trend",
            title=f"Xu hướng DS theo ngày — Top {top_n} SM", height=380,
            display_cols={"supermarket_name": "Siêu thị",
                          "report_date": "Ngày", "revenue": "DS (VND)"},
            format_cols={"revenue": "vnd"},
        )
