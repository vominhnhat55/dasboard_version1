# auth/auth.py
# Authentication + RBAC — user lưu trong secrets.toml
# Không cần BigQuery, không cần deploy lại khi đổi password
# ─────────────────────────────────────────────────────────────────────────────
#
# 3 roles:
#   superadmin   → xem tất cả
#   area_manager → chỉ xem area + zone trong area đó
#   zone_manager → chỉ xem zone + điểm bán trong zone đó
#
# ─────────────────────────────────────────────────────────────────────────────

import hashlib
import streamlit as st
from dataclasses import dataclass
from typing import Optional


# ── User dataclass ─────────────────────────────────────────────────────────
@dataclass
class User:
    username:  str
    full_name: str
    role:      str            # 'superadmin' | 'area_manager' | 'zone_manager'
    area:      Optional[str]  # KV1 | KV2
    zone:      Optional[str]  # V1/TB, V2/TSG, ...

    @property
    def is_superadmin(self) -> bool: return self.role == "superadmin"
    @property
    def is_area_manager(self) -> bool: return self.role == "area_manager"
    @property
    def is_zone_manager(self) -> bool: return self.role == "zone_manager"

    @property
    def display_scope(self) -> str:
        if self.is_superadmin:
            return "SUPERADMIN"
        if self.is_area_manager:
            return f"Khu vực {self.area}"
        return f"Zone {self.zone}"


# ── Password hashing ────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ── Đọc danh sách user từ secrets.toml ─────────────────────────────────────


def _get_users() -> dict:
    """
    Đọc block [users] từ secrets.toml.
    Mỗi user là 1 sub-table: [users.username]
    """
    return st.secrets.get("users", {})


def _find_user(username: str) -> Optional[dict]:
    users = _get_users()
    return users.get(username.strip().lower())


# ── Login logic ─────────────────────────────────────────────────────────────
def login(username: str, password: str) -> tuple[bool, str]:
    if not username or not password:
        return False, "Vui lòng nhập đầy đủ thông tin."

    row = _find_user(username)
    if row is None:
        return False, "Tài khoản không tồn tại."
    if not row.get("is_active", True):
        return False, "Tài khoản đã bị vô hiệu hóa. Liên hệ admin."
    if row.get("password_hash") != hash_password(password):
        return False, "Mật khẩu không đúng."

    st.session_state["user"] = User(
        username=username.strip().lower(),
        full_name=row.get("full_name", username),
        role=row.get("role", "zone_manager"),
        area=row.get("area"),
        zone=row.get("zone"),
    )
    return True, ""


def logout():
    st.session_state.pop("user", None)
    st.rerun()


def get_current_user() -> Optional[User]:
    return st.session_state.get("user")


def require_login():
    """Gọi đầu app.py — chưa login thì chặn lại."""
    if get_current_user() is None:
        _render_login_page()
        st.stop()

# ── Login page UI ───────────────────────────────────────────────────────────


def _render_login_page():
    st.markdown("""
    <style>
    html,body,[class*="css"]{font-family:'Segoe UI',sans-serif;}
    .main,.stApp{background:#0f1117;}
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a1d29,#1e2235);
                    border:1px solid #2a2d3e;border-radius:16px;padding:40px 36px;
                    text-align:center;">
            <div style="font-size:40px;">📊</div>
            <div style="color:#fff;font-size:22px;font-weight:700;margin:8px 0 4px;">
                DASHBOARD DOANH SỐ
            </div>
            <div style="color:#8b8fa8;font-size:13px;">
                Đăng nhập để truy cập dashboard
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("👤 Tên đăng nhập", placeholder="username")
            password = st.text_input(
                "🔒 Mật khẩu", type="password", placeholder="••••••••")
            submitted = st.form_submit_button(
                "Đăng nhập →", use_container_width=True)

        if submitted:
            with st.spinner("Đang xác thực..."):
                ok, err = login(username, password)
            if ok:
                st.rerun()
            else:
                st.error(f"❌ {err}")
