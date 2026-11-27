"""Giỏ hàng, đặt hàng, trạng thái đơn và đánh giá (luồng giống web bán sữa La Che Fresca, bỏ phần tồn kho / HSD).

- Giỏ hàng nằm trong st.session_state["cart"]: {mã món hoặc mã combo: số lượng}; phải đăng nhập mới thêm được.
- Đặt hàng: chỉ đặt các món được chọn; giá lấy lại từ thực đơn lúc đặt (không tin giá ở giao diện).
- Trạng thái: pending (Chờ xác nhận) -> shipping (Đang giao) -> completed (Hoàn tất); pending/shipping -> cancelled.
  Khách hủy được đơn đang chờ xác nhận; admin chuyển trạng thái.
- Đánh giá: 1-5 sao cho cả đơn (dịch vụ), hiện ngay sau khi đặt; bỏ qua thì đánh giá sau trong "Đơn hàng của tôi".

Hai thuộc tính của mô hình được suy ra ở đây thay vì hỏi khách (thang 1–7 như khảo sát, None = bỏ qua khi xếp nhóm):
- Thái độ: số sao đánh giá trung bình, đổi từ thang 1–5 sang 1–7 (1 + (sao - 1) x 1,5); chưa đánh giá -> None.
- Ý định đặt tiếp: số đơn chưa hủy trong ACTIVE_DAYS ngày gần nhất: 0 đơn -> 3, 1 đơn -> 4,5, từ 2 đơn -> 6;
  chưa đặt đơn nào -> None. Giả định của đề tài: còn đặt đều nghĩa là có ý định tiếp tục đặt.
Ngoài ra Output (còn đặt trong 30 ngày) và Feedback (sao TB >= POSITIVE_STARS) dùng để chọn ưu đãi giữ chân khách.
"""
import re
from datetime import datetime, timedelta

import math

import auth
import combos
from menu import load_menu

ACTIVE_DAYS = 30
POSITIVE_STARS = 4
INTENTION_BY_RECENT = {0: 3.0, 1: 4.5}   # số đơn trong ACTIVE_DAYS ngày -> Ý định đặt tiếp; từ 2 đơn -> 6
INTENTION_FREQUENT = 6.0
MAX_QTY = 100

STATUS_LABEL = {"pending": "Chờ xác nhận", "shipping": "Đang giao", "completed": "Hoàn tất", "cancelled": "Đã hủy"}
STATUS_COLOR = {"pending": "orange", "shipping": "blue", "completed": "green", "cancelled": "gray"}
NEXT_STATUS = {"pending": ["shipping", "cancelled"], "shipping": ["completed", "cancelled"]}
PAYMENT_LABEL = {"cod": "Thanh toán khi nhận hàng (COD)", "bank_transfer": "Chuyển khoản ngân hàng"}


class OrderError(Exception):
    """Lỗi hiển thị được cho người dùng."""


def _now():
    return datetime.now().replace(microsecond=0)


def order_code(order_id):
    return f"DH{int(order_id):08d}"


def catalog(today=None):
    """{mã: (tên hiển thị, giá)} cho món lẻ và các combo đang hiển thị."""
    items = {r.item_id: (r.name, int(r.price)) for r in load_menu().itertuples()}
    items.update({c.combo_id: (f"Combo {c.name}", c.price) for c in combos.displayed(today)[0]})
    return items


def availability(code, today=None):
    """(đặt được không, ghi chú) cho một mã trong giỏ: combo chỉ đặt được đúng loại ngày của nó."""
    if code in set(load_menu()["item_id"]):  # món lẻ đặt được mọi ngày
        return True, ""
    combo = combos.get(code, today)
    if combo is None:
        return False, "Combo đã hết hạn"
    if not combos.is_available(combo, today):
        return False, f"Chỉ áp dụng {combos.DAY_SHORT[combo.day_type]}"
    return True, ""


# ---------- Giỏ hàng (thao tác trên dict trong session) ----------

