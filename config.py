# config.py
# Tất cả constants và cấu hình tập trung tại đây
# ─────────────────────────────────────────────────────────────────────────────

# ── BigQuery ──────────────────────────────────────────────────────────────────
BQ_PROJECT = "sales-nutty"           # GCP Project ID
BQ_TABLE = "sales_db.fact_sales"     # dataset.table  ← đổi tên bảng thật vào đây
# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_TTL = 7200   # seconds — query BigQuery mới sau mỗi 1 tiếng
# ── Business logic ────────────────────────────────────────────────────────────
DEFAULT_FC_GROWTH = 10     # % tăng trưởng forecast mặc định
DEFAULT_ALERT_PCT = -20    # % sụt giảm để cảnh báo đỏ
DEFAULT_TOP_N = 15     # số điểm bán / SP hiển thị mặc định
DEFAULT_LOOKBACK = 60     # số ngày mặc định khi mở dashboard (3 tháng)
LOW_COVERAGE_DAYS = 5      # điểm bán ≤ N ngày → cảnh báo coverage thấp
NARROW_DIST_OUTLETS = 2      # SKU ≤ N điểm bán → cảnh báo phân phối hẹp
LOW_SKU_THRESHOLD = 20     # điểm bán < N SKU → cảnh báo danh mục mỏng
SURGE_THRESHOLD = 30     # % tăng trưởng để coi là "tăng tốt"
TOP5_RISK_PCT = 40     # % doanh số tập trung top 5 SM → cảnh báo rủi ro
HHI_WARNING = 0.25   # HHI > ngưỡng này → cảnh báo tập trung danh mục
# ── Forecast ─────────────────────────────────────────────────────────────────
FORECAST_DAYS = 7      # số ngày dự báo
WMA_WINDOW = 14     # số ngày dùng cho Weighted Moving Average
# ── UI Colors ─────────────────────────────────────────────────────────────────
COLOR_PRIMARY = "#4c6ef5"
COLOR_SUCCESS = "#00c48c"
COLOR_WARNING = "#ffaa44"
COLOR_DANGER = "#ff5b5b"
COLOR_PURPLE = "#7950f2"
COLOR_TEAL = "#15aabf"
COLOR_MUTED = "#8b8fa8"

COLOR_SEQ = [
    "#4c6ef5", "#00c48c", "#ffaa44", "#ff5b5b", "#7950f2",
    "#15aabf", "#f03e3e", "#94d82d", "#f59f00", "#cc5de8",
]

# ── Plotly dark theme ─────────────────────────────────────────────────────────
PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(26,29,41,.6)",
    font=dict(color="#8b8fa8", family="Segoe UI", size=11),
    xaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
    yaxis=dict(gridcolor="#2a2d3e", linecolor="#2a2d3e"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=8, r=8, t=36, b=8),
)
