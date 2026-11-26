"""Tài khoản người dùng của app: đăng ký, đăng nhập, hồ sơ.
Lưu trong database của db.py: SQLite users.db trên máy (không đưa lên git) hoặc PostgreSQL khi có cấu hình.

Quy tắc giống web bán sữa La Che Fresca:
- Mật khẩu 8-72 ký tự, băm bằng scrypt (thư viện chuẩn Python), không lưu mật khẩu gốc.
- Sai mật khẩu MAX_ATTEMPTS lần liên tiếp thì khóa tạm LOCK_MINUTES phút.
- Thông báo lỗi đăng nhập chung chung, không cho biết email có tồn tại hay không.
- Số điện thoại (nếu nhập) gồm 10 chữ số, bắt đầu bằng 0.
Các thông tin hồ sơ (địa chỉ và 8 thuộc tính của mô hình phân khúc) đều không bắt buộc.
"""
import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta

import db

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
PASSWORD_MIN, PASSWORD_MAX = 8, 72

# Cột hồ sơ được sửa trong trang Tài khoản (đều không bắt buộc)
CONTACT_FIELDS = ["name", "phone", "address_line", "address_commune", "address_province"]
# 6 thuộc tính khách tự khai; Output và Feedback của mô hình lấy từ đơn hàng và đánh giá (orders.py)
SURVEY_FIELDS = ["age", "family_size", "gender", "marital_status", "occupation", "education"]

class AuthError(Exception):
    """Lỗi hiển thị được cho người dùng (dữ liệu không hợp lệ, sai mật khẩu...)."""


connect = db.connect  # orders.py, combos.py dùng auth.connect()
_connect = db.connect


def _now():
    return datetime.now().replace(microsecond=0)


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        _, salt, digest = stored.split("$")
        check = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1)
        return hmac.compare_digest(check.hex(), digest)
    except (ValueError, TypeError):
        return False


def validate_password(password, confirm):
    if not PASSWORD_MIN <= len(password.encode()) <= PASSWORD_MAX:
        raise AuthError(f"Mật khẩu phải từ {PASSWORD_MIN} đến {PASSWORD_MAX} ký tự.")
    if password != confirm:
        raise AuthError("Mật khẩu nhập lại không khớp.")


def _clean_phone(phone):
    phone = (phone or "").strip()
    if phone and not re.fullmatch(r"0\d{9}", phone):
        raise AuthError("Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0.")
    return phone or None


def register(name, email, password, confirm, phone=""):
    """Tạo tài khoản khách hàng, trả về user_id."""
    name, email = name.strip(), email.strip().lower()
    if not name:
        raise AuthError("Vui lòng nhập họ tên.")
    if len(name) > 100:
        raise AuthError("Họ tên tối đa 100 ký tự.")
    if len(email) > 100 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise AuthError("Email không hợp lệ.")
    phone = _clean_phone(phone)
    validate_password(password, confirm)
    with _connect() as conn:
        try:
            row = conn.execute(
                "INSERT INTO users (name, email, phone, password_hash, created_at) VALUES (?, ?, ?, ?, ?)"
                " RETURNING user_id",
                (name, email, phone, hash_password(password), _now().isoformat(" "))).fetchone()
        except db.IntegrityError:
            raise AuthError("Email này đã được đăng ký!") from None
        return row[0]


def login(email, password):
    """Trả về user_id nếu đúng; sai thì tăng bộ đếm và khóa tạm khi quá số lần."""
    email = email.strip().lower()
    with _connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        now = _now()
        if user and user["locked_until"] and datetime.fromisoformat(user["locked_until"]) > now:
            remain = -(-(datetime.fromisoformat(user["locked_until"]) - now).seconds // 60)
            raise AuthError(f"Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {remain} phút.")
        if user and verify_password(password, user["password_hash"]):
            conn.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?",
                         (user["user_id"],))
            return user["user_id"]
        if user:
            attempts = user["failed_attempts"] + 1
            if attempts >= MAX_ATTEMPTS:
                conn.execute("UPDATE users SET failed_attempts = 0, locked_until = ? WHERE user_id = ?",
                             ((now + timedelta(minutes=LOCK_MINUTES)).isoformat(" "), user["user_id"]))
            else:
                conn.execute("UPDATE users SET failed_attempts = ? WHERE user_id = ?",
                             (attempts, user["user_id"]))
    raise AuthError("Email hoặc mật khẩu không chính xác!")


def get_user(user_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def all_customers():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM users WHERE role = 'user' ORDER BY user_id").fetchall()
    return [dict(r) for r in rows]


def update_profile(user_id, values):
    """Lưu hồ sơ. Ô bỏ trống lưu NULL; chỉ họ tên là bắt buộc (đã có từ lúc đăng ký)."""
    data = {k: values.get(k) for k in CONTACT_FIELDS + SURVEY_FIELDS}
    for k in CONTACT_FIELDS:
        data[k] = (data[k] or "").strip() or None
    if not data["name"]:
        raise AuthError("Họ tên không được để trống.")
    if len(data["name"]) > 100:
        raise AuthError("Họ tên tối đa 100 ký tự.")
    data["phone"] = _clean_phone(data["phone"])
    for k in ("address_line", "address_commune", "address_province"):
        if data[k] and len(data[k]) > 255:
            raise AuthError("Địa chỉ quá dài.")
    data["profile_updated_at"] = _now().isoformat(" ")
    sets = ", ".join(f"{k} = ?" for k in data)
    with _connect() as conn:
        conn.execute(f"UPDATE users SET {sets} WHERE user_id = ?", (*data.values(), user_id))


def change_password(user_id, old, new, confirm):
    user = get_user(user_id)
    if not user or not verify_password(old, user["password_hash"]):
        raise AuthError("Mật khẩu hiện tại không đúng.")
    validate_password(new, confirm)
    with _connect() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (hash_password(new), user_id))


def ensure_admin(email, password, name="Quản trị viên"):
    """Tạo tài khoản admin lần đầu chạy app (nếu chưa có admin nào)."""
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone():
            return
        conn.execute(
            "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'admin', ?)"
            " ON CONFLICT DO NOTHING",
            (name, email.strip().lower(), hash_password(password), _now().isoformat(" ")))