def cart_add(cart, code, qty=1, today=None):
    if code not in catalog(today):
        raise OrderError("Món này không còn bán.")
    ok, note = availability(code, today)
    if not ok:
        raise OrderError(f"Combo này {note[0].lower() + note[1:]}, hôm nay chưa đặt được.")
    cart[code] = min(cart.get(code, 0) + max(1, int(qty)), MAX_QTY)


def cart_rows(cart, today=None):
    """Danh sách món trong giỏ kèm tên, đơn giá, thành tiền và có đặt được hôm nay không.
    Combo đã hết hạn (sang tháng mới) được giữ lại nhưng khóa, để khách tự xóa."""
    cat = catalog(today)
    rows = []
    for code, qty in list(cart.items()):
        ok, note = availability(code, today)
        if code not in cat:
            if ok:  # món lẻ không còn trong thực đơn
                del cart[code]
                continue
            rows.append({"code": code, "name": f"Combo {code}", "price": 0, "qty": qty, "subtotal": 0,
                         "available": False, "note": note})
            continue
        rows.append({"code": code, "name": cat[code][0], "price": cat[code][1], "qty": qty,
                     "subtotal": cat[code][1] * qty, "available": ok, "note": note})
    return rows


def _split_price(total, weights):
    """Chia `total` đồng cho các dòng theo trọng số; tổng sau làm tròn đúng bằng total (phần dư lớn nhất)."""
    raw = [total * w / sum(weights) for w in weights]
    base = [math.floor(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)[:total - sum(base)]:
        base[i] += 1
    return base


def order_item_rows(picked, today=None):
    """Đổi các mã trong giỏ thành dòng order_items: món lẻ giữ nguyên; combo tách ra từng món,
    giá combo chia cho các món theo tỷ lệ giá lẻ (tổng các dòng đúng bằng giá combo x số phần)."""
    menu = load_menu().set_index("item_id")
    rows = []
    for code, qty in picked.items():
        if code in menu.index:
            price = int(menu.loc[code, "price"])
            rows.append(dict(code=code, name=menu.loc[code, "name"], quantity=qty, unit_price=price,
                             line_total=price * qty, combo_id=None, combo_name=None, combo_qty=None))
            continue
        combo = combos.get(code, today)
        lines = [(item, q * qty, int(menu.loc[item, "price"])) for item, q in combo.items]
        totals = _split_price(combo.price * qty, [n * p for _, n, p in lines])
        for (item, n, _), line_total in zip(lines, totals):
            rows.append(dict(code=item, name=menu.loc[item, "name"], quantity=n,
                             unit_price=round(line_total / n), line_total=line_total,
                             combo_id=combo.combo_id, combo_name=f"Combo {combo.name}", combo_qty=qty))
    return rows


# ---------- Đặt hàng ----------

def place_order(user_id, cart, selected, form, segment=None, today=None):
    """Tạo đơn từ các món được chọn trong giỏ; trả về order_id. Món đã đặt được bỏ khỏi giỏ.
    segment: cụm của khách lúc đặt (lưu lại để tạo combo tháng sau)."""
    name = (form.get("name") or "").strip()
    phone = (form.get("phone") or "").strip()
    line = (form.get("shipping_line") or "").strip()
    commune = (form.get("shipping_commune") or "").strip()
    province = (form.get("shipping_province") or "").strip()
    note = (form.get("note") or "").strip()
    payment = form.get("payment_method") if form.get("payment_method") in PAYMENT_LABEL else "cod"

    if not (name and line and commune and province):
        raise OrderError("Vui lòng nhập họ tên và đầy đủ địa chỉ giao hàng (số nhà/đường, phường/xã, tỉnh/thành phố).")
    if len(name) > 100 or len(line) > 255 or len(commune) > 100 or len(province) > 100 or len(note) > 500:
        raise OrderError("Thông tin quá dài: họ tên, phường/xã, tỉnh tối đa 100 ký tự, địa chỉ cụ thể 255, ghi chú 500.")
    if not re.fullmatch(r"0\d{9}", phone):
        raise OrderError("Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0.")
    if not cart:
        raise OrderError("Giỏ hàng đang trống.")
    picked = {code: cart[code] for code in selected if code in cart}
    if not picked:
        raise OrderError("Vui lòng chọn ít nhất một món để đặt hàng.")

    cat = catalog(today)  # giá lấy lại từ thực đơn / combo đang áp dụng, không tin giá ở giao diện
    for code in picked:
        ok, why = availability(code, today)
        if code not in cat or not ok:
            raise OrderError(f"\"{cat.get(code, (code,))[0]}\" không đặt được hôm nay ({why or 'không còn bán'}), "
                             "vui lòng bỏ chọn hoặc xóa khỏi giỏ.")
    lines = order_item_rows(picked, today)
    total = sum(r["line_total"] for r in lines)
    now = _now().isoformat(" ")
    with auth.connect() as conn:
        order_id = conn.execute(
            "INSERT INTO orders (user_id, name, phone, shipping_line, shipping_commune, shipping_province, note,"
            " payment_method, total_amount, status, created_at, updated_at, day_type, segment)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?) RETURNING order_id",
            (user_id, name, phone, line, commune, province, note or None, payment, total, now, now,
             combos.day_type(today), segment)).fetchone()[0]
        conn.executemany(
            "INSERT INTO order_items (order_id, code, name, quantity, unit_price, line_total, combo_id, combo_name,"
            " combo_qty) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(order_id, r["code"], r["name"], r["quantity"], r["unit_price"], r["line_total"], r["combo_id"],
              r["combo_name"], r["combo_qty"]) for r in lines])
    for code in picked:  # chỉ bỏ những món vừa đặt, món chưa chọn vẫn giữ trong giỏ
        del cart[code]
    return order_id


