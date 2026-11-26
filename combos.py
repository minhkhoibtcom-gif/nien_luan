"""Combo theo tháng: đề xuất từ số lượng món mà mỗi cụm mua vào ngày thường / cuối tuần của tháng trước.

Quy trình mỗi tháng M:
1. Gom đơn tháng M-1: đơn thật trong database (đã lưu cụm và loại ngày lúc đặt, bỏ đơn đã hủy)
   và đơn mô phỏng trong simulated_orders.csv (nếu có của tháng đó).
   Cỡ đơn (số người) = số phần món chính trong đơn (mỗi người một món chính).
2. Mỗi cụm có 3 combo: 2 combo NGÀY THƯỜNG theo 2 cỡ đơn phổ biến nhất của ngày thường, và 1 combo CUỐI TUẦN
   theo cỡ đơn phổ biến nhất của cuối tuần. Mỗi combo được dựng từ các đơn cùng cụm, cùng loại ngày, cùng cỡ
   (cần từ MIN_ORDERS đơn), theo các ràng buộc:
   - Món chính (gà giòn, mì Ý, cơm, burger): đúng bằng số người, tối đa 2 loại (2 món được mua nhiều nhất).
   - Thức uống: đúng bằng số người và cùng một loại (loại được mua nhiều nhất).
   - Món thêm (khoai, súp): số phần trung bình mỗi đơn, làm tròn, tối đa 2 loại; Cơm trắng và Mì Ý thêm
     không bao giờ có trong combo (menu.NOT_IN_COMBO).
   - Món phụ (tráng miệng): số phần trung bình làm tròn, không quá số người, tối đa 2 loại; 2 cụm sinh viên
     (thu nhập thấp) không có món phụ.
3. Giá combo = giá lẻ giảm 10%, làm tròn xuống giá đuôi 5.000₫ / 9.000₫. Lưu thành đề xuất (status = proposed).
4. Admin duyệt (có thể sửa giá) -> active. Combo ngày thường đặt được MỌI NGÀY (cả cuối tuần); combo cuối tuần
   chỉ đặt được Thứ 7-CN (ngày thường vẫn xem được). Sang tháng mới cần đề xuất + duyệt lại; chưa duyệt thì
   tạm dùng combo đã duyệt gần nhất, chưa từng duyệt thì dùng combo mặc định (menu.DEFAULT_COMBOS).
"""
import math
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

import auth
from menu import DEFAULT_COMBOS, NOT_IN_COMBO, Combo, list_price, load_menu, pick_default_combo

SIMULATED_FILE = Path(__file__).parent / "simulated_orders.csv"
MIN_ORDERS = 20
MAX_KINDS = 2                      # tối đa 2 loại món chính / món thêm / món phụ trong một combo
COMBOS_PER_DAY = {"weekday": 2, "weekend": 1}

DAY_LABEL = {"weekday": "Combo ngày thường (áp dụng mọi ngày)", "weekend": "Combo cuối tuần (Thứ 7–CN)",
             "all": "Mọi ngày"}
DAY_SHORT = {"weekday": "Mọi ngày", "weekend": "Thứ 7–CN", "all": "Mọi ngày"}
SEGMENT_CODE = {"Sinh viên hộ nhỏ": "SVN", "Sinh viên hộ đông": "SVD",
                "Người đi làm trẻ": "DLT", "Người có gia đình hộ đông": "GD"}
SEGMENT_NAME = {"Sinh viên hộ nhỏ": "Sinh Viên", "Sinh viên hộ đông": "Hội Bạn",
                "Người đi làm trẻ": "Dân Văn Phòng", "Người có gia đình hộ đông": "Cả Nhà"}
