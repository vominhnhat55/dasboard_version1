# queries/filters.py
# Xây dựng WHERE clause động từ filter sidebar
# ─────────────────────────────────────────────────────────────────────────────


def build_where(
    start: str,
    end: str,
    area: str       = "Tất cả",
    zone: str       = "Tất cả",
    store_code: str = "Tất cả",
) -> str:
    """
    Trả về chuỗi SQL WHERE bổ sung (không bao gồm type='X').

    VD output:
        AND report_date BETWEEN '2026-01-01' AND '2026-03-26'
        AND area = 'KV1'
    """
    clause = f"AND report_date BETWEEN '{start}' AND '{end}'"
    if area       != "Tất cả": clause += f" AND area             = '{area}'"
    if zone       != "Tất cả": clause += f" AND zone             = '{zone}'"
    if store_code != "Tất cả": clause += f" AND supermarket_code = '{store_code}'"
    return clause
