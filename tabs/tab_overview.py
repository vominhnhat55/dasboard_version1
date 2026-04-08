# pages/tab_overview.py — Tab Tổng quan
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import COLOR_SEQ
from utils.helpers import kpi_card, section_header, alert_box, update_fig, fmt_vnd, chart_with_data, download_button, fmt_qty
from utils.forecast import forecast_next_n_days
from queries.sales import get_weekly, get_area_zone, get_outlet_summary, get_forecast
from tabs.tab_fc import _compute_fc_status, DANGER_PCT, WARNING_PCT


def render(filters: dict, daily_df):
    s, e = filters["start"], filters["end"]
    a, z, sc = filters["area"], filters["zone"], filters["store_codes"]
    weekly = get_weekly(s, e, a, z, sc)
    area_df = get_area_zone(s, e, a, z, sc)
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
            title="Doanh số theo tuần (Tuần/Tuần -1 %)", height=280,
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

    # ── FC Summary ────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("🎯 Tiến độ vs Forecast")
    outlet = get_outlet_summary(s, e, a, z, sc)
    fc_df_raw = get_forecast(s, a, z, store_codes=sc)

    if fc_df_raw.empty:
        st.info("⚠️ Không có dữ liệu FC trong khoảng thời gian này.")
    else:
        fc_status = _compute_fc_status(outlet, fc_df_raw, s, e)

        total_fc = fc_status["fc_total"].sum()
        total_actual = fc_status["revenue"].sum()
        overall_pct = total_actual / total_fc * 100 if total_fc > 0 else 0
        n_achieved = len(fc_status[fc_status["status"] == "achieved"])
        n_ontrack = len(fc_status[fc_status["status"] == "on_track"])
        n_warning = len(fc_status[fc_status["status"] == "warning"])
        n_danger = len(fc_status[fc_status["status"] == "danger"])

        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        with fc1:
            kpi_card("🎯 FC tổng", fmt_vnd(total_fc) + " VND")
        with fc2:
            kpi_card("💰 Thực tế", fmt_vnd(total_actual) + " VND")
        with fc3:
            kpi_card("📊 % Đạt FC", f"{overall_pct:.1f}%",
                     "so FC kỳ", "pos" if overall_pct >= 85 else "neg")
        with fc4:
            kpi_card("✅ Đạt / Đúng tiến độ",
                     f"{n_achieved + n_ontrack} SM", "", "pos")
        with fc5:
            kpi_card("🔴 Nguy cơ / Cần TDõi",
                     f"{n_danger + n_warning} SM", "", "neg")

        st.markdown("<br>", unsafe_allow_html=True)
        gcol, dcol = st.columns([1, 2])
        with gcol:
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
                        {"range": [0, DANGER_PCT],
                            "color": "#2d1b1b"},
                        {"range": [DANGER_PCT, WARNING_PCT],
                            "color": "#2d2414"},
                        {"range": [WARNING_PCT, 100],
                            "color": "#0d2d1f"},
                        {"range": [100, 120],
                            "color": "#0a3d2e"},
                    ],
                    "threshold": {"line": {"color": "#00c48c", "width": 3},
                                  "thickness": 0.85, "value": 100},
                },
                title={"text": "% Đạt FC tổng thể",
                       "font": {"color": "#8b8fa8", "size": 13}},
            ))
            fig_gauge.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260,
                margin=dict(l=20, r=20, t=40, b=20),
                font=dict(color="#8b8fa8"),
            )
            st.plotly_chart(fig_gauge, width="stretch")

        with dcol:
            status_count = fc_status["status_label"].value_counts(
            ).reset_index()
            status_count.columns = ["Trạng thái", "Số SM"]
            status_colors = {
                "✅ Đạt FC":            "#00c48c",
                "🟢 Đúng tiến độ":      "#4c6ef5",
                "🟡 Cần theo dõi":      "#ffaa44",
                "🔴 Nguy cơ không đạt": "#ff5b5b",
                "⚪ Không có FC":       "#4a4a5a",
            }
            colors = [status_colors.get(sl, "#8b8fa8")
                      for sl in status_count["Trạng thái"]]
            fig_donut = go.Figure(go.Pie(
                labels=status_count["Trạng thái"],
                values=status_count["Số SM"],
                marker_colors=colors,
                hole=0.5,
                textfont_color="#fff",
            ))
            update_fig(fig_donut, 260, "Phân bổ trạng thái điểm bán vs FC")
            st.plotly_chart(fig_donut, width="stretch")

        # ── Bar: FC vs Actual top stores ──────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📊 So sánh FC vs Thực tế theo điểm bán")
        top_n = filters["top_n"]
        top_stores = fc_status[fc_status["fc_total"]
                               > 0].nlargest(top_n, "fc_total")
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
                          "actual_pct": "% Đạt", "gap_pct": "Gap (%)"},
            format_cols={"fc_total": "vnd", "revenue": "vnd",
                         "actual_pct": "float", "gap_pct": "float"},
        )

        # ── Alerts ────────────────────────────────────────────────────────────
        st.markdown("---")
        section_header("🚨 Cảnh báo điểm bán vs FC")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🔴 Nguy cơ không đạt FC (cần hành động ngay)**")
            danger = fc_status[fc_status["status"] ==
                               "danger"].sort_values("gap_pct").head(15)
            danger = danger.sort_values("zone")
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
            st.markdown(
                "**🟡 Cần theo dõi (có thể không đạt nếu không cải thiện)**")
            warn = fc_status[fc_status["status"] ==
                             "warning"].sort_values("gap_pct").head(15)
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
        achieved_df = fc_status[fc_status["status"] == "achieved"].sort_values(
            "actual_pct", ascending=False).head(10)
        for _, r in achieved_df.iterrows():
            alert_box(
                f"🏆 <b>{r['supermarket_name']}</b> — "
                f"đạt <b>{r['actual_pct']:.1f}%</b> FC  "
                f"({fmt_vnd(r['revenue'])} / {fmt_vnd(r['fc_total'])} VND)", "g"
            )

        # ── Scatter: % đạt vs gap ─────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📈 Phân tích tiến độ FC")
        df_plot = fc_status[fc_status["fc_total"] > 0].copy()
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
        # ── Full table ────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📋 Bảng chi tiết tất cả điểm bán vs FC")
        tbl = fc_status[["supermarket_name", "area", "zone", "fc_total", "revenue",
                         "actual_pct", "expected_pct", "gap_pct", "pace_ratio",
                         "status_label"]].copy()
        tbl.columns = ["Tên SM", "KV", "Zone", "FC (VND)", "Thực tế (VND)",
                       "% Đạt", "% KV tiến độ", "Gap (%)", "Tốc độ (%)", "Trạng thái"]
        for col in ["FC (VND)", "Thực tế (VND)"]:
            tbl[col] = tbl[col].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        for col in ["% Đạt", "% KV tiến độ", "Gap (%)", "Tốc độ (%)"]:
            tbl[col] = tbl[col].apply(
                lambda x: f"{x:.1f}" if pd.notna(x) else "")
        col_tbl, col_btn = st.columns([5, 1])
        with col_tbl:
            st.dataframe(tbl, width="stretch", hide_index=True)
        with col_btn:
            st.markdown("<br><br>", unsafe_allow_html=True)
            download_button(tbl, "fc_vs_actual_all", "⬇️ Tải CSV")