LOW_INCOME = {"Sinh viên hộ nhỏ", "Sinh viên hộ đông"}  # ~62% chưa có thu nhập: combo không có món phụ
DISCOUNT = 0.10  # mọi combo giảm 10% so với giá lẻ, rồi làm tròn xuống giá đuôi 5k / 9k (charm_price)
SEGMENT_OFFER = {
    "Sinh viên hộ nhỏ": "Giảm thêm khi có thẻ sinh viên, miễn phí giao hàng.",
    "Sinh viên hộ đông": "",
    "Người đi làm trẻ": "Cam kết giao đúng giờ.",
    "Người có gia đình hộ đông": "Tặng voucher 50.000₫ cho đơn sau, hoàn tiền nếu giao trễ.",
}
ICON = {("Sinh viên hộ nhỏ", "weekday"): "🎒", ("Sinh viên hộ nhỏ", "weekend"): "🍔",
        ("Sinh viên hộ đông", "weekday"): "👥", ("Sinh viên hộ đông", "weekend"): "🎉",
        ("Người đi làm trẻ", "weekday"): "💼", ("Người đi làm trẻ", "weekend"): "🌙",
        ("Người có gia đình hộ đông", "weekday"): "🏠", ("Người có gia đình hộ đông", "weekend"): "👨‍👩‍👧‍👦"}


# ---------- Ngày / tháng ----------

def day_type(d=None):
    return "weekend" if (d or date.today()).weekday() >= 5 else "weekday"


def current_month(d=None):
    return (d or date.today()).strftime("%Y-%m")


def previous_month(month):
    first = datetime.strptime(month + "-01", "%Y-%m-%d").date()
    return (first - timedelta(days=1)).strftime("%Y-%m")


def month_label(month):
    return f"{month[5:]}/{month[:4]}"


# ---------- Dữ liệu đơn hàng để tạo combo ----------

def order_lines(month, menu=None):
    """Dòng món của đơn tháng `month`: order_key, segment, day_type, item_id, quantity, source (thật / mô phỏng),
    size (cỡ đơn = số phần món chính của đơn, tối thiểu 1)."""
    menu = load_menu() if menu is None else menu
    frames = []
    with auth.connect() as conn:
        rows = conn.execute(
            "SELECT o.order_id, o.segment, o.day_type, i.code, i.quantity "
            "FROM orders o JOIN order_items i ON i.order_id = o.order_id "
            "WHERE o.status <> 'cancelled' AND o.segment IS NOT NULL AND o.day_type IS NOT NULL "
            "AND substr(o.created_at, 1, 7) = ?", (month,)).fetchall()
    real = pd.DataFrame([tuple(r) for r in rows],
                        columns=["order_key", "segment", "day_type", "item_id", "quantity"])
    if not real.empty:
        real["order_key"] = "R" + real["order_key"].astype(str)
        frames.append(real.assign(source="thật"))
    if SIMULATED_FILE.is_file():
        sim = pd.read_csv(SIMULATED_FILE)
        sim = sim[sim["created_at"].str[:7] == month]
        if not sim.empty:
            frames.append(sim.rename(columns={"order_id": "order_key"})[
                ["order_key", "segment", "day_type", "item_id", "quantity"]].assign(source="mô phỏng"))
    cols = ["order_key", "segment", "day_type", "item_id", "quantity", "source", "size"]
    if not frames:
        return pd.DataFrame(columns=cols)
    lines = pd.concat(frames, ignore_index=True)
    is_main = lines["item_id"].map(menu.set_index("item_id")["group"]).eq("Món chính")
    size = (lines["quantity"] * is_main).groupby(lines["order_key"]).sum().clip(lower=1).astype(int)
    lines["size"] = lines["order_key"].map(size)
    return lines


def cell_summary(lines):
    """Số đơn (thật / mô phỏng) của từng ô cụm x loại ngày."""
    if lines.empty:
        return pd.DataFrame(columns=["segment", "day_type", "orders", "real", "simulated"])
    orders = lines.drop_duplicates("order_key")
    g = orders.groupby(["segment", "day_type"])
    return pd.DataFrame({"orders": g.size(),
                         "real": g["source"].apply(lambda s: int((s == "thật").sum())),
                         "simulated": g["source"].apply(lambda s: int((s == "mô phỏng").sum()))}).reset_index()


