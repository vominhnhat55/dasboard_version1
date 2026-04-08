# queries/sales.py
# Tất cả BigQuery queries — mỗi hàm = 1 mục đích rõ ràng
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
import streamlit as st
from config import BQ_PROJECT, BQ_TABLE, CACHE_TTL
from queries.bq_client import run_query
from queries.filters import build_where


# ── Meta queries ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_date_range() -> tuple:
    """Trả về (min_date, max_date) của toàn bộ dữ liệu."""
    sql = f"""
        SELECT
            MIN(report_date) AS min_date,
            MAX(report_date) AS max_date
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X'
    """
    df = run_query(sql)
    return (
        pd.to_datetime(df["min_date"].iloc[0]).date(),
        pd.to_datetime(df["max_date"].iloc[0]).date(),
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_filter_options() -> pd.DataFrame:
    """
    Load tất cả giá trị unique cho dropdown sidebar.
    Chỉ query 1 lần — dùng cho area, zone, category.
    """
    sql = f"""
        SELECT DISTINCT area, zone, category
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X'
        ORDER BY 1, 2, 3
    """
    return run_query(sql)


# ── Tab Tổng quan ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_daily(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Doanh số theo ngày — dùng cho biểu đồ trend và forecast.
    Columns: report_date, dow (0=Mon), revenue, qty
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            report_date,
            -- BigQuery: 1=Sun → chuyển về 0=Mon chuẩn Python
            MOD(EXTRACT(DAYOFWEEK FROM report_date) + 5, 7) AS dow,
            Sum(quantity*weight) AS qty_kg,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2
        ORDER BY 1
    """
    df = run_query(sql)
    df["report_date"] = pd.to_datetime(df["report_date"])
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_weekly(start, end, area, zone, store_codes) -> pd.DataFrame:
    """Doanh số theo tuần — dùng cho biểu đồ WoW%."""
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            EXTRACT(WEEK(SUNDAY) FROM report_date) AS week,
            SUM(item_total) AS revenue
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1
        ORDER BY 1
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_area_zone(start, end, area, zone, store_codes) -> pd.DataFrame:
    """Doanh số theo area và zone."""
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            area,
            zone,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2
        ORDER BY 3 DESC
    """
    return run_query(sql)


# ── Tab Điểm bán ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_outlet_summary(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Tổng hợp hiệu quả từng điểm bán.

    Columns: supermarket_code, supermarket_name, area, zone,
             revenue, qty, active_days, sku_count, rev_per_day
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            supermarket_code,
            supermarket_name,
            area,
            zone,
            SUM(item_total)                              AS revenue,
            SUM(quantity)                                AS qty,
            COUNT(DISTINCT report_date)                  AS active_days,
            COUNT(DISTINCT sku_code)                     AS sku_count,
            SAFE_DIVIDE(SUM(item_total),
            COUNT(DISTINCT report_date))             AS rev_per_day
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2, 3, 4
        ORDER BY 5 DESC
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_outlet_half_trend(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    So sánh doanh số điểm bán nửa đầu vs nửa sau tháng.
    Dùng để phát hiện điểm bán sụt giảm liên tục.

    Columns: supermarket_code, supermarket_name, first, second, chg (%)
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            supermarket_code,
            supermarket_name,
            CASE WHEN EXTRACT(DAY FROM report_date) <= 13
                 THEN 'first' ELSE 'second' END          AS half,
            SUM(item_total)                              AS revenue
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2, 3
    """
    df = run_query(sql)
    piv = df.pivot_table(
        index=["supermarket_code", "supermarket_name"],
        columns="half", values="revenue",
        aggfunc="sum", fill_value=0,
    ).reset_index()
    piv.columns.name = None
    if "first" not in piv.columns:
        piv["first"] = 0
    if "second" not in piv.columns:
        piv["second"] = 0
    piv["chg"] = (piv["second"] - piv["first"]) / (piv["first"] + 1) * 100
    return piv


# ── Tab Sản phẩm ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_product_summary(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Tổng hợp doanh số theo sản phẩm.

    Columns: product_code, product_name, category,
             revenue, qty, outlets, days, rev_per_day, rev_per_outlet
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            product_code,
            product_name,
            category,
            SUM(item_total)                              AS revenue,
            SUM(quantity)                                AS qty,
            COUNT(DISTINCT supermarket_code)             AS outlets,
            COUNT(DISTINCT report_date)                  AS days,
            SAFE_DIVIDE(SUM(item_total),
                COUNT(DISTINCT report_date))             AS rev_per_day,
            SAFE_DIVIDE(SUM(item_total),
                COUNT(DISTINCT supermarket_code))        AS rev_per_outlet
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2, 3
        ORDER BY 4 DESC
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_sku_summary(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Tổng hợp doanh số theo SKU.

    Columns: sku_code, sku_name, product_name, category,
             revenue, qty, outlets
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            sku_code,
            sku_name,
            product_name,
            category,
            SUM(item_total)                  AS revenue,
            SUM(quantity)                    AS qty,
            COUNT(DISTINCT supermarket_code) AS outlets
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2, 3, 4
        ORDER BY 5 DESC
    """
    return run_query(sql)


# ── Tab Danh mục ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_category_weekly(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Doanh số theo danh mục × tuần.
    Dùng cho biểu đồ trend và tính tăng trưởng.

    Columns: category, week, revenue, qty, outlets, products, skus
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            category,
            EXTRACT(ISOWEEK FROM report_date)            AS week,
            SUM(item_total)                              AS revenue,
            SUM(quantity)                                AS qty,
            COUNT(DISTINCT supermarket_code)             AS outlets,
            COUNT(DISTINCT product_name)                 AS products,
            COUNT(DISTINCT sku_code)                     AS skus
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    return run_query(sql)


# ── FC queries ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_forecast(start, area="Tất cả", zone="Tất cả",
                 store_codes=None) -> pd.DataFrame:
    """
    FC theo tháng từ bảng forecast.
    Lấy toàn bộ FC của năm hiện tại — không filter month cứng
    để tránh mất data khi date range lệch với FC period.

    Bảng forecast chỉ có: supermarket_code, year, month, fc_revenue
    → area/zone lọc qua join với bảng sales (lấy từ MAX 1 record/store).
    """
    start_y = int(pd.to_datetime(start).strftime("%Y"))

    area_filter = f"AND s.area = '{area}'" if area != "Tất cả" else ""
    zone_filter = f"AND s.zone = '{zone}'" if zone != "Tất cả" else ""

    store_filter = ""
    if store_codes and "Tất cả" not in store_codes and store_codes:
        codes_escaped = "', '".join(store_codes)
        store_filter = f"AND f.supermarket_code IN ('{codes_escaped}')"

    sql = f"""
        SELECT
            f.supermarket_code,
            COALESCE(s.area,   '') AS area,
            COALESCE(s.zone,   '') AS zone,
            f.month,
            f.year,
            f.fc_revenue
        FROM (
            SELECT supermarket_code, month, year, SUM(fc_revenue) AS fc_revenue
            FROM `{BQ_PROJECT}.sales_db.forecast`
            WHERE year = {start_y}
            GROUP BY 1, 2, 3
        ) f
        LEFT JOIN (
            SELECT supermarket_code, MAX(area) AS area, MAX(zone) AS zone
            FROM `{BQ_PROJECT}.{BQ_TABLE}`
            WHERE type = 'X'
            GROUP BY 1
        ) s ON f.supermarket_code = s.supermarket_code
        WHERE 1=1 {area_filter} {zone_filter} {store_filter}
        ORDER BY f.supermarket_code, f.month
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_outlet_daily(start, end, area, zone, store_codes=None,
                     outlet_code="Tất cả") -> pd.DataFrame:
    """
    Doanh số TỪNG NGÀY của từng điểm bán — dùng cho drill-down.
    """
    f = build_where(start, end, area, zone, store_codes)
    if outlet_code != "Tất cả":
        f += f" AND supermarket_code = '{outlet_code}'"
    sql = f"""
        SELECT
            supermarket_code,
            supermarket_name,
            report_date,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1,2,3
        ORDER BY 1,3
    """
    df = run_query(sql)
    df["report_date"] = pd.to_datetime(df["report_date"])
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_product_daily(start, end, area, zone, store_codes=None,
                      outlet_code="Tất cả") -> pd.DataFrame:
    """
    Doanh số TỪNG NGÀY của từng sản phẩm — dùng cho drill-down.
    """
    f = build_where(start, end, area, zone, store_codes)
    if outlet_code != "Tất cả":
        f += f" AND supermarket_code = '{outlet_code}'"
    sql = f"""
        SELECT
            product_name,
            category,
            report_date,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1,2,3
        ORDER BY 1,3
    """
    df = run_query(sql)
    df["report_date"] = pd.to_datetime(df["report_date"])
    return df


# ── CTKM queries ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ctkm_overview(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Tổng quan CTKM: so sánh doanh số SKU Combo vs Non-Combo.

    Columns: is_combo, revenue, qty, sku_count, outlet_count, avg_revenue
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            IF(STARTS_WITH(sku_code, 'Combo-'), 'Combo', 'Non-Combo') AS is_combo,
            SUM(item_total)                                    AS revenue,
            SUM(quantity)                                      AS qty,
            COUNT(DISTINCT sku_code)                          AS sku_count,
            COUNT(DISTINCT supermarket_code)                  AS outlet_count,
            AVG(item_total)                                    AS avg_revenue
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ctkm_by_outlet(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Doanh số Combo/Non-Combo theo từng điểm bán.
    Dùng cho so sánh giữa các store được chọn.

    Columns: supermarket_code, supermarket_name, is_combo,
             revenue, qty, share_pct
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            supermarket_code,
            supermarket_name,
            IF(STARTS_WITH(sku_code, 'Combo-'), 'Combo', 'Non-Combo') AS is_combo,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2, 3
        ORDER BY 1, 3
    """
    df = run_query(sql)
    total = df.groupby("supermarket_code")["revenue"].transform("sum")
    df["share_pct"] = df["revenue"] / total * 100
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ctkm_by_category(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Doanh số Combo/Non-Combo theo danh mục.

    Columns: category, is_combo, revenue, qty
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            category,
            IF(STARTS_WITH(sku_code, 'Combo-'), 'Combo', 'Non-Combo') AS is_combo,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2
        ORDER BY 1, 3
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ctkm_daily(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Doanh số Combo vs Non-Combo theo ngày.
    Dùng cho trend chart.

    Columns: report_date, is_combo, revenue, qty
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            report_date,
            IF(STARTS_WITH(sku_code, 'Combo-'), 'Combo', 'Non-Combo') AS is_combo,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        GROUP BY 1, 2
        ORDER BY 1
    """
    df = run_query(sql)
    df["report_date"] = pd.to_datetime(df["report_date"])
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ctkm_top_combos(start, end, area, zone, store_codes, top_n=10) -> pd.DataFrame:
    """
    Top Combo SKU theo doanh số.

    Columns: sku_code, sku_name, product_name, category,
             supermarket_name, revenue, qty
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            sku_code,
            sku_name,
            product_name,
            category,
            supermarket_name,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
          AND STARTS_WITH(sku_code, 'Combo-')
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY 6 DESC
        LIMIT {top_n}
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ctkm_all_combos(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Tất cả Combo SKU — không giới hạn. Dùng cho dropdown và treemap.

    Columns: sku_code, sku_name, product_name, category, revenue, qty
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            sku_code,
            sku_name,
            product_name,
            category,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
          AND STARTS_WITH(sku_code, 'Combo-')
        GROUP BY 1, 2, 3, 4
        ORDER BY 5 DESC
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ctkm_summary_by_outlet(start, end, area, zone, store_codes) -> pd.DataFrame:
    """
    Bảng tổng hợp Combo: theo siêu thị và tên combo.
    Columns: supermarket_code, supermarket_name, sku_code, sku_name, revenue, qty
    """
    f = build_where(start, end, area, zone, store_codes)
    sql = f"""
        SELECT
            supermarket_code,
            supermarket_name,
            sku_code,
            sku_name,
            SUM(item_total) AS revenue,
            SUM(quantity)   AS qty
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
          AND STARTS_WITH(sku_code, 'Combo-')
        GROUP BY 1, 2, 3, 4
        ORDER BY 5 DESC
    """
    return run_query(sql)


# ── Store list ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_store_list(area, zone) -> pd.DataFrame:
    """Danh sách store cho dropdown filter."""
    f = ""
    if area != "Tất cả":
        f += f" AND area = '{area}'"
    if zone != "Tất cả":
        f += f" AND zone = '{zone}'"
    sql = f"""
        SELECT DISTINCT supermarket_code, supermarket_name, area, zone
        FROM `{BQ_PROJECT}.{BQ_TABLE}`
        WHERE type = 'X' {f}
        ORDER BY supermarket_name
    """
    return run_query(sql)
