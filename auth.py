"""Tài khoản người dùng của app: đăng ký, đăng nhập, hồ sơ. Lưu trong SQLite (users.db, không đưa lên git).

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
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_FILE = Path(os.environ.get("USERS_DB", Path(__file__).parent / "users.db"))
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
PASSWORD_MIN, PASSWORD_MAX = 8, 72

# Cột hồ sơ được sửa trong trang Tài khoản (đều không bắt buộc)
CONTACT_FIELDS = ["name", "phone", "address_line", "address_commune", "address_province"]
# 6 thuộc tính khách tự khai; Output và Feedback của mô hình lấy từ đơn hàng và đánh giá (orders.py)
SURVEY_FIELDS = ["age", "family_size", "gender", "marital_status", "occupation", "education"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    email            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    phone            TEXT,
    password_hash    TEXT NOT NULL,
    role             TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at       TEXT NOT NULL,
    failed_attempts  INTEGER NOT NULL DEFAULT 0,
    locked_until     TEXT,
    address_line     TEXT,
    address_commune  TEXT,
    address_province TEXT,
    -- 6 thuộc tính của mô hình phân khúc do khách tự khai (giá trị giống bộ dữ liệu), NULL = bỏ trống
    age              INTEGER,
    family_size      INTEGER,
    gender           TEXT,
    marital_status   TEXT,
    occupation       TEXT,
    education        TEXT,
    output           TEXT,     -- không còn dùng (lấy từ đơn hàng), giữ để tương thích users.db cũ
    feedback         TEXT,     -- không còn dùng (lấy từ đánh giá đơn hàng)
    profile_updated_at TEXT
);

-- Đơn hàng: thông tin giao hàng là bản chụp lúc đặt (giống bảng orders của web La Che Fresca)
CREATE TABLE IF NOT EXISTS orders (
    order_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    phone             TEXT NOT NULL,
    shipping_line     TEXT NOT NULL,
    shipping_commune  TEXT NOT NULL,
    shipping_province TEXT NOT NULL,
    note              TEXT,
    payment_method    TEXT NOT NULL DEFAULT 'cod' CHECK (payment_method IN ('cod', 'bank_transfer')),
    total_amount      INTEGER NOT NULL CHECK (total_amount >= 0),
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'shipping', 'completed', 'cancelled')),
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    -- Đánh giá dịch vụ cho cả đơn (1-5 sao), NULL = chưa đánh giá
    rating            INTEGER CHECK (rating BETWEEN 1 AND 5),
    rating_comment    TEXT,
    rated_at          TEXT,
    day_type          TEXT,     -- weekday (T2-T6) / weekend (T7-CN) lúc đặt
    segment           TEXT      -- cụm của khách lúc đặt (NULL = chưa xếp được), dùng để tạo combo tháng sau
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id, created_at);

-- Chi tiết đơn: mỗi dòng là MỘT MÓN của menu.csv. Món trong combo được tách ra từng món,
-- line_total là thành tiền thực trả (giá combo chia cho các món theo tỷ lệ giá lẻ, tổng đúng bằng giá combo).
CREATE TABLE IF NOT EXISTS order_items (
    line_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    code        TEXT NOT NULL,
    name        TEXT NOT NULL,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  INTEGER NOT NULL CHECK (unit_price >= 0),
    line_total  INTEGER NOT NULL CHECK (line_total >= 0),
    combo_id    TEXT,       -- món thuộc combo nào (NULL = món lẻ)
    combo_name  TEXT,
    combo_qty   INTEGER     -- số phần combo đã đặt
);

-- Combo theo tháng: hệ thống đề xuất từ đơn tháng trước (theo cụm x ngày thường/cuối tuần), admin duyệt
CREATE TABLE IF NOT EXISTS combos (
    combo_id    TEXT PRIMARY KEY,        -- VD: 2026-11-WE-SVD
    month       TEXT NOT NULL,           -- tháng áp dụng YYYY-MM
    day_type    TEXT NOT NULL CHECK (day_type IN ('weekday', 'weekend')),
    segment     TEXT NOT NULL,
    name        TEXT NOT NULL,
    people      TEXT NOT NULL,
    price       INTEGER NOT NULL CHECK (price >= 0),
    offer       TEXT,
    reason      TEXT,
    icon        TEXT,
    status      TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'active', 'rejected')),
    created_at  TEXT NOT NULL,
    approved_at TEXT
);
CREATE TABLE IF NOT EXISTS combo_items (
    combo_id    TEXT NOT NULL REFERENCES combos (combo_id) ON DELETE CASCADE,
    item_id     TEXT NOT NULL,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (combo_id, item_id)
);
"""


def _migrate(conn):
    """Nâng cấp users.db tạo bởi phiên bản trước (thêm cột, đổi cấu trúc order_items) mà không mất dữ liệu."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(orders)")}
    for col in ("day_type", "segment"):
        if col not in cols:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {col} TEXT")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(order_items)")}
    if "line_id" not in cols:
        conn.executescript("""
            ALTER TABLE order_items RENAME TO order_items_old;
            CREATE TABLE order_items (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
                code TEXT NOT NULL, name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
                line_total INTEGER NOT NULL CHECK (line_total >= 0),
                combo_id TEXT, combo_name TEXT, combo_qty INTEGER);
            INSERT INTO order_items (order_id, code, name, quantity, unit_price, line_total)
                SELECT order_id, code, name, quantity, unit_price, quantity * unit_price FROM order_items_old;
            DROP TABLE order_items_old;
        """)


class AuthError(Exception):
    """Lỗi hiển thị được cho người dùng (dữ liệu không hợp lệ, sai mật khẩu...)."""


def connect():
    """Kết nối users.db (tạo bảng nếu chưa có). Dùng chung cho tài khoản và đơn hàng."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


_connect = connect


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
            cur = conn.execute(
                "INSERT INTO users (name, email, phone, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (name, email, phone, hash_password(password), _now().isoformat(" ")))
        except sqlite3.IntegrityError:
            raise AuthError("Email này đã được đăng ký!") from None
        return cur.lastrowid


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
            "INSERT OR IGNORE INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'admin', ?)",
            (name, email.strip().lower(), hash_password(password), _now().isoformat(" ")))
