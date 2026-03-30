# utils/helpers.py
# ─────────────────────────────────────────────────────────────────────────────

import io
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import PLOTLY_DARK


# ── Format ────────────────────────────────────────────────────────────────────
def fmt_qty(value: float) -> str:
    qty = f"{value:,.0f}"
    return qty.replace(",", ".")


def fmt_vnd(value: float) -> str:
    if value >= 1e9:
        return f"{value / 1e9:.3f}B"
    if value >= 1e6:
        return f"{value / 1e6:.0f}M"
    return f"{value:,.0f}"


def fmt_pct(value: float, sign=True) -> str:
    prefix = "+" if sign and value >= 0 else ""
    return f"{prefix}{value:.1f}%"


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """UTF-8 BOM — Excel mở đúng tiếng Việt."""
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


# ── UI Components ─────────────────────────────────────────────────────────────

def kpi_card(label: str, value: str, sub: str = "", sub_class: str = "neu"):
    sub_html = f'<div class="kpi-sub {sub_class}">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="kpi">
      <div class="kpi-lbl">{label}</div>
      <div class="kpi-val">{value}</div>
      {sub_html}
    </div>""", unsafe_allow_html=True)


def section_header(title: str):
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def alert_box(text: str, kind: str = "r"):
    css_class = {"r": "al-r", "w": "al-w", "g": "al-g"}.get(kind, "al-w")
    st.markdown(
        f'<div class="{css_class}">{text}</div>', unsafe_allow_html=True)


def update_fig(fig: go.Figure, height: int = 300, title: str = "") -> go.Figure:
    fig.update_layout(
        **PLOTLY_DARK,
        height=height,
        title=dict(text=title, font=dict(color="#fff", size=13)),
    )
    return fig


# ── Chart + Download button ───────────────────────────────────────────────────

def _prep_df(df: pd.DataFrame, display_cols: dict, format_cols: dict) -> pd.DataFrame:
    """Đổi tên cột và format số cho CSV/bảng."""
    out = df.copy()
    if display_cols:
        out = out.rename(columns=display_cols)
        out = out[[c for c in display_cols.values() if c in out.columns]]
    if format_cols:
        for col, fmt in format_cols.items():
            col_name = display_cols.get(col, col) if display_cols else col
            if col_name not in out.columns:
                continue
            if fmt == "vnd":
                out[col_name] = out[col_name].apply(
                    lambda x: f"{x:,.0f}" if pd.notna(x) else "")
            elif fmt == "pct":
                out[col_name] = out[col_name].apply(
                    lambda x: f"{x:+.1f}%" if pd.notna(x) else "")
            elif fmt == "int":
                out[col_name] = out[col_name].apply(
                    lambda x: f"{int(x):,}" if pd.notna(x) else "")
            elif fmt == "float":
                out[col_name] = out[col_name].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "")
    return out


def chart_with_data(
    fig:          go.Figure,
    df:           pd.DataFrame,
    filename:     str,
    display_cols: dict = None,
    height:       int = 300,
    title:        str = "",
    format_cols:  dict = None,
):
    """
    Render chart + nút ⬇️ Download CSV nhỏ ở góc phải tiêu đề.
    Không có bảng collapsible — gọn giao diện.
    """
    update_fig(fig, height, title)

    export_df = _prep_df(df, display_cols, format_cols)

    # Tiêu đề chart + nút download cùng hàng
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        if title:
            st.markdown(
                f'<div style="color:#8b8fa8;font-size:12px;'
                f'margin-bottom:-8px;">{title}</div>',
                unsafe_allow_html=True,
            )
    with col_btn:
        st.download_button(
            label="⬇️ CSV",
            data=to_csv_bytes(export_df),
            file_name=f"{filename}.csv",
            mime="text/csv",
            width="stretch",
            help=f"Tải xuống {filename}.csv",
        )

    st.plotly_chart(fig, width="stretch")


def download_button(df: pd.DataFrame, filename: str, label: str = "⬇️ Tải CSV"):
    """Nút download CSV đứng độc lập cho bảng chi tiết."""
    st.download_button(
        label=label,
        data=to_csv_bytes(df),
        file_name=f"{filename}.csv",
        mime="text/csv",
    )


# ── CSS ───────────────────────────────────────────────────────────────────────

def load_css():
    st.markdown("""
    <style>
    html,body,[class*="css"]{font-family:'Segoe UI',sans-serif;}
    .main,.stApp{background:#0f1117;}
    [data-testid="stSidebar"]{background:#12151f;border-right:1px solid #2a2d3e;}
    .block-container{padding:1.5rem 2rem;}

    .kpi{background:linear-gradient(135deg,#1a1d29,#1e2235);
         border:1px solid #2a2d3e;border-radius:12px;
         padding:16px 20px;margin-bottom:8px;}
    .kpi-lbl{color:#8b8fa8;font-size:11px;font-weight:600;
              text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px;}
    .kpi-val{color:#fff;font-size:26px;font-weight:700;line-height:1.1;}
    .kpi-sub{margin-top:4px;font-size:12px;font-weight:500;}
    .pos{color:#00c48c;} .neg{color:#ff5b5b;} .neu{color:#8b8fa8;}

    .sec{color:#fff;font-size:15px;font-weight:700;
         padding:6px 0 12px;border-bottom:1px solid #2a2d3e;margin-bottom:14px;}

    .al-r{background:#2d1b1b;border-left:4px solid #ff5b5b;
          border-radius:6px;padding:9px 13px;margin:4px 0;
          color:#ffaaaa;font-size:12.5px;}
    .al-w{background:#2d2414;border-left:4px solid #ffaa44;
          border-radius:6px;padding:9px 13px;margin:4px 0;
          color:#ffdd99;font-size:12.5px;}
    .al-g{background:#0d2d1f;border-left:4px solid #00c48c;
          border-radius:6px;padding:9px 13px;margin:4px 0;
          color:#88ffcc;font-size:12.5px;}

    .stTabs [data-baseweb="tab-list"]{background:#1a1d29;border-radius:8px;padding:3px;}
    .stTabs [data-baseweb="tab"]{color:#8b8fa8;font-size:13px;}
    .stTabs [aria-selected="true"]{color:#fff!important;
         background:#2a2d3e!important;border-radius:6px;}

    /* Download button nhỏ gọn */
    [data-testid="stDownloadButton"] button {
        background:#1a1d29 !important;
        border:1px solid #2a2d3e !important;
        color:#8b8fa8 !important;
        font-size:11px !important;
        padding:4px 8px !important;
        border-radius:6px !important;
    }
    [data-testid="stDownloadButton"] button:hover {
        border-color:#4c6ef5 !important;
        color:#fff !important;
    }
    </style>
    """, unsafe_allow_html=True)
