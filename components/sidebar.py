# components/sidebar.py
# Sidebar filters — tích hợp RBAC
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
from datetime import timedelta

from config import (
    BQ_TABLE,
    DEFAULT_FC_GROWTH, DEFAULT_ALERT_PCT, DEFAULT_TOP_N, DEFAULT_LOOKBACK,
)
from auth.auth import get_current_user, logout
from queries.sales import get_date_range, get_filter_options


def render_sidebar() -> dict:
    """
    Render sidebar và trả về filters đã được áp dụng quyền user.
    Zone manager sẽ không thể thay đổi area/zone của mình.
    """
    user = get_current_user()

    with st.sidebar:
        _render_user_info(user)
        st.markdown("---")
        st.markdown("## ⚙️ Bộ lọc & Cài đặt")
        st.markdown("---")

        # Date range
        with st.spinner("Đang tải..."):
            mn, mx = get_date_range()

        default_start = max(mn, mx - timedelta(days=DEFAULT_LOOKBACK))
        dr = st.date_input(
            "📅 Khoảng ngày",
            value=(default_start, mx),
            min_value=mn, max_value=mx,
        )
        start = str(dr[0]) if len(dr) == 2 else str(mn)
        end = str(dr[1]) if len(dr) == 2 else str(mx)

        # Area / Zone / Category
        opts = get_filter_options()
        sel_area, sel_zone, sel_cat = _render_dimension_filters(user, opts)

        # Forecast settings
        st.markdown("---")
        st.markdown("### 🔮 Dự báo & Cảnh báo")
        fc_pct = st.slider("Tăng trưởng FC (%)", -30, 60, DEFAULT_FC_GROWTH)
        alert_pct = st.slider(
            "Ngưỡng cảnh báo sụt giảm (%)", -50, -5, DEFAULT_ALERT_PCT)
        top_n = st.slider("Top N điểm bán / SP", 5, 30, DEFAULT_TOP_N)

        st.markdown("---")
        if st.button("🔄 Refresh data", width="stretch"):
            st.cache_data.clear()
            st.rerun()

        st.caption(f"📦 Nguồn: BigQuery · {BQ_TABLE}")

    return {
        "start":     start,
        "end":       end,
        "area":      sel_area,
        "zone":      sel_zone,
        "category":  sel_cat,
        "fc_pct":    fc_pct,
        "alert_pct": alert_pct,
        "top_n":     top_n,
    }


def _render_user_info(user):
    """Hiển thị thông tin user + nút logout."""
    role_badge = {
        "superadmin":   ("🔴", "Super Admin"),
        "area_manager": ("🟡", "Quản lý Vùng"),
        "zone_manager": ("🟢", "Quản lý Zone"),
    }.get(user.role, ("⚪", user.role))

    st.markdown(f"""
    <div style="background:#1a1d29;border:1px solid #2a2d3e;border-radius:10px;
                padding:14px 16px;margin-bottom:8px;">
        <div style="color:#fff;font-weight:700;font-size:14px;">
            👤 {user.full_name}
        </div>
        <div style="color:#8b8fa8;font-size:12px;margin-top:4px;">
            {role_badge[0]} {role_badge[1]} · {user.display_scope}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Đăng xuất", width="stretch"):
        logout()


def _render_dimension_filters(user, opts) -> tuple:
    """
    Render area + zone theo role:
    - superadmin   → tự do chọn tất cả
    - area_manager → area cố định, zone tự chọn trong area
    - zone_manager → area + zone đều cố định (disabled)
    """
    if user.is_superadmin:
        areas = ["Tất cả"] + sorted(opts["area"].unique().tolist())
        sel_area = st.selectbox("🗺️ Khu vực", areas)
        z_pool = (opts["zone"].unique() if sel_area == "Tất cả"
                  else opts[opts["area"] == sel_area]["zone"].unique())
        zones = ["Tất cả"] + sorted(z_pool.tolist())
        sel_zone = st.selectbox("📍 Zone", zones)
    elif user.is_area_manager:
        st.selectbox("🗺️ Khu vực", [user.area], disabled=True,
                     help="Bạn chỉ có quyền xem khu vực của mình")
        sel_area = user.area
        z_pool = opts[opts["area"] == user.area]["zone"].unique()
        zones = ["Tất cả"] + sorted(z_pool.tolist())
        sel_zone = st.selectbox("📍 Zone", zones)
    else:  # zone_manager
        st.selectbox("🗺️ Khu vực", [user.area], disabled=True,
                     help="Bạn chỉ có quyền xem khu vực của mình")
        st.selectbox("📍 Zone", [user.zone], disabled=True,
                     help="Bạn chỉ có quyền xem zone của mình")
        sel_area = user.area
        sel_zone = user.zone

    cats = ["Tất cả"] + sorted(opts["category"].unique().tolist())
    sel_cat = st.selectbox("🏷️ Danh mục", cats)

    return sel_area, sel_zone, sel_cat
