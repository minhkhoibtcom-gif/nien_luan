"""Trang Sản phẩm: toàn bộ combo và món lẻ, lọc theo danh mục, tìm theo tên, sắp xếp theo giá.

Danh mục = "Combo" + các loại món trong menu.csv (Gà giòn, Mì Ý, Cơm, Burger, Món thêm, Món phụ, Thức uống).
Danh mục đang chọn được giữ trên URL (?danh-muc=...) nên tải lại trang (F5) vẫn giữ bộ lọc.
"""
import unicodedata

import streamlit as st

import combos
import shared
import ui
from menu import CATEGORY_ICON

ALL = "Tất cả"
COMBO = "Combo"
SORTS = ["Mặc định", "Giá tăng dần", "Giá giảm dần", "Tên A–Z"]

menu = shared.menu()
shown, combo_month = combos.displayed()
categories = list(dict.fromkeys(menu["category"]))  # giữ thứ tự trong menu.csv
counts = menu["category"].value_counts()
options = [ALL, COMBO] + categories
icons = {ALL: "🍽️", COMBO: "🎁", **CATEGORY_ICON}
sizes = {ALL: len(menu) + len(shown), COMBO: len(shown), **counts.to_dict()}


def plain(text):
    """Chữ thường, bỏ dấu tiếng Việt: tìm "ga gion" vẫn ra "Gà giòn"."""
    text = unicodedata.normalize("NFD", str(text).lower()).replace("đ", "d")
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


ui.hero("Sản phẩm", "Toàn bộ combo và món lẻ của FASTBITE. Chọn danh mục hoặc tìm theo tên món.")
st.write("")

current = st.query_params.get("danh-muc", ALL)
category = st.pills("Danh mục", options, default=current if current in options else ALL,
                    format_func=lambda o: f"{icons.get(o, '🍽️')} {o} ({sizes.get(o, 0)})",
                    key="product_category") or ALL  # bấm lại mục đang chọn thì về Tất cả
if category == ALL:
    st.query_params.pop("danh-muc", None)
else:
    st.query_params["danh-muc"] = category

c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
query = c1.text_input("Tìm món", placeholder="Ví dụ: gà sốt cay, burger, trà sữa...",
                      key="product_search", icon=":material/search:")
sort = c2.selectbox("Sắp xếp", SORTS, key="product_sort")
needle = plain(query.strip())


def matches(name):
    return not needle or needle in plain(name)


# ---------- Combo ----------
combo_list = [c for c in shown if category in (ALL, COMBO) and (matches(c.name) or matches(f"combo {c.name}"))]
items = menu if category in (ALL, COMBO) else menu[menu["category"] == category]
items = items[items["name"].map(matches)] if category != COMBO else items.iloc[0:0]
if sort == "Giá tăng dần":
    combo_list.sort(key=lambda c: c.price)
    items = items.sort_values("price", kind="stable")
elif sort == "Giá giảm dần":
    combo_list.sort(key=lambda c: -c.price)
    items = items.sort_values("price", ascending=False, kind="stable")
elif sort == "Tên A–Z":
    combo_list.sort(key=lambda c: plain(c.name))
    items = items.iloc[items["name"].map(plain).argsort(kind="stable")]

st.caption(f"Tìm thấy {len(combo_list) + len(items)} sản phẩm")
if not combo_list and items.empty:
    st.info("Không có sản phẩm nào khớp. Thử bỏ bớt từ khóa hoặc chọn danh mục khác.")

if combo_list:
    ui.section_title("Combo khuyến mãi" + (f" tháng {combos.month_label(combo_month)}" if combo_month else ""))
    ui.combo_cards(combo_list, menu, key_prefix="prod_combo", on_add=shared.add_to_cart)

# ---------- Món lẻ: Tất cả thì chia theo loại món, chọn một loại thì hiện thẳng ----------
if not items.empty:
    if category == ALL and sort == "Mặc định":
        for cat in categories:
            part = items[items["category"] == cat]
            if not part.empty:
                ui.section_title(f"{icons.get(cat, '🍽️')} {cat}")
                ui.item_cards(part, key_prefix=f"prod_{cat}", on_add=shared.add_to_cart)
    else:
        ui.section_title("Món lẻ" if category == ALL else f"{icons.get(category, '🍽️')} {category}")
        ui.item_cards(items, key_prefix="prod_item", on_add=shared.add_to_cart)
