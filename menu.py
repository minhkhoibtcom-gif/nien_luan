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
    Combo("CB01", "SV Tiết Kiệm", "Sinh viên hộ nhỏ", "1 người",
          (("C03", 1), ("N01", 1)), 39000,
          "Giảm thêm khi có thẻ sinh viên, miễn phí giao đơn từ 39.000₫.",
          "Nhóm đông nhất, đa số chưa có thu nhập: suất nhỏ, giá thấp nhất.", "🎒"),
    Combo("CB02", "SV Đôi Bạn", "Sinh viên hộ nhỏ", "2–3 người",
          (("B01", 2), ("P02", 1), ("N01", 2)), 95000,
          "Giảm thêm khi có thẻ sinh viên, miễn phí giao hàng.",
          "Hộ 2–3 người, chưa có thu nhập: giảm sâu nhất.", "🍔"),
    Combo("CB03", "Hội Bạn 4 Người", "Sinh viên hộ đông", "4 người",
          (("G04", 1), ("M01", 2), ("P03", 2), ("N01", 4)), 245000,
          "",
          "Trung thành và hài lòng nhất (tiếp tục đặt món cao nhất): ăn chung, giá mỗi người thấp.", "👥"),
    Combo("CB04", "Hội Bạn 6 Người", "Sinh viên hộ đông", "5–6 người",
          (("G06", 1), ("M01", 3), ("P02", 2), ("N01", 6)), 349000,
          "",
          "Hộ 5–6 người: phần ăn chia sẻ, giá mỗi người thấp.", "🎉"),
    Combo("CB05", "Trưa Văn Phòng", "Người đi làm trẻ", "1 người",
          (("C01", 1), ("P05", 1), ("N05", 1)), 75000,
          "Cam kết giao đúng giờ.",
          "Có thu nhập, cần tiện lợi: giảm nhẹ, ưu tiên giao đúng giờ.", "💼"),
    Combo("CB06", "Tối Cặp Đôi", "Người đi làm trẻ", "2–3 người",
          (("G12", 1), ("M03", 2), ("P04", 1), ("N07", 2), ("T02", 1)), 219000,
          "Món cao cấp hơn, giảm vừa phải.",
          "Đa số thu nhập khá, hơn nửa đã kết hôn: bữa tối cho 2 người.", "🌙"),
    Combo("CB07", "Cả Nhà 4 Người", "Người có gia đình hộ đông", "3–4 người",
          (("G04", 1), ("M01", 2), ("P02", 2), ("N01", 4), ("T06", 4)), 269000,
          "Đặt trước bữa tối và cuối tuần, tặng voucher 50.000₫ cho đơn sau, hoàn tiền nếu giao trễ.",
          "Thu nhập khá nhưng tỷ lệ quay lại thấp nhất: ưu đãi kéo khách quay lại.", "🏠"),
    Combo("CB08", "Cả Nhà 5–6 Người", "Người có gia đình hộ đông", "5–6 người",
          (("G06", 1), ("M01", 3), ("P02", 2), ("N01", 5), ("T06", 5)), 369000,
          "Đặt trước bữa tối và cuối tuần, tặng voucher 50.000₫ cho đơn sau, hoàn tiền nếu giao trễ.",
          "Hộ đông nhất, quay lại ít nhất: combo lớn kèm voucher và cam kết chất lượng.", "👨‍👩‍👧‍👦"),
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


def pick_default_combo(segment, family_size=None):
    """Combo mặc định của khách: theo nhóm và số người trong hộ (bỏ trống thì lấy cỡ phổ biến của nhóm)."""
    ids = {
        "Sinh viên hộ nhỏ": "CB01" if family_size == 1 else "CB02",
        "Sinh viên hộ đông": "CB04" if family_size is not None and family_size >= 5 else "CB03",
        "Người đi làm trẻ": ("CB05" if family_size == 1 else
                              "CB07" if family_size is not None and family_size >= 4 else "CB06"),
        "Người có gia đình hộ đông": "CB07" if family_size is not None and family_size <= 4 else "CB08",
    }
    return next(c for c in DEFAULT_COMBOS if c.combo_id == ids[segment])


def retention_offer(output=None, feedback=None):
    """Ưu đãi kèm theo trạng thái của khách; thiếu một trong hai thông tin thì không có."""
    return RETENTION_OFFERS.get((output, feedback))


def image_path(code):
    for ext in IMAGE_EXTS:
        path = IMAGE_DIR / f"{code}{ext}"
        if path.is_file():
            return path
    return None
