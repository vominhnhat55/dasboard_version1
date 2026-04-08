# queries/filters.py
# Xây dựng WHERE clause động từ filter sidebar
# ─────────────────────────────────────────────────────────────────────────────


def build_where(
    start: str,
    end: str,
    area: str           = "Tất cả",
    zone: str           = "Tất cả",
    store_codes: list   = None,
) -> str:
    """
    Trả về chuỗi SQL WHERE bổ sung (không bao gồm type='X').
    store_codes: list of supermarket_code (str). None/"Tất cả" = all stores.

    VD output:
        AND report_date BETWEEN '2026-01-01' AND '2026-03-26'
        AND area = 'KV1'
    """
    if store_codes is None:
        store_codes = ["Tất cả"]

    clause = f"AND report_date BETWEEN '{start}' AND '{end}'"
    if area != "Tất cả":
        clause += f" AND area = '{area}'"
    if zone != "Tất cả":
        clause += f" AND zone = '{zone}'"
    if "Tất cả" not in store_codes and store_codes:
        codes_escaped = "', '".join(store_codes)
        clause += f" AND supermarket_code IN ('{codes_escaped}')"
    return clause
