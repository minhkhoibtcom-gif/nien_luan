"""Tạo tài khoản khách để test (mặc định 100), xóa được bằng --delete.

Mỗi tài khoản lấy hồ sơ của một người ngẫu nhiên trong dataset (data/genz_vn.xlsx): tuổi (số ngẫu nhiên trong nhóm
tuổi), nhóm thu nhập, giới tính, hôn nhân, học vấn. Thái độ và Ý định đặt tiếp không lưu trong hồ sơ mà app suy ra
từ đơn hàng, nên script tạo đơn hàng sao cho suy ra gần đúng điểm khảo sát của người đó:
- Ý định < 3,75 -> 1 đơn cũ (40–90 ngày trước); 3,75–5,25 -> 1 đơn trong 30 ngày; > 5,25 -> 2–3 đơn trong 30 ngày.
- Mọi đơn đã Hoàn tất và được đánh giá số sao gần nhất với Thái độ (sao = 1 + (Thái độ - 1) / 1,5).
Mỗi đơn là combo gợi ý cho cụm của người đó (cỡ theo số người thường đặt).

Ghi vào database app đang dùng (Supabase nếu .streamlit/secrets.toml có mục [postgres], ngược lại users.db).
Email dạng khach001@test.local, cùng mật khẩu TEST_PASSWORD bên dưới.

    python seed_test_accounts.py            # tạo 100 tài khoản (bỏ qua email đã có)
    python seed_test_accounts.py 30         # tạo 30 tài khoản
    python seed_test_accounts.py --status-orders  # thêm 3–4 đơn Chờ xác nhận, Đang giao, Đã hủy cho tài khoản test
    python seed_test_accounts.py --delete   # xóa mọi tài khoản @test.local cùng đơn hàng của họ
"""
import random
import sys
from datetime import datetime, timedelta

import pandas as pd

import auth
import combos
import db
import orders
from menu import load_menu
from segmentation import AGE_GROUPS, ATT, CAT_COLS, DATA_FILE, INT, NUM_COLS, load_customers, predict, train

DOMAIN = "test.local"
TEST_PASSWORD = "Test@12345"
SEED = 2026

LAST = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Võ", "Đặng", "Bùi", "Đỗ", "Ngô", "Dương", "Lý"]
MIDDLE = {"Nam": ["Văn", "Minh", "Quốc", "Hoàng", "Đức", "Gia"], "Nữ": ["Thị", "Ngọc", "Thu", "Bảo", "Khánh", "Mỹ"]}
FIRST = {"Nam": ["An", "Bình", "Khoa", "Huy", "Phúc", "Tuấn", "Long", "Nam", "Khôi", "Đạt", "Hiếu", "Tài"],
         "Nữ": ["Anh", "Linh", "Trang", "Vy", "Nhi", "Hân", "Thảo", "Uyên", "Mai", "Hương", "Ngân", "Yến"]}
ADDRESSES = [("Ninh Kiều", "Cần Thơ"), ("Cái Răng", "Cần Thơ"), ("Bình Thủy", "Cần Thơ"),
             ("Quận 1", "TP. Hồ Chí Minh"), ("Thủ Đức", "TP. Hồ Chí Minh"), ("Bình Thạnh", "TP. Hồ Chí Minh")]
# Số người thường đặt theo cụm (giống simulate_orders.py)
PARTY = {"Sinh viên thu nhập thấp": [1, 1, 1, 2, 2, 3], "Người đi làm thu nhập khá": [2, 2, 3, 3, 4, 4],
         "Khách trung thành": [1, 1, 2, 2, 3]}


def age_from_group(raw_group, rng):
    lo, hi = (int(x) for x in AGE_GROUPS[raw_group][0].split("–"))
    return rng.randint(lo, hi)


def plan_orders(intention, rng, now):
    """Ngày tạo các đơn sao cho Ý định suy ra gần với điểm khảo sát."""
    if intention < 3.75:
        return [now - timedelta(days=rng.randint(40, 90))]
    n = 1 if intention <= 5.25 else rng.randint(2, 3)
    return sorted(now - timedelta(days=rng.randint(1, 29), hours=rng.randint(0, 10)) for _ in range(n))


def stars_from_attitude(attitude):
    return min(5, max(1, round(1 + (attitude - 1) / 1.5)))


