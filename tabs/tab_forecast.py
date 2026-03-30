# pages/tab_forecast.py — Tab Dự báo & Scorecard
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from config import TOP5_RISK_PCT, HHI_WARNING, LOW_SKU_THRESHOLD
from utils.helpers import (kpi_card, section_header, alert_box, update_fig,
                           fmt_vnd, fmt_pct, chart_with_data, download_button)
from utils.forecast import forecast_next_n_days, estimate_month_forecast
from queries.sales import get_outlet_summary, get_category_weekly


def render(filters: dict, daily_df):
    s, e = filters["start"], filters["end"]
    a, z, c = filters["area"], filters["zone"], filters["category"]
    fc_pct = filters["fc_pct"]
    fc_df = forecast_next_n_days(daily_df, fc_pct)
    total_rev = daily_df["revenue"].sum()
    avg_day = daily_df["revenue"].mean()
    section_header("🔮 Dự báo doanh số")
    daily_df = daily_df.copy()
    daily_df["ma7"] = daily_df["revenue"].rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_bar(x=daily_df["report_date"], y=daily_df["revenue"],
                name="Thực tế", marker_color="#4c6ef5", opacity=.7)
    fig.add_scatter(x=daily_df["report_date"], y=daily_df["ma7"],
                    name="MA7", line=dict(color="#00c48c", width=2))
    if not fc_df.empty:
        fig.add_scatter(
            x=fc_df["date"], y=fc_df["forecast"], name="Dự báo 7 ngày",
            line=dict(color="#ffaa44", width=2, dash="dash"),
            mode="lines+markers", marker=dict(size=7, color="#ffaa44"),
            fill="tozeroy", fillcolor="rgba(255,170,68,.07)",
        )

    # Merge actual + forecast cho bảng
    actual_rows = daily_df[["report_date", "revenue", "qty", "ma7"]].copy()
    actual_rows["loai"] = "Thực tế"
    if not fc_df.empty:
        fc_rows = fc_df.rename(
            columns={"date": "report_date", "forecast": "revenue"})
        fc_rows["qty"] = None
        fc_rows["ma7"] = None
        fc_rows["loai"] = "Dự báo"
        tbl_data = pd.concat([actual_rows, fc_rows], ignore_index=True)
    else:
        tbl_data = actual_rows

    chart_with_data(
        fig=fig, df=tbl_data, filename="forecast_detail",
        title="Doanh số thực tế + Dự báo WMA 7 ngày tới", height=360,
        display_cols={"report_date": "Ngày", "revenue": "Doanh số (VND)",
                      "qty": "Sản lượng", "ma7": "MA7", "loai": "Loại"},
        format_cols={"revenue": "vnd", "ma7": "vnd"},
    )

    # ── Forecast KPIs ─────────────────────────────────────────────────────────
    if not fc_df.empty:
        week_fc = fc_df["forecast"].sum()
        day_fc = fc_df["forecast"].mean()
        last_day = daily_df["report_date"].max()
        month_end = pd.Timestamp(last_day.year, last_day.month,
                                 pd.Timestamp(last_day.year, last_day.month, 1).days_in_month)
        month_fc = estimate_month_forecast(
            total_rev, daily_df, fc_pct, month_end)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("📅 FC 7 ngày tới",   fmt_vnd(week_fc) + " VND")
        with c2:
            kpi_card("📆 FC tháng (tổng)", fmt_vnd(month_fc) + " VND")
        with c3:
            kpi_card("📊 FC TB / ngày",     fmt_vnd(day_fc) + " VND")
        with c4:
            kpi_card("📈 Tăng trưởng FC",   fmt_pct(
                fc_pct), "vs WMA gốc", "pos")
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📅 Chi tiết dự báo 7 ngày")

        fc_show = fc_df.copy()
        fc_show["Ngày"] = fc_show["date"].dt.strftime("%d/%m/%Y (%A)")
        fc_show["Dự báo DS (VND)"] = fc_show["forecast"].apply(
            lambda x: f"{x:,.0f}")
        fc_show["So TB thực tế"] = ((fc_show["forecast"] - avg_day) / avg_day * 100)\
            .apply(lambda x: f"{'🟢' if x >= 0 else '🔻'} {abs(x):.1f}%")

        col_tbl, col_btn = st.columns([4, 1])
        with col_tbl:
            st.dataframe(fc_show[["Ngày", "Dự báo DS (VND)", "So TB thực tế"]],
                         width="stretch", hide_index=True)
        with col_btn:
            st.markdown("<br><br>", unsafe_allow_html=True)
            download_button(fc_show[["Ngày", "Dự báo DS (VND)", "So TB thực tế"]],
                            "forecast_7days", "⬇️ Tải CSV")
    # ── Scorecard ─────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("📊 Scorecard hiệu quả kinh doanh")
    outlet = get_outlet_summary(s, e, a, z, c)
    cat_raw = get_category_weekly(s, e, a, z, c)
    cat_sum = cat_raw.groupby("category")["revenue"].sum()
    top5_pct = outlet.nlargest(5, "revenue")["revenue"].sum() / total_rev * 100
    hhi = ((cat_sum / cat_sum.sum()) ** 2).sum()
    weekend_avg = daily_df[daily_df["dow"].isin([5, 6])]["revenue"].mean()
    weekday_avg = daily_df[~daily_df["dow"].isin([5, 6])]["revenue"].mean()
    we_lift = (weekend_avg / weekday_avg - 1) * 100 if weekday_avg > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("🏪 Điểm bán active", str(len(outlet)))
        kpi_card("⚠️ Top 5 SM chiếm", f"{top5_pct:.1f}%", "tổng DS",
                 "neg" if top5_pct > TOP5_RISK_PCT else "pos")
    with c2:
        kpi_card("📐 HHI danh mục", f"{hhi:.3f}", "0=đa dạng · 1=tập trung",
                 "pos" if hhi < HHI_WARNING else "neg")
        kpi_card("💰 DS/outlet/ngày (median)",
                 fmt_vnd(outlet["rev_per_day"].median()) + " VND")
    with c3:
        kpi_card("📅 Cuối tuần vs ngày thường", fmt_pct(we_lift),
                 "T7–CN vs T2–T6", "pos" if we_lift > 0 else "neg")

    # ── Nhận xét ─────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("💡 Nhận xét tự động")
    if top5_pct > TOP5_RISK_PCT:
        alert_box(
            f"⚠️ Top 5 SM chiếm {top5_pct:.1f}% DS — rủi ro tập trung cao", "r")
    if hhi > HHI_WARNING:
        alert_box(f"⚠️ HHI = {hhi:.3f} — DS tập trung vào ít danh mục", "w")
    if we_lift > 20:
        alert_box(
            f"📌 Cuối tuần mạnh hơn {we_lift:.0f}% — đảm bảo tồn kho T7–CN", "g")
    low_sku_sm = outlet[outlet["sku_count"] < LOW_SKU_THRESHOLD]
    if len(low_sku_sm) > 0:
        alert_box(
            f"📦 {len(low_sku_sm)} điểm bán có <{LOW_SKU_THRESHOLD} SKU", "w")
    alert_box(
        "💡 Forecast dùng WMA 14 ngày + DOW pattern. Càng nhiều lịch sử → càng chính xác.", "w")
