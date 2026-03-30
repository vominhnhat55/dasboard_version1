# pages/tab_overview.py — Tab Tổng quan
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import COLOR_SEQ
from utils.helpers import kpi_card, section_header, update_fig, fmt_vnd, chart_with_data, download_button, fmt_qty
from utils.forecast import forecast_next_n_days
from queries.sales import get_weekly, get_area_zone


def render(filters: dict, daily_df):
    s, e = filters["start"], filters["end"]
    a, z, c = filters["area"], filters["zone"], filters["category"]
    weekly = get_weekly(s, e, a, z, c)
    area_df = get_area_zone(s, e, a, z, c)
    fc_df = forecast_next_n_days(daily_df, filters["fc_pct"])
    total_rev = daily_df["revenue"].sum()
    total_qty = daily_df["qty"].sum()
    total_qty_kg = daily_df["qty_kg"].sum()
    avg_day = daily_df["revenue"].mean()
    # ── KPIs ─────────────────────────────────────────────────────────────────
    section_header("📈 Chỉ số tổng thể")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        kpi_card("💰 Tổng doanh số",  fmt_vnd(total_rev) + " VND")
    with c2:
        kpi_card("📦 Số lượng(SP)",       fmt_qty(total_qty)+" SP")
    with c3:
        kpi_card("📦 Số lượng(KG)",      fmt_qty(total_qty_kg)+" KG")
    with c4:
        kpi_card("📊 TB / ngày",       fmt_vnd(avg_day) + " VND")
    with c5:
        kpi_card("📅 Số ngày",         str(daily_df["report_date"].nunique()))
    with c6:
        kpi_card("📆 Số tuần",         str(weekly["week"].nunique()))
    st.markdown("<br>", unsafe_allow_html=True)
    # ── Trend chart ───────────────────────────────────────────────────────────
    section_header("📆 Doanh số theo ngày")
    daily_df = daily_df.copy()
    daily_df["ma7"] = daily_df["revenue"].rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_bar(x=daily_df["report_date"], y=daily_df["revenue"],
                name="Doanh số", marker_color="#4c6ef5", opacity=.75)
    fig.add_scatter(x=daily_df["report_date"], y=daily_df["ma7"],
                    name="MA7", line=dict(color="#00c48c", width=2))
    if not fc_df.empty:
        fig.add_scatter(
            x=fc_df["date"], y=fc_df["forecast"], name="Dự báo 7 ngày",
            line=dict(color="#ffaa44", width=2, dash="dash"),
            mode="lines+markers", marker=dict(size=6, color="#ffaa44"),
            fill="tozeroy", fillcolor="rgba(255,170,68,.07)",
        )

    # Chuẩn bị data cho bảng
    trend_data = daily_df[["report_date", "revenue", "qty", "ma7"]].copy()
    if not fc_df.empty:
        fc_rows = fc_df.rename(
            columns={"date": "report_date", "forecast": "revenue"})
        fc_rows["qty"] = None
        fc_rows["ma7"] = None
        fc_rows["_type"] = "Dự báo"
        trend_data["_type"] = "Thực tế"
        trend_data = pd.concat([trend_data, fc_rows], ignore_index=True)
    else:
        trend_data["_type"] = "Thực tế"

    chart_with_data(
        fig=fig, df=trend_data, filename="daily_revenue",
        title="Doanh số thực + MA7 + Dự báo 7 ngày", height=340,
        display_cols={"report_date": "Ngày", "revenue": "Doanh số (VND)",
                      "qty": "Sản lượng", "ma7": "MA7", "_type": "Loại"},
        format_cols={"revenue": "vnd", "ma7": "vnd"},
    )

    # ── WoW & DOW ────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        weekly = weekly.copy()
        weekly["wow"] = weekly["revenue"].pct_change() * 100
        colors = ["#00c48c" if (pd.isna(v) or v >= 0)
                  else "#ff5b5b" for v in weekly["wow"]]
        fig2 = go.Figure(go.Bar(
            x=[f"Tuần {w}" for w in weekly["week"]], y=weekly["revenue"],
            marker_color=colors,
            text=[
                f"{v:+.1f}%" if not pd.isna(v) else "" for v in weekly["wow"]],
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig2, df=weekly, filename="weekly_revenue",
            title="Doanh số theo tuần (WoW%)", height=280,
            display_cols={"week": "Tuần",
                          "revenue": "Doanh số (VND)", "wow": "WoW%"},
            format_cols={"revenue": "vnd", "wow": "pct"},
        )

    with col2:
        dow_lbl = {0: "T2", 1: "T3", 2: "T4",
                   3: "T5", 4: "T6", 5: "T7", 6: "CN"}
        dw = daily_df.groupby("dow")["revenue"].mean().reset_index()
        dw["label"] = dw["dow"].map(dow_lbl)
        fig3 = go.Figure(go.Bar(
            x=dw["label"], y=dw["revenue"], marker_color="#7950f2",
            text=dw["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig3, df=dw, filename="dow_revenue",
            title="DS TB theo thứ trong tuần", height=280,
            display_cols={"label": "Thứ", "revenue": "DS TB (VND)"},
            format_cols={"revenue": "vnd"},
        )

    # ── Area & Zone ───────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        area_sum = area_df.groupby("area")["revenue"].sum().reset_index()
        fig4 = px.pie(area_sum, names="area", values="revenue",
                      color_discrete_sequence=COLOR_SEQ, hole=.45)
        fig4.update_traces(textfont_color="#fff")
        chart_with_data(
            fig=fig4, df=area_sum, filename="area_revenue",
            title="Tỷ trọng theo Khu vực", height=260,
            display_cols={"area": "Khu vực", "revenue": "Doanh số (VND)"},
            format_cols={"revenue": "vnd"},
        )

    with col2:
        zone_sum = area_df.groupby("zone")["revenue"].sum(
        ).reset_index().sort_values("revenue")
        fig5 = go.Figure(go.Bar(
            x=zone_sum["revenue"], y=zone_sum["zone"], orientation="h",
            marker_color="#15aabf",
            text=zone_sum["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig5, df=zone_sum, filename="zone_revenue",
            title="Doanh số theo Zone", height=260,
            display_cols={"zone": "Zone", "revenue": "Doanh số (VND)"},
            format_cols={"revenue": "vnd"},
        )