def create(n):
    rng = random.Random(SEED)
    model = train()
    df = load_customers()
    raw_age = pd.read_excel(DATA_FILE)["Q27"]  # nhóm tuổi gốc, để chọn tuổi trong nhóm
    df["Cụm"] = predict(model, df[NUM_COLS + CAT_COLS])
    now = datetime.now().replace(microsecond=0)
    made, skipped = 0, 0
    for i, idx in enumerate(rng.sample(range(len(df)), n), start=1):
        row = df.loc[idx]
        email = f"khach{i:03d}@{DOMAIN}"
        gender = row["Giới tính"]
        name = f"{rng.choice(LAST)} {rng.choice(MIDDLE[gender])} {rng.choice(FIRST[gender])}"
        phone = "09" + "".join(rng.choice("0123456789") for _ in range(8))
        commune, province = rng.choice(ADDRESSES)
        line = f"{rng.randint(1, 300)} đường số {rng.randint(1, 30)}"
        party = rng.choice(PARTY[row["Cụm"]])
        try:
            user_id = auth.register(name, email, TEST_PASSWORD, TEST_PASSWORD, phone)
        except auth.AuthError:
            skipped += 1
            continue
        auth.update_profile(user_id, {
            "name": name, "phone": phone, "address_line": line, "address_commune": commune,
            "address_province": province, "age": age_from_group(raw_age[idx], rng),
            "income": row["Nhóm thu nhập"], "gender": gender, "marital_status": row["Hôn nhân"],
            "education": row["Học vấn"], "party_size": party})

        combo = combos.pick_for(row["Cụm"], party)
        stars = stars_from_attitude(row[ATT])
        form = {"name": name, "phone": phone, "shipping_line": line, "shipping_commune": commune,
                "shipping_province": province, "payment_method": "cod"}
        for when in plan_orders(row[INT], rng, now):
            code = combo.combo_id if combo else "G01"
            order_id = orders.place_order(user_id, {code: 1}, [code], form, segment=row["Cụm"])
            stamp = when.isoformat(" ")
            with db.connect() as conn:
                conn.execute("UPDATE orders SET status = 'completed', created_at = ?, updated_at = ?, day_type = ?,"
                             " rating = ?, rated_at = ? WHERE order_id = ?",
                             (stamp, stamp, combos.day_type(when.date()), stars, stamp, order_id))
        made += 1
        print(f"{email}: {row['Cụm']} ({party} người, {stars} sao)")
    print(f"\nĐã tạo {made} tài khoản, bỏ qua {skipped} email đã có. Database: {db.describe()}")


def status_orders():
    """Thêm 3–4 đơn cho mỗi trạng thái Chờ xác nhận, Đang giao, Đã hủy (đơn Hoàn tất đã có từ lúc tạo tài khoản),
    đặt bởi các tài khoản test ngẫu nhiên. Đơn chờ / đang giao là đơn hôm nay; đơn hủy trong 1–20 ngày trước."""
    import shared  # user_values dùng được ngoài Streamlit
    from segmentation import predict_partial
    rng = random.Random()
    model = train()
    users = [u for u in auth.all_customers() if u["email"].endswith(f"@{DOMAIN}")]
    if not users:
        sys.exit("Chưa có tài khoản test, chạy python seed_test_accounts.py trước.")
    extras = list(load_menu().query("group != 'Món chính'")["item_id"])
    now = datetime.now().replace(microsecond=0)
    for status in ("pending", "shipping", "cancelled"):
        for u in rng.sample(users, rng.randint(3, 4)):
            segment, _ = predict_partial(model, shared.user_values(u))
            combo = combos.pick_for(segment, u["party_size"])
            cart = {combo.combo_id if combo else "G01": 1}
            if rng.random() < 0.5:
                cart[rng.choice(extras)] = rng.randint(1, 2)
            form = {"name": u["name"], "phone": u["phone"], "shipping_line": u["address_line"],
                    "shipping_commune": u["address_commune"], "shipping_province": u["address_province"],
                    "payment_method": rng.choice(["cod", "bank_transfer"])}
            order_id = orders.place_order(u["user_id"], cart, list(cart), form, segment=segment)
            when = now - (timedelta(days=rng.randint(1, 20)) if status == "cancelled"
                          else timedelta(minutes=rng.randint(5, 240)))
            stamp = when.isoformat(" ")
            with db.connect() as conn:
                conn.execute("UPDATE orders SET status = ?, created_at = ?, updated_at = ?, day_type = ? "
                             "WHERE order_id = ?", (status, stamp, stamp, combos.day_type(when.date()), order_id))
            print(f"{orders.order_code(order_id)} {orders.STATUS_LABEL[status]}: {u['email']} ({segment})")
    print(f"Database: {db.describe()}")


def delete():
    with db.connect() as conn:
        n = conn.execute("DELETE FROM users WHERE role = 'user' AND email LIKE ?", (f"%@{DOMAIN}",)).rowcount
    print(f"Đã xóa {n} tài khoản @{DOMAIN} (đơn hàng của họ bị xóa theo). Database: {db.describe()}")


if __name__ == "__main__":
    if "--delete" in sys.argv:
        delete()
    elif "--status-orders" in sys.argv:
        status_orders()
    else:
        nums = [a for a in sys.argv[1:] if a.isdigit()]
        create(int(nums[0]) if nums else 100)
