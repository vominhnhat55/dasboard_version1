# app.py — entry point
# Chạy: streamlit run app.py
import streamlit as st
from utils.helpers import load_css
from auth.auth import require_login, get_current_user
from components.sidebar import render_sidebar
from queries.sales import get_daily
from tabs import (tab_overview, tab_outlet, tab_product,
                  tab_forecast, tab_category, tab_fc, tab_ctkm)
st.set_page_config(
    page_title="Sales dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()
require_login()
user = get_current_user()
filters = render_sidebar()
with st.spinner("⚡ Đang lấy dữ liệu..."):
    daily_df = get_daily(
        filters["start"], filters["end"],
        filters["area"], filters["zone"], filters["store_codes"],
    )
if daily_df.empty:
    st.warning("⚠️ Không có dữ liệu với bộ lọc hiện tại.")
    st.stop()
st.title("📊 DASHBOARD DOANH SỐ")
st.markdown(
    f"<span style='color:#8b8fa8;font-size:13px;'>"
    f"BigQuery · {filters['start']} → {filters['end']} · "
    f"{daily_df['report_date'].nunique()} ngày · "
    f"Phạm vi: <b style='color:#fff'>"
    f"{user.display_scope if user else 'N/A'}"
    f"</b></span>",
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Tổng quan",
    "🏪 Điểm bán",
    "📦 Sản phẩm",
    "🔮 Dự báo",
    "🎁 CTKM",
])
with tab1:
    tab_overview.render(filters, daily_df)
with tab2:
    tab_outlet.render(filters)
with tab3:
    tab_product.render(filters)
with tab4:
    tab_forecast.render(filters, daily_df)
with tab5:
    tab_ctkm.render(filters)
