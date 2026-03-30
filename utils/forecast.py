# utils/forecast.py
# Toàn bộ logic dự báo doanh số
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
import numpy as np
from datetime import timedelta
from config import FORECAST_DAYS, WMA_WINDOW


def compute_wma(revenue: np.ndarray, window: int = WMA_WINDOW) -> float:
    """
    Weighted Moving Average — ngày gần hơn có trọng số cao hơn.

    Công thức:
        n   = min(window, len(revenue))
        w   = linspace(1 → 3, n phần tử)
        WMA = Σ(revenue[-n:] × w) / Σ(w)
    """
    n   = min(window, len(revenue))
    w   = np.linspace(1, 3, n)
    return float(np.average(revenue[-n:], weights=w))


def compute_dow_index(daily_df: pd.DataFrame) -> dict:
    """
    Tính hệ số điều chỉnh theo thứ trong tuần (Day-of-Week index).

    DOW_index[thứ] = DS_TB_ngày_đó / DS_TB_toàn_kỳ

    VD: DOW_index[5] = 1.30  →  T7 cao hơn TB 30%
    """
    global_mean = daily_df["revenue"].mean()
    if global_mean == 0:
        return {i: 1.0 for i in range(7)}
    dow_avg = daily_df.groupby("dow")["revenue"].mean()
    return (dow_avg / global_mean).to_dict()


def forecast_next_n_days(
    daily_df: pd.DataFrame,
    fc_growth_pct: float,
    n_days: int = FORECAST_DAYS,
) -> pd.DataFrame:
    """
    Dự báo N ngày tiếp theo.

    Công thức mỗi ngày d:
        FC[d] = WMA × DOW_index[thứ(d)] × (1 + fc_growth_pct / 100)

    Args:
        daily_df:       DataFrame có cột [report_date, revenue, dow]
        fc_growth_pct:  % kỳ vọng tăng trưởng (từ sidebar)
        n_days:         số ngày cần dự báo

    Returns:
        DataFrame [date, forecast]
    """
    if len(daily_df) < 3:
        return pd.DataFrame(columns=["date", "forecast"])

    wma      = compute_wma(daily_df["revenue"].values)
    dow_idx  = compute_dow_index(daily_df)
    last_day = daily_df["report_date"].max()

    rows = []
    for i in range(1, n_days + 1):
        d      = last_day + timedelta(days=i)
        factor = dow_idx.get(d.dayofweek, 1.0)
        rows.append({
            "date":     d,
            "forecast": wma * factor * (1 + fc_growth_pct / 100),
        })
    return pd.DataFrame(rows)


def estimate_month_forecast(
    actual_revenue: float,
    daily_df: pd.DataFrame,
    fc_growth_pct: float,
    month_end: pd.Timestamp,
) -> float:
    """
    Ước tính tổng doanh số tháng = thực tế đã có + dự báo ngày còn lại.

        FC_tháng = DS_thực_tế + FC_TB/ngày × số_ngày_còn_lại
    """
    last_day      = daily_df["report_date"].max()
    remain_days   = max(0, (month_end - last_day).days)
    wma           = compute_wma(daily_df["revenue"].values)
    daily_fc_avg  = wma * (1 + fc_growth_pct / 100)
    return actual_revenue + daily_fc_avg * remain_days
