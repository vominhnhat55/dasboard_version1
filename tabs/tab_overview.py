# pages/tab_overview.py — Tab Tổng quan
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import COLOR_SEQ
from utils.helpers import kpi_card, section_header, alert_box, update_fig, fmt_vnd, chart_with_data, download_button, fmt_qty
from utils.forecast import forecast_next_n_days, compute_wma, compute_dow_index
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
    # ── Daily sales chart (actual + 7-day forecast) ─────────────────────────
    section_header("📊 Doanh số theo ngày (Thực tế + Dự báo 7 ngày)")
    daily_disp = daily_df[["report_date", "revenue"]].copy()
    daily_disp = daily_disp.sort_values("report_date")
    daily_disp.columns = ["date", "revenue"]
    fc7 = forecast_next_n_days(daily_df, filters["fc_pct"], n_days=7)
    fc7 = fc7.rename(columns={"date": "date", "forecast": "revenue"})
    fc7["type"] = "forecast"
    daily_disp["type"] = "actual"
    combined = pd.concat([daily_disp, fc7], ignore_index=True)
    combined = combined.sort_values("date")
    # WMA label for legend
    wma_val = compute_wma(daily_df["revenue"].values)
    dow_idx = compute_dow_index(daily_df)
    fig_daily = go.Figure()
    # Actual bars
    actual_mask = combined["type"] == "actual"
    fig_daily.add_trace(go.Bar(
        x=combined.loc[actual_mask, "date"],
        y=combined.loc[actual_mask, "revenue"],
        name="Thực tế",
        marker_color="#4c6ef5",
        text=combined.loc[actual_mask, "revenue"].apply(fmt_vnd),
        textposition="outside",
        textfont=dict(color="#fff", size=8),
    ))
    # Forecast bars (dashed border, orange)
    fc_mask = combined["type"] == "forecast"
    fig_daily.add_trace(go.Bar(
        x=combined.loc[fc_mask, "date"],
        y=combined.loc[fc_mask, "revenue"],
        name="FC 7 ngày",
        marker_color="#ffaa44",
        marker_opacity=0.7,
        text=combined.loc[fc_mask, "revenue"].apply(fmt_vnd),
        textposition="outside",
        textfont=dict(color="#fff", size=8),
    ))
    # Trendline through actuals (7-day MA)
    daily_disp_sorted = daily_disp.sort_values("date")
    ma7 = daily_disp_sorted["revenue"].rolling(7, min_periods=1).mean()
    fig_daily.add_trace(go.Scatter(
        x=daily_disp_sorted["date"],
        y=ma7,
        name="MA7",
        mode="lines",
        line=dict(color="#00c48c", width=2, dash="dot"),
    ))
    fig_daily.update_layout(
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.08,
                    xanchor="center", x=0.5),
        xaxis=dict(title=dict(font=dict(color="#8b8fa8", size=11))),
        yaxis=dict(title=dict(text="Doanh số (VND)",
                   font=dict(color="#8b8fa8", size=11))),
    )
    chart_with_data(
        fig=fig_daily,
        df=combined,
        filename="daily_sales_with_forecast",
        title="Doanh số & Dự báo 7 ngày",
        height=320,
        display_cols={"date": "Ngày",
                      "revenue": "Doanh số (VND)", "type": "Loại"},
        format_cols={"revenue": "vnd"},
    )

    # ── 7-day FC breakdown table ─────────────────────────────────────────────
    dow_labels = {0: "T2", 1: "T3", 2: "T4",
                  3: "T5", 4: "T6", 5: "T7", 6: "CN"}
    fc7_detail = forecast_next_n_days(daily_df, filters["fc_pct"], n_days=7)
    fc7_detail = fc7_detail.copy()
    fc7_detail["dow_label"] = fc7_detail["date"].dt.dayofweek.map(dow_labels)
    fc7_detail["DOW_factor"] = fc7_detail["date"].dt.dayofweek.map(
        lambda d: dow_idx.get(d, 1.0))
    fc7_detail["Ngày"] = fc7_detail["date"].dt.strftime("%d/%m")
    fc7_detail["Thứ"] = fc7_detail["dow_label"]
    fc7_detail["Hệ số DOW"] = fc7_detail["DOW_factor"].round(3)
    fc7_detail["FC (VND)"] = fc7_detail["forecast"].apply(lambda x: fmt_vnd(x))
    tbl7 = fc7_detail[["Ngày", "Thứ", "Hệ số DOW", "FC (VND)"]].copy()
    with st.expander("📋 Chi tiết FC 7 ngày"):
        st.dataframe(tbl7, width="stretch", hide_index=True,
                     use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    # ── Trend chart ───────────────────────────────────────────────────────────
    # ── WoW & DOW ────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        weekly = weekly.copy()
        weekly["wow"] = weekly["revenue"].pct_change() * 100
        # ── Current week forecast (WMA × DOW factors) ────────────────────────
        wma_val = compute_wma(daily_df["revenue"].values)
        dow_idx = compute_dow_index(daily_df)
        recent_dates = pd.date_range(
            daily_df["report_date"].max() - pd.Timedelta(days=6),
            daily_df["report_date"].max(),
        )
        current_week_forecast = sum(
            wma_val * dow_idx.get(d.dayofweek, 1.0) for d in recent_dates
        )
        current_week_num = weekly["week"].max()

        # Build display df: actual weeks + current week forecast
        weekly_disp = pd.concat([
            weekly,
            pd.DataFrame({
                "week": [current_week_num],
                "revenue": [current_week_forecast],
                "wow": [None],
            }),
        ], ignore_index=True)

        # ── Combo chart: bars (revenue) + line (WoW%) ──────────────────────────
        labels = [f"Tuần {w}" for w in weekly_disp["week"]]
        # Actual weeks: blue bars
        actual_labels = labels[:-1]
        actual_rev = weekly_disp["revenue"].iloc[:-1].tolist()
        fig2 = go.Figure(go.Bar(
            x=actual_labels, y=actual_rev,
            name="Doanh số",
            marker_color="#4c6ef5",
            text=[fmt_vnd(v) for v in actual_rev],
            textposition="outside",
            textfont=dict(color="#fff", size=9),
        ))

        # Forecast week: purple bar (last row)
        fig2.add_bar(
            x=[labels[-1]], y=[weekly_disp["revenue"].iloc[-1]],
            name="FC Dự báo",
            marker_color="#ffaa44",
            marker_opacity=0.75,
            text=[fmt_vnd(weekly_disp["revenue"].iloc[-1])],
            textposition="outside",
            textfont=dict(color="#fff", size=9),
        )

        # WoW% line on secondary y-axis
        fig2.add_trace(go.Scatter(
            x=labels, y=weekly_disp["wow"],
            name="%tuần/tuần-1", mode="lines+markers+text",
            yaxis="y2",
            line=dict(color="#ffaa44", width=2.5),
            marker=dict(size=8, color="#ffaa44"),
            text=[f"{v:+.1f}%" if pd.notna(v)
                  else "" for v in weekly_disp["wow"]],
            textposition="top center",
            textfont=dict(color="#ffaa44", size=9),
        ))

        fig2.update_layout(
            yaxis=dict(title=dict(text="Doanh số (VND)",
                       font=dict(color="#8b8fa8", size=11))),
            yaxis2=dict(
                title=dict(text="WoW%", font=dict(color="#ffaa44", size=11)),
                anchor="free", overlaying="y", side="right", position=1.0,
                tickfont=dict(color="#ffaa44"),
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.06,
                        xanchor="center", x=0.5),
            height=300,
        )
        chart_with_data(
            fig=fig2, df=weekly_disp, filename="weekly_revenue",
            # title="Doanh số theo tuần (cột) & WoW% (đường) — Tuần cuối = FC dự báo",
            height=300,
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

        # ── Alerts — table with progress ─────────────────────────────────────────
        st.markdown("---")
        section_header("🚨 Cảnh báo điểm bán vs FC")

        alert_df = fc_status[fc_status["status"].isin(
            ["danger", "warning", "achieved", "on_track"]
        )].copy()
        alert_df["sort_val"] = alert_df["status"].map(
            {"danger": 0, "warning": 1, "on_track": 2, "achieved": 3})
        alert_df = alert_df.sort_values(
            ["sort_val", "gap_pct"]).reset_index(drop=True)

        status_icon = {
            "danger":   "🔴",
            "warning":  "🟡",
            "on_track": "🟢",
            "achieved": "✅",
        }
        status_label = {
            "danger":   "Nguy hiểm",
            "warning":  "Cần TDõi",
            "on_track": "Đúng tiến độ",
            "achieved": "Đạt FC",
        }
        status_color = {
            "danger": "#ff5b5b",
            "warning": "#ffaa44",
            "on_track": "#4c6ef5",
            "achieved": "#00c48c",
        }
        # ── Filter pills ───────────────────────────────────────────────────────
        pill_options = [status_label[k] for k in status_label]
        selected = st.pills(
            "Lọc trạng thái",
            options=pill_options,
            default=pill_options,
            selection_mode="multi",
            key="alert_filter",
        )
        visible = [k for k in status_label if status_label[k] in selected]

        # ── Search row ─────────────────────────────────────────────────────────
        search_q = st.text_input(
            "🔍 Tìm tên SM / Zone",
            placeholder="Nhập tên điểm bán hoặc zone…",
            label_visibility="collapsed",
        )

        # ── Build table ───────────────────────────────────────────────────────
        tbl = fc_status.copy()
        tbl = tbl[tbl["status"].isin(visible)].copy()
        if search_q:
            q = search_q.lower()
            tbl = tbl[tbl["supermarket_name"].str.lower().str.contains(q, na=False) |
                      tbl["zone"].str.lower().str.contains(q, na=False)]
        tbl["TT"] = tbl["status"].map(status_icon)
        tbl["Tên SM"] = tbl["supermarket_name"]
        tbl["KV"] = tbl["area"]
        tbl["Zone"] = tbl["zone"]
        tbl["FC (VND)"] = tbl["fc_total"]
        tbl["Thực tế (VND)"] = tbl["revenue"]
        tbl["% Đạt"] = tbl["actual_pct"]
        tbl["% KV tiến độ"] = tbl["expected_pct"]
        tbl["Gap (%)"] = tbl["gap_pct"]
        tbl["Tốc độ (%)"] = tbl["pace_ratio"]
        tbl["Trạng thái"] = tbl["status_label"]
        tbl["Cần/ngày"] = tbl["needed_pace"]
        for col in ["FC (VND)", "Thực tế (VND)"]:
            tbl[col] = tbl[col].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        for col in ["% Đạt", "% KV tiến độ", "Gap (%)", "Tốc độ (%)"]:
            tbl[col] = tbl[col].apply(
                lambda x: f"{x:.1f}" if pd.notna(x) else "")
        tbl["Cần/ngày"] = tbl["Cần/ngày"].apply(
            lambda x: fmt_vnd(x) if x > 0 else "—")

        disp = tbl[["TT", "Tên SM", "KV", "Zone", "FC (VND)", "Thực tế (VND)",
                    "% Đạt", "% KV tiến độ", "Gap (%)", "Tốc độ (%)",
                    "Trạng thái", "Cần/ngày"]].copy()

        # download button (after disp is built)
        download_button(disp, "fc_vs_actual_all", "⬇️ Tải CSV")

        # progress bar HTML (st.dataframe can't render HTML — use HTML table)
        def progress_bar(pct, status):
            color = status_color.get(status, "#8b8fa8")
            pct_txt = f"{pct:.1f}%"
            text_color = "#fff" if pct <= 70 else "#111"
            return (
                f'<div style="background:#1e1e2e;border-radius:4px;height:18px;width:100%;'
                f'position:relative;display:flex;align-items:center;">'
                f'<div style="background:{color};width:{min(pct, 100):.1f}%;height:18px;'
                f'border-radius:4px;display:inline-block;'
                f'line-height:18px;text-align:center;">'
                f'<span style="color:{text_color};font-size:11px;font-weight:600;'
                f'padding-left:4px;white-space:nowrap;">{pct_txt}</span></div></div>'
            )

        tbl["Tiến độ"] = [
            progress_bar(p, s)
            for p, s in zip(tbl["actual_pct"].fillna(0), tbl["status"])
        ]

        disp_pb = tbl[["TT", "Tên SM", "KV", "Zone", "FC (VND)", "Thực tế (VND)",
                       "% Đạt", "% KV tiến độ", "Gap (%)", "Tốc độ (%)",
                       "Trạng thái", "Cần/ngày", "Tiến độ"]].copy()

        st.markdown(
            f'<div style="height:360px;overflow-y:auto;border:1px solid #2d2d4a;'
            f'border-radius:8px;padding:4px;">'
            f'{disp_pb.to_html(escape=False, index=False)}</div>',
            unsafe_allow_html=True)

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
