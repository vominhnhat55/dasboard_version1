# pages/tab_drilldown.py
# Tab Drill-down — DS từng ngày từng siêu thị & từng sản phẩm
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from config import COLOR_SEQ
from utils.helpers import (kpi_card, section_header, alert_box,
                           fmt_vnd, chart_with_data, download_button, update_fig)
from queries.sales import get_outlet_daily, get_product_daily, get_store_list, get_forecast


def render(filters: dict):
    """Render Tab Drill-down."""
    s, e = filters["start"], filters["end"]
    a, z = filters["area"], filters["zone"]
    c = filters["category"]

    section_header("🔍 Drill-down — Doanh số chi tiết")

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    sub1, sub2 = st.tabs(["🏪 Theo Siêu thị", "📦 Theo Sản phẩm"])

    # ══════════ SUB-TAB 1: SIÊU THỊ ══════════════════════════════════════════
    with sub1:
        section_header("🏪 Doanh số từng ngày — từng siêu thị")

        # Filter siêu thị
        stores_df = get_store_list(a, z)
        store_options = ["Tất cả (tổng hợp)"] + [
            f"{r['supermarket_code']} — {r['supermarket_name']}"
            for _, r in stores_df.iterrows()
        ]
        sel_store_label = st.selectbox(
            "🏪 Chọn siêu thị",
            store_options,
            help="Chọn 1 SM để xem chi tiết từng ngày, hoặc 'Tất cả' để xem tổng hợp"
        )

        # Parse store code
        if sel_store_label == "Tất cả (tổng hợp)":
            sel_store_code = "Tất cả"
            sel_store_name = "Tất cả siêu thị"
        else:
            sel_store_code = sel_store_label.split(" — ")[0]
            sel_store_name = sel_store_label.split(" — ")[1]

        # Load data
        with st.spinner("Đang query..."):
            daily = get_outlet_daily(s, e, a, z, c, sel_store_code)
            fc_df = get_forecast(s, e, a, z)

        if daily.empty:
            st.warning("Không có dữ liệu cho lựa chọn này.")
            return

        # Aggregate nếu chọn "Tất cả"
        if sel_store_code == "Tất cả":
            daily_agg = daily.groupby("report_date").agg(
                revenue=("revenue", "sum"), qty=("qty", "sum")
            ).reset_index()
        else:
            daily_agg = daily.groupby("report_date").agg(
                revenue=("revenue", "sum"), qty=("qty", "sum")
            ).reset_index()

        daily_agg["ma7"] = daily_agg["revenue"].rolling(
            7, min_periods=1).mean()

        # FC của store này (theo tháng)
        fc_store = None
        if sel_store_code != "Tất cả" and not fc_df.empty:
            fc_store = fc_df[fc_df["store_code"] == sel_store_code]

        # KPIs
        total_rev = daily_agg["revenue"].sum()
        total_qty = daily_agg["qty"].sum()
        avg_day = daily_agg["revenue"].mean()
        peak_day = daily_agg.loc[daily_agg["revenue"].idxmax()]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("💰 Tổng DS", fmt_vnd(total_rev)+" VND")
        with c2:
            kpi_card("📊 TB / ngày", fmt_vnd(avg_day)+" VND")
        with c3:
            kpi_card("📦 Sản lượng", f"{int(total_qty):,}")
        with c4:
            kpi_card("🏆 Ngày đỉnh",
                     peak_day["report_date"].strftime("%d/%m"),
                     fmt_vnd(peak_day["revenue"])+" VND", "pos")

        # FC KPI nếu có
        if fc_store is not None and not fc_store.empty:
            fc_total = fc_store["fc_revenue"].sum()
            fc_pct = total_rev / fc_total * 100 if fc_total > 0 else 0
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                kpi_card("🎯 FC kỳ này", fmt_vnd(fc_total)+" VND")
            with c2:
                kpi_card("📊 % Đạt FC", f"{fc_pct:.1f}%", "",
                         "pos" if fc_pct >= 85 else "neg")
            with c3:
                kpi_card("💸 Còn cần",
                         fmt_vnd(max(0, fc_total - total_rev))+" VND",
                         "để đạt FC", "neu")

        st.markdown("<br>", unsafe_allow_html=True)
        # ── Chart DS theo ngày ─────────────────────────────────────────────
        fig = go.Figure()
        fig.add_bar(x=daily_agg["report_date"], y=daily_agg["revenue"],
                    name="Doanh số", marker_color="#4c6ef5", opacity=.8)
        fig.add_scatter(x=daily_agg["report_date"], y=daily_agg["ma7"],
                        name="MA7", line=dict(color="#00c48c", width=2))

        # Đường FC/ngày nếu có
        if fc_store is not None and not fc_store.empty:
            fc_total = fc_store["fc_revenue"].sum()
            total_days = (pd.to_datetime(e) - pd.to_datetime(s)).days + 1
            fc_per_day = fc_total / total_days
            fig.add_hline(
                y=fc_per_day, line_dash="dot",
                line_color="#ffaa44", line_width=2,
                annotation_text=f"FC TB/ngày: {fmt_vnd(fc_per_day)}",
                annotation_font_color="#ffaa44",
            )

        chart_with_data(
            fig=fig,
            df=daily_agg.rename(columns={"report_date": "Ngày",
                                         "revenue": "Doanh số (VND)",
                                         "qty": "Sản lượng", "ma7": "MA7"}),
            filename=f"daily_{sel_store_code}",
            title=f"DS theo ngày — {sel_store_name}", height=360,
            format_cols={"Doanh số (VND)": "vnd", "MA7": "vnd"},
        )

        # ── Nếu chọn cụ thể 1 SM: hiển thị FC theo tháng ─────────────────
        if fc_store is not None and not fc_store.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            section_header("📅 FC vs Thực tế theo tháng")

            # Actual theo tháng
            daily_agg["month"] = daily_agg["report_date"].dt.month
            act_month = daily_agg.groupby(
                "month")["revenue"].sum().reset_index()

            fc_month = fc_store[["month", "fc_revenue"]].copy()
            merged = act_month.merge(
                fc_month, on="month", how="outer").fillna(0)
            merged["month_name"] = merged["month"].apply(
                lambda m: f"Tháng {m}")
            merged["pct"] = (merged["revenue"] /
                             merged["fc_revenue"] * 100).round(1)

            fig2 = go.Figure()
            fig2.add_bar(x=merged["month_name"], y=merged["fc_revenue"],
                         name="FC", marker_color="#2a3a6e",
                         text=merged["fc_revenue"].apply(fmt_vnd),
                         textposition="outside", textfont=dict(color="#8b8fa8", size=10))
            fig2.add_bar(x=merged["month_name"], y=merged["revenue"],
                         name="Thực tế", marker_color="#4c6ef5",
                         text=merged["revenue"].apply(fmt_vnd),
                         textposition="outside", textfont=dict(color="#fff", size=10))
            fig2.update_layout(barmode="group")
            chart_with_data(
                fig=fig2, df=merged,
                filename=f"fc_monthly_{sel_store_code}",
                title=f"FC vs Thực tế theo tháng — {sel_store_name}", height=300,
                display_cols={"month_name": "Tháng", "fc_revenue": "FC (VND)",
                              "revenue": "Thực tế (VND)", "pct": "% Đạt"},
                format_cols={"fc_revenue": "vnd", "revenue": "vnd"},
            )

        # ── So sánh nhiều SM (nếu chọn "Tất cả") ─────────────────────────
        if sel_store_code == "Tất cả":
            st.markdown("<br>", unsafe_allow_html=True)
            section_header("📊 So sánh DS theo ngày — Top SM")

            top_sm = (daily.groupby(["supermarket_code", "supermarket_name"])["revenue"]
                      .sum().nlargest(filters["top_n"]).reset_index())
            daily_top = daily[daily["supermarket_code"].isin(
                top_sm["supermarket_code"])]
            daily_top_agg = daily_top.groupby(
                ["supermarket_name", "report_date"])["revenue"].sum().reset_index()

            fig3 = px.line(
                daily_top_agg, x="report_date", y="revenue",
                color="supermarket_name",
                color_discrete_sequence=COLOR_SEQ,
                labels={"report_date": "Ngày", "revenue": "Doanh số (VND)",
                        "supermarket_name": "Siêu thị"},
            )
            fig3.update_traces(mode="lines+markers", marker=dict(size=4))
            chart_with_data(
                fig=fig3, df=daily_top_agg,
                filename="top_outlets_daily_trend",
                title=f"Xu hướng DS theo ngày — Top {filters['top_n']} SM", height=380,
                display_cols={"supermarket_name": "Siêu thị",
                              "report_date": "Ngày", "revenue": "DS (VND)"},
                format_cols={"revenue": "vnd"},
            )

    # ══════════ SUB-TAB 2: SẢN PHẨM ══════════════════════════════════════════
    with sub2:
        section_header("📦 Doanh số từng ngày — theo sản phẩm")

        # Filter store cho sản phẩm
        stores_df2 = get_store_list(a, z)
        store_opts2 = ["Tất cả siêu thị"] + [
            f"{r['supermarket_code']} — {r['supermarket_name']}"
            for _, r in stores_df2.iterrows()
        ]
        col_store, col_cat = st.columns(2)
        with col_store:
            sel_store2 = st.selectbox("🏪 Lọc theo siêu thị", store_opts2,
                                      key="dd_store2")
        with col_cat:
            # Category options từ data
            cats = ["Tất cả"] + sorted(
                get_product_daily(s, e, a, z, c)["category"].unique().tolist()
            ) if True else ["Tất cả"]
            sel_cat2 = st.selectbox(
                "🏷️ Lọc danh mục", ["Tất cả"], key="dd_cat2")

        store_code2 = ("Tất cả" if sel_store2 == "Tất cả siêu thị"
                       else sel_store2.split(" — ")[0])

        with st.spinner("Đang query..."):
            prod_daily = get_product_daily(s, e, a, z, c, store_code2)

        if prod_daily.empty:
            st.warning("Không có dữ liệu sản phẩm.")
            return

        # Top N sản phẩm theo tổng DS
        top_prods = (prod_daily.groupby("product_name")["revenue"]
                     .sum().nlargest(filters["top_n"]).index.tolist())
        prod_top = prod_daily[prod_daily["product_name"].isin(top_prods)]

        # KPIs
        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card("📦 Tổng SP", str(prod_daily["product_name"].nunique()))
        with c2:
            kpi_card("💰 Tổng DS", fmt_vnd(prod_daily["revenue"].sum())+" VND")
        with c3:
            kpi_card("🏆 SP #1",
                     prod_daily.groupby("product_name")["revenue"].sum().idxmax())

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Heatmap: SP × ngày ────────────────────────────────────────────
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
                   f"Heatmap DS sản phẩm × ngày (Top {filters['top_n']} SP)")
        st.plotly_chart(fig_heat, use_container_width=True)

        # ── Line chart: trend từng SP ──────────────────────────────────────
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
            title=f"Xu hướng DS theo ngày — Top {filters['top_n']} sản phẩm",
            height=380,
            display_cols={"product_name": "Sản phẩm",
                          "report_date": "Ngày", "revenue": "DS (VND)"},
            format_cols={"revenue": "vnd"},
        )

        # ── Download raw data sản phẩm theo ngày ──────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📋 Bảng DS sản phẩm theo ngày")

        prod_tbl = prod_daily.copy()
        prod_tbl["report_date"] = prod_tbl["report_date"].dt.strftime(
            "%d/%m/%Y")
        prod_tbl = prod_tbl.rename(columns={
            "product_name": "Sản phẩm", "category": "Danh mục",
            "report_date": "Ngày", "revenue": "DS (VND)", "qty": "Sản lượng"
        })
        prod_tbl["DS (VND)"] = prod_tbl["DS (VND)"].apply(
            lambda x: f"{x:,.0f}")

        col_tbl, col_btn = st.columns([5, 1])
        with col_tbl:
            st.dataframe(prod_tbl, use_container_width=True, hide_index=True)
        with col_btn:
            st.markdown("<br><br>", unsafe_allow_html=True)
            download_button(
                prod_tbl, f"product_daily_{store_code2}", "⬇️ Tải CSV")