def size_summary(lines, segment, dtype):
    """Số đơn theo cỡ đơn (số người) của một ô cụm x loại ngày."""
    orders = lines[(lines["segment"] == segment) & (lines["day_type"] == dtype)].drop_duplicates("order_key")
    return orders["size"].value_counts().sort_index()


def item_averages(lines, segment, dtype, menu=None, size=None):
    """Trung bình số phần mỗi món trên một đơn của ô (cụm, loại ngày[, cỡ đơn]), kèm nhóm món."""
    menu = load_menu() if menu is None else menu
    cell = lines[(lines["segment"] == segment) & (lines["day_type"] == dtype)]
    if size is not None:
        cell = cell[cell["size"] == size]
    n = cell["order_key"].nunique()
    if n == 0:
        return n, pd.DataFrame(columns=["item_id", "name", "group", "category", "avg"])
    avg = (cell.groupby("item_id")["quantity"].sum() / n).rename("avg").reset_index()
    avg = avg.merge(menu[["item_id", "name", "group", "category"]], on="item_id")
    return n, avg.sort_values("avg", ascending=False).reset_index(drop=True)


def _allocate(total, weights):
    """Chia `total` phần cho các món theo trọng số (phương pháp phần dư lớn nhất)."""
    raw = [total * w / sum(weights) for w in weights]
    base = [math.floor(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)[:total - sum(base)]:
        base[i] += 1
    return base


def _pick(avg, group, total):
    """total phần cho nhóm món `group`, chia cho tối đa MAX_KINDS món được mua nhiều nhất (bỏ món NOT_IN_COMBO)."""
    rows = avg[(avg["group"] == group) & ~avg["item_id"].isin(NOT_IN_COMBO)].head(MAX_KINDS)
    if total < 1 or rows.empty:
        return []
    return [(i, int(q)) for i, q in zip(rows["item_id"], _allocate(total, list(rows["avg"]))) if q > 0]


def charm_price(price):
    """Làm tròn xuống giá gần nhất có hàng nghìn là 5 hoặc 9 (…5.000₫ / …9.000₫), vd 102.600 → 99.000."""
    k = int(price) // 1000
    while k > 0 and k % 10 not in (5, 9):
        k -= 1
    return max(k, 1) * 1000


def build_combo(segment, dtype, size, slot, month, n, avg, menu, source_note):
    """Combo cho đơn cỡ `size` người của ô (cụm, loại ngày), theo ràng buộc ở đầu file."""
    mains = _pick(avg, "Món chính", size)
    drinks = _pick(avg, "Thức uống", 1)
    if not mains or not drinks:
        return None
    drinks = [(drinks[0][0], size)]                                       # đủ số người, cùng một loại
    addons = _pick(avg, "Món thêm", round(avg[(avg["group"] == "Món thêm")
                                             & ~avg["item_id"].isin(NOT_IN_COMBO)]["avg"].sum()))
    sides = [] if segment in LOW_INCOME else _pick(
        avg, "Món phụ", min(size, round(avg[avg["group"] == "Món phụ"]["avg"].sum())))
    items = tuple(mains + addons + sides + drinks)

    draft = Combo("", "", segment, "", items, 0, "", "", "")
    list_total = list_price(draft, menu)
    price = charm_price(list_total * (1 - DISCOUNT))
    names = menu.set_index("item_id")["name"]
    day_txt = "ngày thường" if dtype == "weekday" else "cuối tuần"
    code = f"{'WD' if dtype == 'weekday' else 'WE'}{slot}"
    offer = ("Áp dụng mọi ngày." if dtype == "weekday" else "Chỉ áp dụng Thứ 7–CN.") + " " + SEGMENT_OFFER[segment]
    return Combo(
        combo_id=f"{month}-{code}-{SEGMENT_CODE[segment]}",
        name=f"{SEGMENT_NAME[segment]} {'Ngày Thường' if dtype == 'weekday' else 'Cuối Tuần'} {size} Người",
        segment=segment, people=f"{size} người", items=items, price=price, offer=offer.strip(),
        reason=(f"Từ {n} đơn {size} người vào {day_txt} tháng {month_label(previous_month(month))} của cụm {segment} "
                f"({source_note}); món chính mua nhiều nhất: {', '.join(names[i] for i, _ in mains)}; "
                f"thức uống: {names[drinks[0][0]]}. Giảm {DISCOUNT:.0%} so với giá lẻ, làm tròn xuống giá đuôi 5k/9k "
                f"(thực giảm {1 - price / list_total:.0%})."),
        icon=ICON[(segment, dtype)], day_type=dtype, month=month, status="proposed")


def suggest(month):
    """Tạo đề xuất combo cho tháng `month` từ đơn tháng trước (chưa lưu). Trả về (danh sách combo, lines)."""
    menu = load_menu()
    lines = order_lines(previous_month(month), menu)
    combos = []
    if lines.empty:
        return combos, lines
    for segment in SEGMENT_CODE:
        for dtype, k in COMBOS_PER_DAY.items():
            sizes = size_summary(lines, segment, dtype)
            sizes = sizes[sizes >= MIN_ORDERS].sort_values(ascending=False).head(k)
            for slot, size in enumerate(sorted(sizes.index), start=1):
                cell = lines[(lines["segment"] == segment) & (lines["day_type"] == dtype) & (lines["size"] == size)]
                n, avg = item_averages(lines, segment, dtype, menu, size)
                real = cell[cell["source"] == "thật"]["order_key"].nunique()
                note = f"{real} đơn thật, {n - real} đơn mô phỏng"
                combo = build_combo(segment, dtype, int(size), slot if k > 1 else "", month, n, avg, menu, note)
                if combo:
                    combos.append(combo)
    return combos, lines


# ---------- Lưu / duyệt ----------

def _now():
    return datetime.now().replace(microsecond=0).isoformat(" ")


# combo đang hiển thị được nhớ tạm (đỡ truy vấn lặp lại khi database ở xa); ghi / duyệt combo thì xóa ngay
CACHE_SECONDS = 60
_displayed_cache = {}


def _invalidate():
    _displayed_cache.clear()


def save_proposals(month, combos):
    """Ghi đề xuất mới của tháng (thay đề xuất chưa duyệt cũ; combo đã duyệt giữ nguyên)."""
    _invalidate()
    with auth.connect() as conn:
        conn.execute("DELETE FROM combos WHERE month = ? AND status <> 'active'", (month,))
        active = {r[0] for r in conn.execute("SELECT combo_id FROM combos WHERE month = ?", (month,))}
        for c in combos:
            if c.combo_id in active:
                continue
            conn.execute("INSERT INTO combos (combo_id, month, day_type, segment, name, people, price, offer, reason,"
                         " icon, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?)",
                         (c.combo_id, month, c.day_type, c.segment, c.name, c.people, c.price, c.offer, c.reason,
                          c.icon, _now()))
            conn.executemany("INSERT INTO combo_items (combo_id, item_id, quantity, line_no) VALUES (?, ?, ?, ?)",
                             [(c.combo_id, i, q, n) for n, (i, q) in enumerate(c.items)])


def clear_month(month):
    """Xóa toàn bộ combo của tháng (kể cả đã duyệt) để tạo lại theo quy tắc mới. Đơn đã đặt không bị ảnh hưởng
    vì order_items lưu từng món và tên combo riêng."""
    _invalidate()
    with auth.connect() as conn:
        conn.execute("DELETE FROM combos WHERE month = ?", (month,))


def _load(where, params):
    with auth.connect() as conn:
        rows = conn.execute(f"SELECT * FROM combos WHERE {where} ORDER BY combo_id", params).fetchall()
        items = {}
        for r in conn.execute("SELECT combo_id, item_id, quantity FROM combo_items WHERE combo_id IN "
                              f"(SELECT combo_id FROM combos WHERE {where}) ORDER BY combo_id, line_no", params):
            items.setdefault(r["combo_id"], []).append((r["item_id"], r["quantity"]))
    order = {s: i for i, s in enumerate(SEGMENT_CODE)}
    combos = [Combo(r["combo_id"], r["name"], r["segment"], r["people"], tuple(items.get(r["combo_id"], [])),
                    r["price"], r["offer"] or "", r["reason"] or "", r["icon"] or "🍽️",
                    r["day_type"], r["month"], r["status"]) for r in rows]
    return sorted(combos, key=lambda c: (c.month or "", order.get(c.segment, 9), c.day_type != "weekday",
                                         int(c.people.split()[0]) if c.people[:1].isdigit() else 0))


def month_combos(month, status=None):
    if status:
        return _load("month = ? AND status = ?", (month, status))
    return _load("month = ?", (month,))


def approve(combo_id, price=None):
    _invalidate()
    with auth.connect() as conn:
        if price is not None:
            conn.execute("UPDATE combos SET price = ? WHERE combo_id = ?", (int(price), combo_id))
        conn.execute("UPDATE combos SET status = 'active', approved_at = ? WHERE combo_id = ?", (_now(), combo_id))


def reject(combo_id):
    _invalidate()
    with auth.connect() as conn:
        conn.execute("UPDATE combos SET status = 'rejected' WHERE combo_id = ?", (combo_id,))


def ensure_proposals(month=None):
    """Đầu tháng: chưa có combo nào của tháng thì tự tạo đề xuất (admin vẫn phải duyệt)."""
    month = month or current_month()
    if not month_combos(month):
        save_proposals(month, suggest(month)[0])


# ---------- Combo đang áp dụng cho khách ----------

def displayed(today=None):
    """(combo đang hiển thị, tháng của bộ combo hoặc None nếu dùng combo mặc định).
    Ưu tiên combo đã duyệt của tháng này; chưa có thì combo đã duyệt gần nhất; chưa từng duyệt thì mặc định."""
    month = current_month(today)
    hit = _displayed_cache.get(month)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return list(hit[1]), hit[2]
    shown, shown_month = month_combos(month, "active"), month
    if not shown:
        with auth.connect() as conn:
            row = conn.execute("SELECT MAX(month) FROM combos WHERE status = 'active' AND month < ?",
                               (month,)).fetchone()
        if row and row[0]:
            shown, shown_month = month_combos(row[0], "active"), row[0]
        else:
            shown, shown_month = list(DEFAULT_COMBOS), None
    _displayed_cache[month] = (time.monotonic(), shown, shown_month)
    return list(shown), shown_month


def get(combo_id, today=None):
    """Combo đang hiển thị theo mã (None nếu đã hết hạn / không còn áp dụng)."""
    return next((c for c in displayed(today)[0] if c.combo_id == combo_id), None)


def is_available(combo, today=None):
    """Combo ngày thường và combo mặc định đặt được mọi ngày; combo cuối tuần chỉ đặt được Thứ 7-CN."""
    return combo is not None and (combo.day_type != "weekend" or day_type(today) == "weekend")


def for_segment(segment, today=None):
    return [c for c in displayed(today)[0] if c.segment == segment]


def pick_for(segment, family_size=None, today=None):
    """Combo gợi ý cho khách hôm nay: trong các combo của cụm đặt được hôm nay, chọn combo có số người gần
    số người trong hộ nhất (bỏ trống thì lấy combo nhỏ nhất); cuối tuần ưu tiên combo cuối tuần khi bằng nhau."""
    combos, month = displayed(today)
    if month is None:
        return pick_default_combo(segment, family_size)
    mine = [c for c in combos if c.segment == segment and is_available(c, today)]
    if not mine:
        return None

    def people(c):
        return int(c.people.split()[0]) if c.people[:1].isdigit() else 1

    target = family_size or min(people(c) for c in mine)
    return min(mine, key=lambda c: (abs(people(c) - target), c.day_type != "weekend"))
