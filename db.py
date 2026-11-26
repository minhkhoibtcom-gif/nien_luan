"""Kết nối database dùng chung cho tài khoản, đơn hàng và combo.

Hai chế độ, cùng một bộ câu SQL (viết với dấu ? như SQLite):
- SQLite (mặc định): file users.db cạnh code (hoặc đường dẫn trong biến môi trường USERS_DB). Dùng khi chạy trên máy.
- PostgreSQL: khi có biến môi trường DATABASE_URL hoặc mục [postgres] url = "postgresql://..." trong
  .streamlit/secrets.toml (trên Streamlit Cloud: Settings -> Secrets). Dùng để dữ liệu không mất khi app
  khởi động lại (Supabase, Neon...). Ở chế độ này dấu ? được đổi thành %s trước khi gửi tới PostgreSQL.

Dùng:
    with db.connect() as conn:          # thoát khối with: commit (lỗi thì rollback) rồi trả kết nối
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (1,)).fetchone()
        row["email"], row[0], dict(row)   # đọc theo tên cột hoặc vị trí, giống sqlite3.Row
"""
import atexit
import os
import sqlite3
import threading
import time
from decimal import Decimal
from pathlib import Path

SQLITE_FILE = Path(os.environ.get("USERS_DB", Path(__file__).parent / "users.db"))


def _postgres_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        import streamlit as st
        return st.secrets["postgres"]["url"]
    except Exception:  # không có secrets.toml hoặc không có mục [postgres]
        return None


POSTGRES_URL = _postgres_url()
BACKEND = "postgres" if POSTGRES_URL else "sqlite"

if BACKEND == "postgres":
    import psycopg
    from psycopg_pool import ConnectionPool
    IntegrityError = (sqlite3.IntegrityError, psycopg.errors.IntegrityError)
else:
    IntegrityError = (sqlite3.IntegrityError,)


class DatabaseUnavailable(Exception):
    """Không kết nối được database (sai URL, mất mạng, database bị tạm dừng...)."""


