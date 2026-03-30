# pages/tab_fc.py
# Tab FC — So sánh doanh số thực tế vs Forecast
# Cảnh báo điểm bán không đạt / có nguy cơ không đạt FC
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from config import COLOR_SEQ
from utils.helpers import (kpi_card, section_header, alert_box,
                           fmt_vnd, chart_with_data, download_button, update_fig)
from queries.sales import get_outlet_summary, get_forecast


# ── Hằng số cảnh báo ──────────────────────────────────────────────────────────
DANGER_PCT = 70    # % đạt FC → đỏ (nguy hiểm)
WARNING_PCT = 85    # % đạt FC → vàng (cần theo dõi)
PACE_DANGER = 75    # % tốc độ/ngày → đỏ
PACE_WARN = 90    # % tốc độ/ngày → vàng


def _compute_fc_status(outlet_df: pd.DataFrame, fc_df: pd.DataFrame,
                       start: str, end: str) -> pd.DataFrame:
    """
    Tính toán trạng thái FC cho từng điểm bán.

    Chỉ số 1 — Lũy kế:
        actual_pct = DS_thực_tế / FC_tháng × 100
        expected_pct = ngày_đã_qua / tổng_ngày_tháng × 100
        gap = actual_pct - expected_pct  (âm = đang lag so tiến độ)

    Chỉ số 2 — Tốc độ/ngày:
        actual_pace = DS_thực / ngày_đã_bán
        needed_pace = (FC - DS_thực) / ngày_còn_lại
        pace_ratio  = actual_pace / (FC / tổng_ngày) × 100
    """
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    today = min(end_dt, pd.Timestamp.today().normalize())

    # FC: lấy tháng trong range, fallback lấy toàn bộ nếu không có
    months_in_range = list(range(start_dt.month, end_dt.month + 1))
    fc_in_range = fc_df[fc_df["month"].isin(months_in_range)]
    fc_use = fc_in_range if not fc_in_range.empty else fc_df
    fc_agg = (fc_use
              .groupby("store_code")["fc_revenue"].sum()
              .reset_index().rename(columns={"fc_revenue": "fc_total"}))

    # Actual
    act = outlet_df[["supermarket_code", "supermarket_name", "area", "zone",
                     "revenue", "active_days", "rev_per_day"]].copy()
    act = act.rename(columns={"supermarket_code": "store_code"})
    # Merge
    df = act.merge(fc_agg, on="store_code", how="left")
    df["fc_total"] = df["fc_total"].fillna(0)

    # Số ngày trong khoảng
    total_days = (end_dt - start_dt).days + 1
    elapsed_days = (today - start_dt).days + 1
    remain_days = max(1, total_days - elapsed_days)

    # Chỉ số 1: lũy kế
    df["actual_pct"] = np.where(df["fc_total"] > 0,
                                df["revenue"] / df["fc_total"] * 100, np.nan)
    df["expected_pct"] = elapsed_days / total_days * 100
    df["gap_pct"] = df["actual_pct"] - df["expected_pct"]
    actual_pace = df["revenue"] / max(1, elapsed_days)
    # Chỉ số 2: tốc độ
    df["needed_pace"] = np.where(
        (df["fc_total"] > df["revenue"]) & (remain_days > 0),
        (df["fc_total"] - df["revenue"]) / remain_days, 0)
    df["pace_ratio"] = np.where(
        df["needed_pace"] > 0,
        actual_pace / df["needed_pace"] * 100, 100)

    # Trạng thái
    def status(row):
        if pd.isna(row["actual_pct"]) or row["fc_total"] == 0:
            return "no_fc"
        if row["actual_pct"] >= 100:
            return "achieved"
        if row["actual_pct"] < DANGER_PCT or row["pace_ratio"] < PACE_DANGER:
            return "danger"
        if row["actual_pct"] < WARNING_PCT or row["pace_ratio"] < PACE_WARN:
            return "warning"
        return "on_track"

    df["status"] = df.apply(status, axis=1)
    df["status_label"] = df["status"].map({
        "achieved":  "✅ Đạt FC",
        "on_track":  "🟢 Đúng tiến độ",
        "warning":   "🟡 Cần theo dõi",
        "danger":    "🔴 Nguy cơ không đạt",
        "no_fc":     "⚪ Không có FC",
    })
    return df.sort_values("gap_pct")