# ---------- Xem / đổi trạng thái đơn ----------

def _attach_items(conn, orders):
    """Gắn chi tiết món cho các đơn bằng một truy vấn (không phải một truy vấn cho mỗi đơn)."""
    items = {o["order_id"]: [] for o in orders}
    ids = list(items)
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        for r in conn.execute(
                "SELECT order_id, code, name, quantity, unit_price, line_total, combo_id, combo_name, combo_qty "
                f"FROM order_items WHERE order_id IN ({', '.join('?' * len(chunk))}) ORDER BY line_id", chunk):
            row = dict(r)
            items[row.pop("order_id")].append(row)
    for o in orders:
        o["items"] = items[o["order_id"]]
    return orders


def display_lines(order):
    """Các dòng hiển thị của đơn: món trong combo gom lại dưới tên combo. Trả về [(tiêu đề, chi tiết, thành tiền)]."""
    out, groups = [], {}
    for i in order["items"]:
        if i["combo_id"]:
            key = (i["combo_id"], i["combo_name"], i["combo_qty"])
            if key not in groups:
                groups[key] = []
                out.append(key)
            groups[key].append(i)
        else:
            out.append(i)
    rows = []
    for entry in out:
        if isinstance(entry, tuple):
            items = groups[entry]
            rows.append((f"{entry[2]} × {entry[1]}", ", ".join(f"{i['quantity']} {i['name']}" for i in items),
                         sum(i["line_total"] for i in items)))
        else:
            rows.append((f"{entry['quantity']} × {entry['name']}", "", entry["line_total"]))
    return rows


def user_orders(user_id):
    with auth.connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC, order_id DESC", (user_id,))]
        return _attach_items(conn, rows)


def get_order(order_id):
    with auth.connect() as conn:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        return _attach_items(conn, [dict(row)])[0] if row else None


def all_orders(status="all", query=""):
    """Đơn cho admin: lọc trạng thái, tìm theo mã đơn / tên / SĐT người nhận."""
    sql, params = "SELECT o.*, u.email FROM orders o JOIN users u ON u.user_id = o.user_id WHERE 1 = 1", []
    if status in STATUS_LABEL:
        sql += " AND o.status = ?"
        params.append(status)
    query = query.strip()
    if query:
        digits = re.sub(r"\D", "", query.upper().removeprefix("DH"))
        # LOWER: LIKE của PostgreSQL phân biệt hoa thường, của SQLite thì không
        sql += " AND (LOWER(o.name) LIKE LOWER(?) OR o.phone LIKE ?" + (" OR o.order_id = ?" if digits else "") + ")"
        params += [f"%{query}%", f"%{query}%"] + ([int(digits)] if digits else [])
    sql += " ORDER BY o.created_at DESC, o.order_id DESC"
    with auth.connect() as conn:
        return _attach_items(conn, [dict(r) for r in conn.execute(sql, params)])


