"""Thực đơn, lớp Combo và combo mặc định.

Thực đơn (menu.csv): món ăn và giá lẻ tham khảo từ jollibee.com.vn ngày 16/11/2026.
FASTBITE là tên cửa hàng giả định của đồ án, không liên quan tới Jollibee.

Combo chính thức được tạo mỗi tháng từ đơn hàng tháng trước, theo cụm x ngày thường/cuối tuần (combos.py),
admin duyệt rồi mới áp dụng. DEFAULT_COMBOS bên dưới (thiết kế tay từ đặc điểm cụm) chỉ dùng khi
chưa có combo tháng nào được duyệt; combo mặc định áp dụng mọi ngày.
Giá lẻ của combo tính tự động từ menu.csv.
Ảnh món: assets/products/<item_id>.(png|jpg|jpeg|webp), ảnh combo: assets/products/<combo_id>.*;
chưa có ảnh thì dùng biểu tượng của nhóm món.
"""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
MENU_FILE = HERE / "menu.csv"
IMAGE_DIR = HERE / "assets" / "products"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
MENU_SOURCE = "Thực đơn và giá lẻ tham khảo từ jollibee.com.vn (16/11/2026)."

CATEGORY_ICON = {
    "Gà giòn": "🍗", "Mì Ý": "🍝", "Cơm": "🍚", "Burger": "🍔",
    "Món thêm": "🍟", "Món phụ": "🍨", "Thức uống": "🥤",
}
# Nhóm lớn (cột group của menu.csv): món chính gồm gà giòn, mì Ý, cơm, burger;
# món thêm = khoai, súp, cơm trắng, mì Ý thêm; món phụ = tráng miệng
GROUP_ICON = {"Món chính": "🍗", "Món thêm": "🍟", "Món phụ": "🍨", "Thức uống": "🥤"}
NOT_IN_COMBO = {"P06", "P07"}  # Cơm trắng, Mì Ý thêm: chỉ bán lẻ, không đưa vào combo


@dataclass(frozen=True)
class Combo:
    combo_id: str
    name: str
    segment: str
    people: str            # cỡ phục vụ, hiển thị trên thẻ
    items: tuple           # ((item_id, số lượng), ...)
    price: int             # giá combo
    offer: str             # kiểu ưu đãi
    reason: str            # căn cứ từ đặc điểm cụm / dữ liệu đơn hàng
    icon: str
    day_type: str = "all"  # weekday (T2-T6) | weekend (T7-CN) | all (combo mặc định)
    month: str | None = None
    status: str = "active"


