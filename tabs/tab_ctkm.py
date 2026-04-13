# tabs/tab_ctkm.py
# Tab CTKM — Phân tích Chương trình Khuyến mãi (Combo SKU)
# SKU Combo: sku_code bắt đầu bằng "Combo-"
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from config import COLOR_SEQ
from utils.helpers import (
    kpi_card, section_header, alert_box,
    fmt_vnd, chart_with_data, download_button,
)


def render(filters: dict):
    s, e = filters["start"], filters["end"]
    a, z = filters["area"], filters["zone"]
    sc = filters["store_codes"]

    overview = _load_overview(s, e, a, z, sc)
    by_outlet = _load_by_outlet(s, e, a, z, sc)
    by_cat = _load_by_category(s, e, a, z, sc)
    daily = _load_daily(s, e, a, z, sc)
    top_combo = _load_top_combos(s, e, a, z, sc, top_n=10)
    all_combos = _load_all_combos(s, e, a, z, sc)
    summary_combo = _load_summary_combo(s, e, a, z, sc)

    # ── Giải thích Combo là gì ─────────────────────────────────────────────────
    section_header("🎁 CTKM — Chương trình Khuyến mãi")
    # st.markdown("""
    # <div style="background:#1e2235;border:1px solid #2a2d3e;border-radius:10px;
    #             padding:12px 16px;margin-bottom:14px;">
    #     <div style="color:#fff;font-size:13px;font-weight:600;margin-bottom:6px;">
    #         📌 Combo SKU là gì?
    #     </div>
    #     <div style="color:#8b8fa8;font-size:12.5px;line-height:1.6;">
    #         Các sản phẩm thuộc chương trình khuyến mãi được nhận diện qua
    #         <b style="color:#ff6b6b;">sku_code bắt đầu bằng <code style="background:#2a2d3e;padding:2px 6px;border-radius:4px;">Combo-</code></b>.
    #         Nhóm <b style="color:#4c6ef5;">Non-Combo</b> = tất cả SKU còn lại (bán thông thường).
    #         Tab này phân tích đóng góp doanh số, tỷ lệ, và xu hướng của CTKM.
    #     </div>
    # </div>
    # """, unsafe_allow_html=True)

    # ── KPIs tổng quan ─────────────────────────────────────────────────────────
    section_header("📊 Chỉ số tổng quan")

    if overview.empty:
        st.info("⚠️ Không có dữ liệu trong khoảng thời gian này.")
        return

    # Combo bestseller
    best = top_combo.iloc[0] if not top_combo.empty else None

    combo_row = overview[overview["is_combo"] == "Combo"]
    ncombo_row = overview[overview["is_combo"] == "Non-Combo"]

    combo_rev = float(combo_row["revenue"].iloc[0]
                      ) if not combo_row.empty else 0
    ncombo_rev = float(ncombo_row["revenue"].iloc[0]
                       ) if not ncombo_row.empty else 0
    total_rev = combo_rev + ncombo_rev
    combo_pct = combo_rev / total_rev * 100 if total_rev > 0 else 0
    combo_qty = int(combo_row["qty"].iloc[0]) if not combo_row.empty else 0
    ncombo_qty = int(ncombo_row["qty"].iloc[0]) if not ncombo_row.empty else 0
    combo_sku = int(combo_row["sku_count"].iloc[0]
                    ) if not combo_row.empty else 0
    ncombo_sku = int(ncombo_row["sku_count"].iloc[0]
                     ) if not ncombo_row.empty else 0
    combo_outlet = int(combo_row["outlet_count"].iloc[0]
                       ) if not combo_row.empty else 0

    kpi_combo = combo_rev / (combo_outlet or 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("💰 DS Combo",         fmt_vnd(combo_rev) + " VND",  "", "pos")
    with c2:
        kpi_card("💸 DS Non-Combo",      fmt_vnd(ncombo_rev) + " VND")
    with c3:
        kpi_card("📊 Tỷ trọng Combo",   f"{combo_pct:.1f}%",
                 "trên tổng DS", "pos" if combo_pct > 10 else "neg")
    with c4:
        kpi_card("🛒 SL Combo",         f"{combo_qty:,}".replace(",", "."))
    with c5:
        kpi_card("🏪 SM bán Combo",      str(combo_outlet))

    # Bestseller combo
    if best is not None:
        c6, c7 = st.columns([3, 3])
        with c6:
            kpi_card("🏆 Combo bán chạy nhất", best["sku_name"],
                     f"{fmt_vnd(best['revenue'])} VND · {int(best['qty'])} SP", "pos")
        with c7:
            combo2 = top_combo.iloc[1] if len(top_combo) > 1 else None
            if combo2 is not None:
                kpi_card("🥈 Combo #2", combo2["sku_name"],
                         f"{fmt_vnd(combo2['revenue'])} VND", "pos")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Pie + Bar: tỷ trọng Combo vs Non-Combo ────────────────────────────────
    col_pie, col_bar = st.columns(2)
    with col_pie:
        pie_data = overview.copy()
        fig_pie = px.pie(
            pie_data, names="is_combo", values="revenue",
            color="is_combo",
            color_discrete_map={"Combo": "#ff6b6b", "Non-Combo": "#4c6ef5"},
            hole=0.45,
            labels={"is_combo": "Loại", "revenue": "Doanh số"},
        )
        fig_pie.update_traces(
            text=pie_data["is_combo"],
            textposition="outside",
            textfont=dict(color="#fff", size=13),
            hovertemplate="<b>%{label}</b><br>DS: %{value:,.0f} VND<br>%{percent}<extra></extra>",
        )
        chart_with_data(
            fig=fig_pie, df=pie_data, filename="ctkm_pie",
            title="Tỷ trọng Doanh số Combo vs Non-Combo", height=300,
            display_cols={"is_combo": "Loại", "revenue": "Doanh số (VND)",
                          "qty": "SL", "sku_count": "# SKU", "outlet_count": "# SM"},
            format_cols={"revenue": "vnd"},
        )

    with col_bar:
        bar_data = overview.copy()
        colors_bar = ["#ff6b6b" if t == "Combo" else "#4c6ef5"
                      for t in bar_data["is_combo"]]
        fig_bar = go.Figure(go.Bar(
            x=bar_data["is_combo"], y=bar_data["revenue"],
            marker_color=colors_bar,
            text=bar_data["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=12),
        ))
        chart_with_data(
            fig=fig_bar, df=bar_data, filename="ctkm_bar",
            title="So sánh Doanh số Combo vs Non-Combo", height=300,
            display_cols={"is_combo": "Loại", "revenue": "Doanh số (VND)",
                          "qty": "SL", "sku_count": "# SKU", "outlet_count": "# SM"},
            format_cols={"revenue": "vnd"},
        )

    # ── Trend theo ngày: Combo vs Non-Combo ────────────────────────────────────
    st.markdown("---")
    section_header("📈 Xu hướng Combo vs Non-Combo theo ngày")

    if not daily.empty:
        piv_daily = daily.pivot_table(
            index="report_date", columns="is_combo",
            values="revenue", aggfunc="sum", fill_value=0,
        ).reset_index()
        for col in ["Combo", "Non-Combo"]:
            if col not in piv_daily.columns:
                piv_daily[col] = 0
        piv_daily["Combo_MA7"] = piv_daily["Combo"].rolling(
            7, min_periods=1).mean()
        piv_daily["NonCombo_MA7"] = piv_daily["Non-Combo"].rolling(
            7, min_periods=1).mean()

        fig_trend = go.Figure()
        fig_trend.add_bar(
            x=piv_daily["report_date"], y=piv_daily["Non-Combo"],
            name="Non-Combo", marker_color="#4c6ef5", opacity=0.7,
        )
        fig_trend.add_bar(
            x=piv_daily["report_date"], y=piv_daily["Combo"],
            name="Combo", marker_color="#ff6b6b", opacity=0.85,
        )
        fig_trend.add_scatter(
            x=piv_daily["report_date"], y=piv_daily["Combo_MA7"],
            name="Combo MA7", line=dict(color="#ff5b5b", width=2, dash="dot"),
            mode="lines",
        )
        fig_trend.add_scatter(
            x=piv_daily["report_date"], y=piv_daily["NonCombo_MA7"],
            name="Non-Combo MA7", line=dict(color="#339af0", width=2, dash="dot"),
            mode="lines",
        )
        chart_with_data(
            fig=fig_trend, df=piv_daily, filename="ctkm_daily_trend",
            title="Doanh số Combo vs Non-Combo theo ngày (+ MA7)", height=320,
            display_cols={"report_date": "Ngày", "Combo": "Combo (VND)",
                          "Non-Combo": "Non-Combo (VND)",
                          "Combo_MA7": "Combo MA7", "NonCombo_MA7": "Non-Combo MA7"},
            format_cols={"Combo": "vnd", "Non-Combo": "vnd",
                         "Combo_MA7": "vnd", "NonCombo_MA7": "vnd"},
        )

    # ── So sánh giữa các SM được chọn ─────────────────────────────────────────
    st.markdown("---")
    section_header("🏪 So sánh Combo giữa các Siêu thị được chọn")

    if not by_outlet.empty:
        # Side-by-side: mỗi SM = 2 cột Combo / Non-Combo
        piv_sm = by_outlet.pivot_table(
            index=["supermarket_code", "supermarket_name"],
            columns="is_combo", values="revenue",
            aggfunc="sum", fill_value=0,
        ).reset_index()
        for col in ["Combo", "Non-Combo"]:
            if col not in piv_sm.columns:
                piv_sm[col] = 0
        piv_sm["Tổng"] = piv_sm["Combo"] + piv_sm["Non-Combo"]
        piv_sm["Combo%"] = piv_sm["Combo"] / piv_sm["Tổng"] * 100
        piv_sm = piv_sm.sort_values("Tổng", ascending=False)

        # Grouped bar
        fig_sm = go.Figure()
        fig_sm.add_bar(
            name="Non-Combo", x=piv_sm["supermarket_name"], y=piv_sm["Non-Combo"],
            marker_color="#4c6ef5",
            text=piv_sm["Non-Combo"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#8b8fa8", size=9),
        )
        fig_sm.add_bar(
            name="Combo", x=piv_sm["supermarket_name"], y=piv_sm["Combo"],
            marker_color="#ff6b6b",
            text=piv_sm["Combo"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=9),
        )
        fig_sm.update_layout(barmode="group")
        chart_with_data(
            fig=fig_sm, df=piv_sm, filename="ctkm_by_outlet",
            title="Doanh số Combo vs Non-Combo theo Siêu thị", height=320,
            display_cols={
                "supermarket_name": "Siêu thị", "Non-Combo": "Non-Combo (VND)",
                "Combo": "Combo (VND)", "Tổng": "Tổng (VND)", "Combo%": "Tỷ lệ Combo (%)",
            },
            format_cols={"Non-Combo": "vnd", "Combo": "vnd",
                         "Tổng": "vnd", "Combo%": "float"},
        )

        # Heatmap: Combo% theo SM
        st.markdown("<br>", unsafe_allow_html=True)
        piv_share = by_outlet.pivot_table(
            index="supermarket_name", columns="is_combo",
            values="share_pct", aggfunc="sum", fill_value=0,
        ).reset_index()
        for col in ["Combo", "Non-Combo"]:
            if col not in piv_share.columns:
                piv_share[col] = 0
        piv_share = piv_share.sort_values("Combo", ascending=False)

        fig_heat = go.Figure(go.Bar(
            x=piv_share["Combo"], y=piv_share["supermarket_name"],
            orientation="h", marker_color="#ff6b6b",
            text=piv_share["Combo"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside", textfont=dict(color="#ff6b6b", size=10),
            hovertemplate="<b>%{y}</b><br>Combo: %{x:.1f}%<extra></extra>",
        ))
        chart_with_data(
            fig=fig_heat, df=piv_share, filename="ctkm_combo_pct_outlet",
            title="Tỷ lệ Combo (%) theo Siêu thị", height=260,
            display_cols={"supermarket_name": "Siêu thị", "Combo": "Combo (%)",
                          "Non-Combo": "Non-Combo (%)"},
            format_cols={"Combo": "float", "Non-Combo": "float"},
        )

    # ── Combo theo danh mục ───────────────────────────────────────────────────
    st.markdown("---")
    section_header("📂 Tỷ trọng Combo theo Danh mục")

    if not by_cat.empty:
        piv_cat = by_cat.pivot_table(
            index="category", columns="is_combo",
            values="revenue", aggfunc="sum", fill_value=0,
        ).reset_index()
        for col in ["Combo", "Non-Combo"]:
            if col not in piv_cat.columns:
                piv_cat[col] = 0
        piv_cat["Tổng"] = piv_cat["Combo"] + piv_cat["Non-Combo"]
        piv_cat["Combo%"] = piv_cat["Combo"] / piv_cat["Tổng"] * 100
        piv_cat = piv_cat.sort_values("Tổng", ascending=False)

        # Stacked bar
        fig_cat = go.Figure()
        fig_cat.add_bar(
            name="Non-Combo", x=piv_cat["category"], y=piv_cat["Non-Combo"],
            marker_color="#4c6ef5",
        )
        fig_cat.add_bar(
            name="Combo", x=piv_cat["category"], y=piv_cat["Combo"],
            marker_color="#ff6b6b",
        )
        fig_cat.update_layout(barmode="relative")
        chart_with_data(
            fig=fig_cat, df=piv_cat, filename="ctkm_by_category",
            title="Doanh số Combo vs Non-Combo theo Danh mục (stacked)", height=300,
            display_cols={"category": "Danh mục", "Combo": "Combo (VND)",
                          "Non-Combo": "Non-Combo (VND)", "Tổng": "Tổng (VND)",
                          "Combo%": "Combo (%)"},
            format_cols={"Combo": "vnd", "Non-Combo": "vnd",
                         "Tổng": "vnd", "Combo%": "float"},
        )

        # Cột % Combo theo danh mục
        fig_catpct = go.Figure(go.Bar(
            x=piv_cat["category"], y=piv_cat["Combo%"],
            marker_color=[
                "#ff6b6b" if p > 10 else "#7950f2" if p > 5 else "#4c6ef5"
                for p in piv_cat["Combo%"]
            ],
            text=piv_cat["Combo%"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig_catpct, df=piv_cat, filename="ctkm_combo_pct_cat",
            title="Tỷ lệ Combo (%) theo Danh mục", height=280,
            display_cols={"category": "Danh mục", "Combo": "Combo (VND)",
                          "Non-Combo": "Non-Combo (VND)", "Combo%": "Combo (%)"},
            format_cols={"Combo": "vnd",
                         "Non-Combo": "vnd", "Combo%": "float"},
        )

    # ── Top Combo SKU ──────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("🏆 Top Combo SKU — Chi tiết sản phẩm")

    if not top_combo.empty:
        # Chart top combos
        fig_top = go.Figure(go.Bar(
            x=top_combo["revenue"], y=top_combo["sku_name"],
            orientation="h", marker_color="#ff6b6b",
            text=top_combo["revenue"].apply(fmt_vnd),
            textposition="outside", textfont=dict(color="#fff", size=10),
        ))
        chart_with_data(
            fig=fig_top, df=top_combo, filename="ctkm_top_combos",
            title=f"Top {len(top_combo)} Combo SKU theo Doanh số", height=max(260, len(top_combo) * 32),
            display_cols={"sku_name": "Tên SKU", "product_name": "Sản phẩm",
                          "category": "Danh mục", "supermarket_name": "SM bán",
                          "revenue": "Doanh số (VND)", "qty": "SL"},
            format_cols={"revenue": "vnd"},
        )

        # Chọn combo để xem chi tiết sản phẩm
        combo_options = {r["sku_code"]: r["sku_name"]
                         for _, r in all_combos.iterrows()}
        sel_combo_code = st.selectbox(
            "🔍 Chọn Combo để xem chi tiết:",
            options=list(combo_options.keys()),
            format_func=lambda x: f"{combo_options[x]}",
            key="ctkm_combo_detail",
        )

        # Chi tiết combo đã chọn
        sel_combo_detail = all_combos[all_combos["sku_code"] == sel_combo_code]
        if not sel_combo_detail.empty:
            r = sel_combo_detail.iloc[0]
            st.markdown(f"""
            <div style="background:#1e2235;border:1px solid #ff6b6b;border-radius:10px;
                        padding:12px 16px;margin-bottom:12px;">
                <div style="color:#fff;font-size:14px;font-weight:700;margin-bottom:8px;">
                    🎯 <b>{r['sku_name']}</b>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                    <div><div style="color:#8b8fa8;font-size:11px;">Doanh số</div>
                         <div style="color:#ff6b6b;font-size:15px;font-weight:700;">{fmt_vnd(r['revenue'])} VND</div></div>
                    <div><div style="color:#8b8fa8;font-size:11px;">Sản lượng</div>
                         <div style="color:#fff;font-size:15px;font-weight:700;">{int(r['qty']):,}</div></div>
                    <div><div style="color:#8b8fa8;font-size:11px;">Danh mục</div>
                         <div style="color:#fff;font-size:15px;font-weight:700;">{r['category']}</div></div>
                    <div><div style="color:#8b8fa8;font-size:11px;">SKU gốc</div>
                         <div style="color:#fff;font-size:13px;font-weight:500;">{r['product_name']}</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Phân bổ tất cả Combo theo danh mục (treemap)
        combo_by_cat = (
            all_combos.groupby(["category", "sku_name"])["revenue"]
            .sum().reset_index().sort_values("revenue", ascending=False)
        )
        fig_treemap = px.treemap(
            combo_by_cat,
            path=["category", "sku_name"],
            values="revenue",
            color="category",
            color_discrete_sequence=COLOR_SEQ,
            title="Phân bổ Combo theo Danh mục & SKU",
        )
        fig_treemap.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8b8fa8"),
            title=dict(font=dict(color="#fff", size=13)),
        )
        fig_treemap.update_traces(
            texttemplate="<b>%{label}</b><br>%{value:,.0f}",
            textfont=dict(color="#fff", size=10),
            hovertemplate="<b>%{label}</b><br>DS: %{value:,.0f} VND<br>%{percentEntry:.1%}<extra></extra>",
        )
        chart_with_data(
            fig=fig_treemap, df=combo_by_cat, filename="ctkm_treemap",
            title="Phân bổ Combo theo Danh mục & SKU", height=320,
            display_cols={"category": "Danh mục", "sku_name": "Tên SKU",
                          "revenue": "Doanh số (VND)"},
            format_cols={"revenue": "vnd"},
        )

        # Bảng chi tiết đầy đủ tất cả combo
        st.markdown("<br>", unsafe_allow_html=True)
        tbl_combo = top_combo.copy()
        tbl_combo["Combo%"] = tbl_combo["revenue"] / \
            tbl_combo["revenue"].sum() * 100
        tbl_combo = tbl_combo.rename(columns={
            "sku_code": "Mã SKU", "sku_name": "Tên Combo",
            "product_name": "Sản phẩm gốc", "category": "Danh mục",
            "supermarket_name": "SM", "revenue": "Doanh số (VND)",
            "qty": "SL",
        })
        for col in ["Doanh số (VND)"]:
            tbl_combo[col] = tbl_combo[col].apply(lambda x: f"{x:,.0f}")
        tbl_combo["Combo%"] = tbl_combo["Combo%"].apply(lambda x: f"{x:.1f}%")

        col_t, col_b = st.columns([5, 1])
        with col_t:
            st.dataframe(tbl_combo[["Tên Combo", "Sản phẩm gốc", "Danh mục",
                                    "SM", "Doanh số (VND)", "SL", "Combo%"]],
                         width="stretch", hide_index=True)
        with col_b:
            st.markdown("<br><br>", unsafe_allow_html=True)
            download_button(tbl_combo, "ctkm_top_combo_detail", "⬇️ Tải CSV")
    else:
        alert_box("ℹ️ Không có SKU Combo nào trong khoảng thời gian này.", "w")

    # ── Bảng tổng hợp Combo ───────────────────────────────────────────────────
    st.markdown("---")
    section_header("📋 Bảng tổng hợp Combo")

    if not summary_combo.empty:
        tbl_s = summary_combo.copy()
        tbl_s = tbl_s.rename(columns={
            "supermarket_code": "Mã SM",
            "supermarket_name": "Tên SM",
            "sku_code": "Mã Combo",
            "sku_name": "Tên Combo",
            "revenue": "Doanh số (VND)",
            "qty": "SL",
        })
        tbl_s["Doanh số (VND)"] = tbl_s["Doanh số (VND)"].apply(
            lambda x: f"{int(x):,}")
        tbl_s["SL"] = tbl_s["SL"].apply(lambda x: f"{int(x):,}")

        col_tbl, col_btn = st.columns([5, 1])
        with col_tbl:
            st.dataframe(tbl_s, width="stretch", hide_index=True)
        with col_btn:
            st.markdown("<br><br>", unsafe_allow_html=True)
            download_button(tbl_s, "ctkm_summary", "⬇️ Tải CSV")
    else:
        alert_box("ℹ️ Không có dữ liệu Combo.", "w")

    # ── Cảnh báo ──────────────────────────────────────────────────────────────
    st.markdown("---")
    section_header("💡 Nhận xét & Cảnh báo")

    if not by_outlet.empty:
        piv_sm2 = by_outlet.pivot_table(
            index=["supermarket_code", "supermarket_name"],
            columns="is_combo", values="revenue", aggfunc="sum", fill_value=0,
        ).reset_index()
        for col in ["Combo", "Non-Combo"]:
            if col not in piv_sm2.columns:
                piv_sm2[col] = 0
        piv_sm2["Tổng"] = piv_sm2["Combo"] + piv_sm2["Non-Combo"]
        piv_sm2["Combo%"] = piv_sm2["Combo"] / piv_sm2["Tổng"] * 100
        piv_sm2 = piv_sm2.sort_values("Combo%", ascending=False)

        top_combo_sm = piv_sm2.nlargest(3, "Combo%")
        low_combo_sm = piv_sm2[piv_sm2["Combo%"] < 5].nsmallest(3, "Combo%")

        st.markdown("**🔺 Top 3 SM có tỷ lệ Combo cao nhất**")
        for _, r in top_combo_sm.iterrows():
            alert_box(
                f"🏆 <b>{r['supermarket_name']}</b> — "
                f"Combo: <b>{r['Combo%']:.1f}%</b> DS "
                f"({fmt_vnd(r['Combo'])} / {fmt_vnd(r['Tổng'])} VND)", "g")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**🔻 SM có tỷ lệ Combo thấp (< 5%)**")
        if low_combo_sm.empty:
            alert_box("✅ Tất cả SM đều có tỷ lệ Combo ≥ 5%", "g")
        for _, r in low_combo_sm.iterrows():
            alert_box(
                f"⚠️ <b>{r['supermarket_name']}</b> — "
                f"Combo chỉ <b>{r['Combo%']:.1f}%</b> DS "
                f"({fmt_vnd(r['Combo'])} / {fmt_vnd(r['Tổng'])} VND) — "
                f"cần đẩy mạnh CTKM", "w")

    if combo_pct > 15:
        alert_box(
            f"📌 Combo chiếm <b>{combo_pct:.1f}%</b> tổng DS — "
            f"CTKM đang đóng góp đáng kể. Theo dõi biên lợi nhuận.", "w")
    elif combo_pct < 3 and total_rev > 0:
        alert_box(
            f"📌 Combo chỉ chiếm <b>{combo_pct:.1f}%</b> tổng DS — "
            f"CTKM chưa phát huy hiệu quả, cần xem lại chính sách.", "r")


# ── Data loaders (cached via sales.py) ───────────────────────────────────────

def _load_overview(s, e, a, z, sc):
    from queries.sales import get_ctkm_overview
    return get_ctkm_overview(s, e, a, z, sc)


def _load_by_outlet(s, e, a, z, sc):
    from queries.sales import get_ctkm_by_outlet
    return get_ctkm_by_outlet(s, e, a, z, sc)


def _load_by_category(s, e, a, z, sc):
    from queries.sales import get_ctkm_by_category
    return get_ctkm_by_category(s, e, a, z, sc)


def _load_daily(s, e, a, z, sc):
    from queries.sales import get_ctkm_daily
    return get_ctkm_daily(s, e, a, z, sc)


def _load_top_combos(s, e, a, z, sc, top_n=10):
    from queries.sales import get_ctkm_top_combos
    return get_ctkm_top_combos(s, e, a, z, sc, top_n=top_n)


def _load_all_combos(s, e, a, z, sc):
    from queries.sales import get_ctkm_all_combos
    return get_ctkm_all_combos(s, e, a, z, sc)


def _load_summary_combo(s, e, a, z, sc):
    from queries.sales import get_ctkm_summary_by_outlet
    return get_ctkm_summary_by_outlet(s, e, a, z, sc)