def order_stats():
    with auth.connect() as conn:
        counts = dict(conn.execute("SELECT status, COUNT(*) FROM orders GROUP BY status").fetchall())
        revenue = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'completed'").fetchone()[0]
    return counts, revenue


def cancel_order(user_id, order_id):
    """Khách hủy đơn của mình khi đơn còn chờ xác nhận."""
    with auth.connect() as conn:
        cur = conn.execute("UPDATE orders SET status = 'cancelled', updated_at = ? "
                           "WHERE order_id = ? AND user_id = ? AND status = 'pending'",
                           (_now().isoformat(" "), order_id, user_id))
        if cur.rowcount != 1:
            raise OrderError("Chỉ có thể hủy đơn đang chờ xác nhận.")


def set_status(order_id, new_status):
    """Admin chuyển trạng thái theo NEXT_STATUS."""
    with auth.connect() as conn:
        row = conn.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row or new_status not in NEXT_STATUS.get(row["status"], []):
            raise OrderError("Không thể chuyển đơn sang trạng thái này.")
        conn.execute("UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ? AND status = ?",
                     (new_status, _now().isoformat(" "), order_id, row["status"]))


# ---------- Đánh giá ----------

def rate_order(user_id, order_id, stars, comment=""):
    stars = int(stars)
    if not 1 <= stars <= 5:
        raise OrderError("Vui lòng chọn từ 1 đến 5 sao.")
    comment = (comment or "").strip()
    if len(comment) > 500:
        raise OrderError("Góp ý tối đa 500 ký tự.")
    with auth.connect() as conn:
        cur = conn.execute("UPDATE orders SET rating = ?, rating_comment = ?, rated_at = ? "
                           "WHERE order_id = ? AND user_id = ? AND rating IS NULL",
                           (stars, comment or None, _now().isoformat(" "), order_id, user_id))
        if cur.rowcount != 1:
            raise OrderError("Đơn hàng không tồn tại hoặc đã được đánh giá.")


# ---------- Hành vi -> thuộc tính của mô hình ----------

def stars_to_attitude(avg_stars):
    """Sao trung bình 1–5 -> điểm Thái độ 1–7."""
    return None if avg_stars is None else round(1 + (float(avg_stars) - 1) * 1.5, 2)


def recent_to_intention(total_orders, recent_orders):
    """Số đơn trong ACTIVE_DAYS ngày -> điểm Ý định đặt tiếp 1–7 (chưa từng đặt -> None)."""
    if not total_orders:
        return None
    return INTENTION_BY_RECENT.get(recent_orders, INTENTION_FREQUENT)


def behavior(user_id, today=None):
    """Số đơn, đơn gần nhất, sao trung bình và các thuộc tính suy ra cho mô hình (None = bỏ qua)."""
    today = today or _now()
    since = (today - timedelta(days=ACTIVE_DAYS)).isoformat(" ")
    with auth.connect() as conn:
        n, last, recent = conn.execute(
            "SELECT COUNT(*), MAX(created_at), SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) FROM orders "
            "WHERE user_id = ? AND status <> 'cancelled'", (since, user_id)).fetchone()
        avg, rated = conn.execute("SELECT AVG(rating), COUNT(rating) FROM orders WHERE user_id = ?",
                                  (user_id,)).fetchone()
    recent = int(recent or 0)
    output = None if not n else ("Yes" if recent else "No")
    feedback = None if not rated else ("Positive" if avg >= POSITIVE_STARS else "Negative")
    return {"orders": n, "last_order": last, "recent_orders": recent,
            "avg_rating": round(float(avg), 1) if avg else None, "rated": rated,
            "attitude": stars_to_attitude(avg) if rated else None,
            "intention": recent_to_intention(n, recent),
            "output": output, "feedback": feedback}