def render(filters: dict):
    """Render Tab FC."""
    s, e = filters["start"], filters["end"]
    a, z = filters["area"], filters["zone"]
    c = filters["category"]
    top_n = filters["top_n"]
    outlet = get_outlet_summary(s, e, a, z, c)
    fc_df = get_forecast(s, e, a, z)

    if fc_df.empty:
        st.warning("⚠️ Không có dữ liệu FC trong khoảng thời gian này. "
                   "Kiểm tra bảng `sales_db.forecast` trên BigQuery.")
        return

    df = _compute_fc_status(outlet, fc_df, s, e)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    section_header("🎯 Tổng quan vs Forecast")

    total_fc = df["fc_total"].sum()
    total_actual = df["revenue"].sum()
    overall_pct = total_actual / total_fc * 100 if total_fc > 0 else 0

    n_achieved = len(df[df["status"] == "achieved"])
    n_ontrack = len(df[df["status"] == "on_track"])
    n_warning = len(df[df["status"] == "warning"])
    n_danger = len(df[df["status"] == "danger"])

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("🎯 FC tổng", fmt_vnd(total_fc)+" VND")
    with c2:
        kpi_card("💰 Thực tế", fmt_vnd(total_actual)+" VND")
    with c3:
        kpi_card("📊 % Đạt FC", f"{overall_pct:.1f}%",
                 "so FC kỳ", "pos" if overall_pct >= 85 else "neg")
    with c4:
        kpi_card("✅ Đạt / Đúng tiến độ",
                 f"{n_achieved + n_ontrack} SM", "", "pos")
    with c5:
        kpi_card("🔴 Nguy cơ / Cần TDõi",
                 f"{n_danger + n_warning} SM", "", "neg")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Gauge tổng thể ────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 2])
    with col1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=overall_pct,
            number={"suffix": "%", "font": {"color": "#fff", "size": 36}},
            delta={"reference": 100, "suffix": "%",
                   "font": {"size": 14},
                   "decreasing": {"color": "#ff5b5b"},
                   "increasing": {"color": "#00c48c"}},
            gauge={
                "axis": {"range": [0, 120], "tickcolor": "#8b8fa8",
                         "tickfont": {"color": "#8b8fa8"}},
                "bar": {"color": "#4c6ef5"},
                "steps": [
                    {"range": [0, DANGER_PCT],  "color": "#2d1b1b"},
                    {"range": [DANGER_PCT, WARNING_PCT], "color": "#2d2414"},
                    {"range": [WARNING_PCT, 100], "color": "#0d2d1f"},
                    {"range": [100, 120], "color": "#0a3d2e"},
                ],
                "threshold": {"line": {"color": "#00c48c", "width": 3},
                              "thickness": 0.85, "value": 100},
            },
            title={"text": "% Đạt FC tổng thể", "font": {
                "color": "#8b8fa8", "size": 13}},
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=260,
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(color="#8b8fa8"),
        )
        st.plotly_chart(fig_gauge, width="stretch")

    with col2:
        # Donut trạng thái SM
        status_count = df["status_label"].value_counts().reset_index()
        status_count.columns = ["Trạng thái", "Số SM"]
        status_colors = {
            "✅ Đạt FC":             "#00c48c",
            "🟢 Đúng tiến độ":       "#4c6ef5",
            "🟡 Cần theo dõi":       "#ffaa44",
            "🔴 Nguy cơ không đạt":  "#ff5b5b",
            "⚪ Không có FC":        "#4a4a5a",
        }
        colors = [status_colors.get(s, "#8b8fa8")
                  for s in status_count["Trạng thái"]]
        fig_donut = go.Figure(go.Pie(
            labels=status_count["Trạng thái"],
            values=status_count["Số SM"],
            marker_colors=colors,
            hole=0.5,
            textfont_color="#fff",
        ))
        update_fig(fig_donut, 260, "Phân bổ trạng thái điểm bán vs FC")
        st.plotly_chart(fig_donut, width="stretch")

    # ── Waterfall: FC vs Actual top stores ───────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📊 So sánh FC vs Thực tế theo điểm bán")

    # Bar chart grouped
    top_stores = df[df["fc_total"] > 0].nlargest(top_n, "fc_total")
    fig_bar = go.Figure()
    fig_bar.add_bar(
        name="FC", x=top_stores["supermarket_name"],
        y=top_stores["fc_total"], marker_color="#2a3a6e",
        text=top_stores["fc_total"].apply(fmt_vnd),
        textposition="outside", textfont=dict(color="#8b8fa8", size=9),
    )
    fig_bar.add_bar(
        name="Thực tế", x=top_stores["supermarket_name"],
        y=top_stores["revenue"], marker_color="#4c6ef5",
        text=top_stores["revenue"].apply(fmt_vnd),
        textposition="outside", textfont=dict(color="#fff", size=9),
    )
    fig_bar.update_layout(barmode="group")
    chart_with_data(
        fig=fig_bar, df=top_stores,
        filename="fc_vs_actual_outlets",
        title=f"Top {top_n} SM — FC vs Thực tế (theo FC lớn nhất)", height=360,
        display_cols={"supermarket_name": "Tên SM", "area": "KV", "zone": "Zone",
                      "fc_total": "FC (VND)", "revenue": "Thực tế (VND)",
                      "actual_pct": "% Đạt", "gap_pct": "   "},
        format_cols={"fc_total": "vnd", "revenue": "vnd",
                     "actual_pct": "float", "gap_pct": "float"},
    )

    # ── CẢNH BÁO ─────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("🚨 Cảnh báo điểm bán vs FC")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🔴 Nguy cơ không đạt FC (cần hành động ngay)**")
        danger = df[df["status"] == "danger"].sort_values("gap_pct").head(15)
        if danger.empty:
            alert_box("✅ Không có điểm bán trong nguy hiểm", "g")
        for _, r in danger.iterrows():
            needed = fmt_vnd(
                r["needed_pace"]) if r["needed_pace"] > 0 else "N/A"
            alert_box(
                f"🔴 <b>{r['supermarket_name']}</b> ({r['zone']}) — "
                f"đạt <b>{r['actual_pct']:.1f}%</b> FC | "
                f"lag tiến độ {abs(r['gap_pct']):.1f}% | "
                f"cần {needed} VND/ngày", "r"
            )

    with col2:
        st.markdown("**🟡 Cần theo dõi (có thể không đạt nếu không cải thiện)**")
        warn = df[df["status"] == "warning"].sort_values("gap_pct").head(15)
        if warn.empty:
            alert_box("✅ Không có điểm bán cần theo dõi đặc biệt", "g")
        for _, r in warn.iterrows():
            needed = fmt_vnd(
                r["needed_pace"]) if r["needed_pace"] > 0 else "N/A"
            alert_box(
                f"🟡 <b>{r['supermarket_name']}</b> ({r['zone']}) — "
                f"đạt <b>{r['actual_pct']:.1f}%</b> FC | "
                f"cần {needed} VND/ngày để hoàn thành", "w"
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**✅ Điểm bán đạt / vượt FC**")
    achieved = df[df["status"].isin(["achieved"])].sort_values(
        "actual_pct", ascending=False).head(10)
    for _, r in achieved.iterrows():
        alert_box(
            f"🏆 <b>{r['supermarket_name']}</b> — "
            f"đạt <b>{r['actual_pct']:.1f}%</b> FC  "
            f"({fmt_vnd(r['revenue'])} / {fmt_vnd(r['fc_total'])} VND)", "g"
        )

    # ── Bubble: % đạt vs gap ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📈 Phân tích tiến độ FC")

    df_plot = df[df["fc_total"] > 0].copy()
    df_plot["color"] = df_plot["status"].map({
        "achieved":  "#00c48c",
        "on_track":  "#4c6ef5",
        "warning":   "#ffaa44",
        "danger":    "#ff5b5b",
        "no_fc":     "#4a4a5a",
    })
    fig_scatter = px.scatter(
        df_plot, x="actual_pct", y="gap_pct",
        size="fc_total", color="status_label",
        color_discrete_map={
            "✅ Đạt FC":            "#00c48c",
            "🟢 Đúng tiến độ":      "#4c6ef5",
            "🟡 Cần theo dõi":      "#ffaa44",
            "🔴 Nguy cơ không đạt": "#ff5b5b",
        },
        hover_data={"supermarket_name": True, "fc_total": True,
                    "revenue": True, "zone": True},
        labels={"actual_pct": "% Đạt FC lũy kế",
                "gap_pct":    "Gap vs tiến độ kỳ vọng (%)"},
    )
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="#8b8fa8",
                          annotation_text="Đúng tiến độ",
                          annotation_font_color="#8b8fa8")
    fig_scatter.add_vline(x=100, line_dash="dash", line_color="#00c48c",
                          annotation_text="100% FC",
                          annotation_font_color="#00c48c")
    fig_scatter.update_traces(marker=dict(opacity=0.8, line=dict(width=0)))
    chart_with_data(
        fig=fig_scatter,
        df=df_plot[["supermarket_name", "zone", "area", "fc_total", "revenue",
                    "actual_pct", "gap_pct", "pace_ratio", "status_label"]],
        filename="fc_progress_scatter",
        title="Tiến độ FC: % Đạt vs Gap tiến độ  (bong bóng = FC)", height=380,
        display_cols={
            "supermarket_name": "Tên SM", "zone": "Zone", "area": "KV",
            "fc_total": "FC (VND)", "revenue": "Thực tế (VND)",
            "actual_pct": "% Đạt FC", "gap_pct": "Gap (%)",
            "pace_ratio": "Tốc độ (%)", "status_label": "Trạng thái",
        },
        format_cols={"fc_total": "vnd", "revenue": "vnd",
                     "actual_pct": "float", "gap_pct": "float", "pace_ratio": "float"},
    )
    # ── Bảng đầy đủ ───────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("📋 Bảng chi tiết tất cả điểm bán vs FC")
    tbl = df[["supermarket_name", "area", "zone", "fc_total", "revenue",
              "actual_pct", "expected_pct", "gap_pct", "pace_ratio", "status_label"]].copy()
    tbl.columns = ["Tên SM", "KV", "Zone", "FC (VND)", "Thực tế (VND)",
                   "% Đạt", "% KV tiến độ", "Gap (%)", "Tốc độ (%)", "Trạng thái"]
    for col in ["FC (VND)", "Thực tế (VND)"]:
        tbl[col] = tbl[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
    for col in ["% Đạt", "% KV tiến độ", "Gap (%)", "Tốc độ (%)"]:
        tbl[col] = tbl[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "")

    col_tbl, col_btn = st.columns([5, 1])
    with col_tbl:
        st.dataframe(tbl, width="stretch", hide_index=True)
    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        download_button(tbl, "fc_vs_actual_all", "⬇️ Tải CSV")