DEFAULT_COMBOS = [
    Combo("CB01", "SV Tiết Kiệm", "Sinh viên thu nhập thấp", "1 người",
          (("C03", 1), ("N01", 1)), 39000,
          "Giảm thêm khi có thẻ sinh viên, miễn phí giao hàng.",
          "Trẻ nhất, đa số thu nhập dưới 10 triệu: suất nhỏ, giá thấp nhất, không có món phụ.", "🎒"),
    Combo("CB02", "SV Đôi Bạn", "Sinh viên thu nhập thấp", "2 người",
          (("B01", 2), ("P02", 1), ("N01", 2)), 105000,
          "Giảm thêm khi có thẻ sinh viên, miễn phí giao hàng.",
          "Đi cùng bạn: món chính rẻ, chia chung một phần khoai.", "🍔"),
    Combo("CB03", "Hội Bạn 3 Người", "Sinh viên thu nhập thấp", "3 người",
          (("B01", 1), ("M01", 1), ("C03", 1), ("P03", 1), ("N01", 3)), 149000,
          "Giảm thêm khi có thẻ sinh viên, miễn phí giao hàng.",
          "Nhóm bạn độc thân ăn chung: giá mỗi người thấp.", "👥"),
    Combo("CB04", "Tối Cặp Đôi", "Người đi làm thu nhập khá", "2 người",
          (("G12", 1), ("M03", 1), ("P04", 1), ("N07", 2), ("T02", 1)), 179000,
          "Cam kết giao đúng giờ, tặng voucher 50.000₫ cho đơn sau.",
          "Thu nhập cao nhất, đa số đã kết hôn nhưng ít gắn bó: bữa tối cho 2 người kèm ưu đãi quay lại.", "🌙"),
    Combo("CB05", "Cả Nhà 3 Người", "Người đi làm thu nhập khá", "3 người",
          (("G04", 1), ("M01", 2), ("P02", 1), ("N01", 3), ("T06", 3)), 239000,
          "Cam kết giao đúng giờ, tặng voucher 50.000₫ cho đơn sau.",
          "Gia đình nhỏ: gà chia chung, có món phụ cho cả nhà.", "🏠"),
    Combo("CB06", "Cả Nhà 4 Người", "Người đi làm thu nhập khá", "4 người",
          (("G06", 1), ("M01", 2), ("P02", 2), ("N01", 4), ("T06", 4)), 335000,
          "Cam kết giao đúng giờ, tặng voucher 50.000₫ cho đơn sau.",
          "Bữa tối và cuối tuần của gia đình: combo lớn kèm cam kết giao đúng giờ.", "👨‍👩‍👧‍👦"),
    Combo("CB07", "Trưa Quen Thuộc", "Khách trung thành", "1 người",
          (("C01", 1), ("P05", 1), ("N05", 1), ("T03", 1)), 85000,
          "",
          "Thái độ và ý định đặt tiếp cao nhất: giữ món quen, thêm món phụ thay vì giảm sâu.", "⭐"),
    Combo("CB08", "Đôi Bạn Thân", "Khách trung thành", "2 người",
          (("G02", 1), ("M01", 1), ("P01", 1), ("N04", 2), ("T01", 1)), 139000,
          "",
          "Khách quen đặt cho 2 người: món được ưa chuộng kèm tráng miệng.", "💛"),
    Combo("CB09", "Nhóm Nhỏ 3 Người", "Khách trung thành", "3 người",
          (("G04", 1), ("M03", 1), ("P03", 2), ("N02", 3), ("T04", 2)), 265000,
          "",
          "Nhóm nhỏ cuối tuần: đủ món chính, món thêm và món phụ.", "🎉"),
]
MAIN_CATEGORIES = ("Gà giòn", "Mì Ý", "Cơm", "Burger")  # món chính: dùng để ước số người của một đơn

# Ưu đãi kèm theo trạng thái của từng khách (Output, Feedback)
RETENTION_OFFERS = {
    ("Yes", "Negative"): "Khảo sát góp ý kèm voucher xin lỗi 20.000₫.",
    ("No", "Positive"): "Voucher \"Nhớ bạn\" 30.000₫ cho đơn kế tiếp.",
    ("No", "Negative"): "Voucher 50.000₫ kèm cam kết hoàn tiền nếu giao trễ hoặc món không đạt.",
}


def load_menu(path=MENU_FILE):
    return pd.read_csv(path)


def list_price(combo, menu):
    prices = menu.set_index("item_id")["price"]
    return int(sum(prices[item] * qty for item, qty in combo.items))


def combo_lines(combo, menu):
    names = menu.set_index("item_id")["name"]
    return [f"{qty} {names[item]}" for item, qty in combo.items]


def combo_people(combo):
    """Số người của combo từ chuỗi "2 người" (không có số thì coi là 1)."""
    return int(combo.people.split()[0]) if combo.people[:1].isdigit() else 1


def pick_default_combo(segment, party_size=None):
    """Combo mặc định của khách: trong nhóm, chọn combo có số người gần số người khách thường đặt nhất
    (bỏ trống thì lấy combo nhỏ nhất)."""
    mine = [c for c in DEFAULT_COMBOS if c.segment == segment]
    target = party_size or min(combo_people(c) for c in mine)
    return min(mine, key=lambda c: abs(combo_people(c) - target))


def retention_offer(output=None, feedback=None):
    """Ưu đãi kèm theo trạng thái của khách; thiếu một trong hai thông tin thì không có."""
    return RETENTION_OFFERS.get((output, feedback))


def image_path(code):
    for ext in IMAGE_EXTS:
        path = IMAGE_DIR / f"{code}{ext}"
        if path.is_file():
            return path
    return None