# ---------- Schema (một bản cho cả hai hệ, khác nhau ở {ID} và {NOCASE}) ----------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id          {ID},
    name             TEXT NOT NULL,
    email            TEXT NOT NULL UNIQUE {NOCASE},
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
    order_id          {ID},
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
    line_id     {ID},
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
    line_no     INTEGER NOT NULL DEFAULT 0,   -- thứ tự món trong combo (món chính, món thêm, món phụ, thức uống)
    PRIMARY KEY (combo_id, item_id)
);
"""
DIALECT = {
    "sqlite": {"ID": "INTEGER PRIMARY KEY AUTOINCREMENT", "NOCASE": "COLLATE NOCASE"},
    # email luôn được chuyển về chữ thường trước khi lưu và tìm (auth.py) nên không cần COLLATE
    "postgres": {"ID": "INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY", "NOCASE": ""},
}
TABLES = ["users", "orders", "order_items", "combos", "combo_items"]  # thứ tự tạo / chép dữ liệu (theo khóa ngoại)
ID_COLUMNS = {"users": "user_id", "orders": "order_id", "order_items": "line_id"}


def schema(backend=BACKEND):
    return SCHEMA.format(**DIALECT[backend])


def _migrate_sqlite(conn):
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
    cols = {r[1] for r in conn.execute("PRAGMA table_info(combo_items)")}
    if "line_no" not in cols:  # trước đây thứ tự món dựa vào rowid của SQLite
        conn.execute("ALTER TABLE combo_items ADD COLUMN line_no INTEGER NOT NULL DEFAULT 0")
        conn.execute("UPDATE combo_items SET line_no = rowid")


# ---------- Dòng kết quả của PostgreSQL: đọc theo tên cột hoặc vị trí như sqlite3.Row ----------
class Row(tuple):
    def __new__(cls, keys, index, values):
        row = super().__new__(cls, values)
        row._keys, row._index = keys, index
        return row

    def __getitem__(self, key):
        if isinstance(key, str):
            return tuple.__getitem__(self, self._index[key])
        return tuple.__getitem__(self, key)

    def keys(self):
        return list(self._keys)


def _row_factory(cursor):
    if cursor.description is None:
        return tuple
    keys = [c.name for c in cursor.description]
    index = {k: i for i, k in enumerate(keys)}
    # AVG() của PostgreSQL trả về Decimal; đổi sang float cho giống SQLite
    return lambda values: Row(keys, index, tuple(float(v) if isinstance(v, Decimal) else v for v in values))


def _to_postgres(sql):
    return sql.replace("%", "%%").replace("?", "%s")


# ---------- Kết nối ----------
_READ_ONLY = ("SELECT", "WITH")


class Connection:
    """Bọc kết nối SQLite / PostgreSQL với cùng cách gọi execute / executemany / with.

    PostgreSQL ở chế độ autocommit: truy vấn chỉ đọc chạy thẳng (một lượt đi về mạng); câu lệnh ghi đầu tiên
    trong khối with mới mở giao dịch (BEGIN), thoát khối thì COMMIT (lỗi thì ROLLBACK). Nhờ vậy các lệnh ghi
    trong cùng khối vẫn trọn vẹn (vd đơn hàng + chi tiết đơn), còn đọc thì nhanh hơn nhiều với database ở xa.
    SQLite: module sqlite3 cũng chỉ mở giao dịch trước câu lệnh ghi, cách dùng như nhau.
    """

    def __init__(self, raw, release):
        self.raw, self._release, self._in_tx = raw, release, False

    def _begin_if_write(self, sql):
        if not self._in_tx and not sql.lstrip().upper().startswith(_READ_ONLY):
            self.raw.execute("BEGIN")
            self._in_tx = True

    def execute(self, sql, params=()):
        if BACKEND == "sqlite":
            return self.raw.execute(sql, params)
        self._begin_if_write(sql)
        cur = self.raw.cursor()
        cur.execute(_to_postgres(sql), params or None)
        return cur

    def executemany(self, sql, seq):
        if BACKEND == "sqlite":
            return self.raw.executemany(sql, seq)
        self._begin_if_write(sql)
        cur = self.raw.cursor()
        cur.executemany(_to_postgres(sql), list(seq))
        return cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if BACKEND == "sqlite":
                self.raw.commit() if exc_type is None else self.raw.rollback()
            elif self._in_tx:
                self.raw.execute("COMMIT" if exc_type is None else "ROLLBACK")
        finally:
            self._release(self.raw)
        return False


_lock = threading.Lock()
_ready = False
_pool = None
_last_used = {}   # id(kết nối) -> thời điểm trả về pool
IDLE_CHECK_SECONDS = 60


def _sqlite_raw():
    raw = sqlite3.connect(SQLITE_FILE)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return raw


def _check(conn):
    """Pool gọi trước khi đưa kết nối ra: chỉ ping khi kết nối đã rảnh lâu (có thể đã bị máy chủ đóng)."""
    if time.monotonic() - _last_used.get(id(conn), 0) > IDLE_CHECK_SECONDS:
        conn.execute("SELECT 1")


def _put(conn):
    _last_used[id(conn)] = time.monotonic()
    _pool.putconn(conn)


def _get_pool():
    global _pool
    if _pool is None:
        # prepare_threshold=None: không dùng prepared statement, để chạy được qua connection pooler (Supabase, Neon)
        _pool = ConnectionPool(POSTGRES_URL, min_size=1, max_size=5, open=True, timeout=10, check=_check,
                               kwargs={"row_factory": _row_factory, "prepare_threshold": None,
                                       "autocommit": True, "connect_timeout": 10})
        atexit.register(_pool.close)  # đóng pool trước khi Python thoát (tránh lỗi luồng nền lúc tắt)
    return _pool


def _init(raw):
    """Tạo bảng (và nâng cấp users.db cũ) một lần cho mỗi lần chạy app."""
    if BACKEND == "sqlite":
        raw.executescript(schema())
        _migrate_sqlite(raw)
        raw.commit()
    else:
        raw.execute(schema())  # autocommit, không có tham số nên gửi được nhiều câu lệnh một lần


def connect():
    global _ready
    if BACKEND == "sqlite":
        raw, release = _sqlite_raw(), (lambda r: r.close())
    else:
        try:
            raw, release = _get_pool().getconn(), _put
        except Exception as e:  # psycopg.OperationalError, PoolTimeout
            raise DatabaseUnavailable(str(e)) from e
    if not _ready:
        with _lock:
            if not _ready:
                try:
                    _init(raw)
                except Exception:
                    release(raw)
                    raise
                _ready = True
    return Connection(raw, release)


def describe():
    """Mô tả ngắn nơi lưu dữ liệu (hiện trong trang quản trị), không lộ mật khẩu."""
    if BACKEND == "sqlite":
        return f"SQLite ({SQLITE_FILE.name})"
    info = psycopg.conninfo.conninfo_to_dict(POSTGRES_URL)
    return f"PostgreSQL ({info.get('host', '?')}/{info.get('dbname', '?')})"
