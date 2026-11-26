"""Chép toàn bộ dữ liệu từ SQLite users.db sang PostgreSQL (chạy một lần khi chuyển sang database cloud).

Chạy (PowerShell), URL lấy từ biến môi trường DATABASE_URL hoặc [postgres] url trong .streamlit/secrets.toml:
    venv\\Scripts\\python migrate_to_postgres.py                 # chép users.db
    venv\\Scripts\\python migrate_to_postgres.py --source khac.db
    venv\\Scripts\\python migrate_to_postgres.py --replace       # xóa dữ liệu đang có trên PostgreSQL rồi chép

- File users.db không bị sửa: dữ liệu được nạp vào bộ nhớ và nâng cấp cấu trúc ở đó trước khi chép.
- Giữ nguyên mã (user_id, order_id...) để đơn hàng vẫn khớp với tài khoản; sau đó chỉnh bộ đếm tự tăng.
- Nếu PostgreSQL đã có dữ liệu (ngoài tài khoản admin tự tạo) thì dừng, trừ khi thêm --replace.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import db


def load_source(path):
    if not Path(path).is_file():
        sys.exit(f"Không thấy file {path}")
    src = sqlite3.connect(path)
    mem = sqlite3.connect(":memory:")
    src.backup(mem)
    src.close()
    mem.row_factory = sqlite3.Row
    mem.executescript(db.schema("sqlite"))  # bảng còn thiếu thì tạo rỗng
    db._migrate_sqlite(mem)
    return mem


def columns(conn, table):
    return [r[0] for r in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=str(db.SQLITE_FILE), help="file SQLite nguồn (mặc định users.db)")
    parser.add_argument("--replace", action="store_true", help="xóa dữ liệu đang có trên PostgreSQL trước khi chép")
    args = parser.parse_args()

    if db.BACKEND != "postgres":
        sys.exit("Chưa cấu hình PostgreSQL: đặt biến môi trường DATABASE_URL hoặc thêm vào .streamlit/secrets.toml\n"
                 '[postgres]\nurl = "postgresql://user:password@host:5432/postgres"')
    src = load_source(args.source)
    print(f"Nguồn: {args.source}  ->  Đích: {db.describe()}")

    with db.connect() as conn:  # lần kết nối đầu tiên tự tạo bảng trên PostgreSQL
        users = conn.execute("SELECT COUNT(*) FROM users WHERE role <> 'admin'").fetchone()[0]
        n_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        n_combos = conn.execute("SELECT COUNT(*) FROM combos").fetchone()[0]
        if (users or n_orders or n_combos) and not args.replace:
            sys.exit(f"PostgreSQL đã có dữ liệu ({users} khách, {n_orders} đơn, {n_combos} combo). "
                     "Thêm --replace nếu muốn xóa và chép lại.")
        conn.execute("TRUNCATE " + ", ".join(db.TABLES) + " RESTART IDENTITY CASCADE")

        for table in db.TABLES:
            cols = [c for c in columns(src, table) if c in columns(conn, table)]
            rows = [tuple(r[c] for c in cols) for r in src.execute(f"SELECT * FROM {table}")]
            if rows:
                conn.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                                 rows)
            print(f"  {table:12} {len(rows):6} dòng")

        for table, col in db.ID_COLUMNS.items():  # bộ đếm tự tăng tiếp tục sau mã lớn nhất đã chép
            conn.execute(f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                         f"COALESCE((SELECT MAX({col}) FROM {table}), 0) + 1, false)")
    print("Xong.")


if __name__ == "__main__":
    main()
