"""Trang chủ (bố cục như trang chủ web La Che Fresca): banner, nhóm món, Dành cho bạn, combo khuyến mãi, thực đơn, cam kết."""
import streamlit as st

import combos
import shared
import ui
from menu import GROUP_ICON

PAGES = shared.PAGES
user = shared.current_user()
menu = shared.menu()
shown, combo_month = combos.displayed()
today = combos.day_type()

# ---------- Banner ----------
with st.container(key="hero"):
    left, right = st.columns([7, 5], vertical_alignment="center")
    with left:
        ui.html_block('<span class="lcf-badge">Gà giòn · Mì Ý · Burger · Giao nhanh</span>'
                      '<h1>Đồ ăn nhanh nóng hổi,<br>combo hợp túi tiền cho mọi nhà</h1>'
                      '<p class="lcf-lead">Cho chúng tôi biết đôi chút về bạn (tuổi, thu nhập...), '
                      'FASTBITE sẽ gợi ý combo khuyến mãi hợp với bạn nhất.</p>')
        b1, b2, _ = st.columns([1.3, 1.3, 2])
        if user is None:
            if b1.button("Đăng ký ngay", type="primary", width="stretch"):
                st.switch_page(PAGES["register"])
            b2.page_link(PAGES["login"], label="Đăng nhập", icon=":material/login:")
        else:
            if b1.button("Cập nhật thông tin", type="primary", width="stretch"):
                st.switch_page(PAGES["account"])
            if shared.is_admin(user):
                b2.page_link(PAGES["admin"], label="Vào trang quản trị", icon=":material/monitoring:")
    with right:
        ui.hero_art()

# ---------- Nhóm món ----------
ui.section_title("Thực đơn")
ui.categories(menu)

# ---------- Dành cho bạn ----------
if user is None or not shared.is_admin(user):
    ui.section_title("Dành cho bạn")
    segment = shared.user_segment(user)[0] if user else None
    if segment:
        combo, extra = shared.user_offer(user, segment)
        ui.soft_note(f"<b>Combo gợi ý cho bạn hôm nay: {ui.esc(combo.name)}</b> (viền vàng)<br>"
                     f"<span style='font-size:.9rem'>Bạn thuộc nhóm khách hàng <b>{ui.esc(segment)}</b>. "
                     f"Combo ngày thường đặt được mọi ngày; combo cuối tuần chỉ đặt được Thứ 7–CN.</span>")
        ui.combo_cards(combos.for_segment(segment), menu, highlight=combo.combo_id if combo else None,
                       extra_offer=extra, key_prefix="foryou", on_add=shared.add_to_cart)
    else:
        with st.container(key="card"):
            c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
            if user is None:
                c1.markdown("**Nhận combo khuyến mãi dành riêng cho bạn**  \n"
                            "Đăng ký tài khoản và điền vài thông tin (tuổi, thu nhập...), "
                            "chúng tôi sẽ gợi ý combo hợp với bạn.")
                if c2.button("Đăng ký", key="cta_register", type="primary", width="stretch"):
                    st.switch_page(PAGES["register"])
            else:
                c1.markdown("**Nhận combo khuyến mãi dành riêng cho bạn**  \n"
                            "Điền tuổi hoặc thu nhập (và các thông tin khác nếu muốn) "
                            "trong trang Tài khoản để nhận gợi ý.")
                if c2.button("Điền thông tin", key="cta_profile", type="primary", width="stretch"):
                    st.switch_page(PAGES["account"])

# ---------- Combo khuyến mãi ----------
ui.section_title("Combo khuyến mãi" + (f" tháng {combos.month_label(combo_month)}" if combo_month else ""))
if combo_month is None:  # chưa có combo tháng nào được duyệt: combo mặc định, áp dụng mọi ngày
    ui.combo_cards(shown, menu, key_prefix="combo", on_add=shared.add_to_cart)
else:
    # Tab của loại ngày hôm nay đứng trước; tab còn lại vẫn xem được nhưng nút đặt bị khóa
    # Combo ngày thường áp dụng mọi ngày; cuối tuần thì cả hai loại đều đặt được (tab cuối tuần đứng trước)
    order = ["weekend", "weekday"] if today == "weekend" else ["weekday", "weekend"]
    labels = [combos.DAY_LABEL[d] + (" · đang áp dụng" if d == "weekday" or today == "weekend" else "")
              for d in order]
    for dtype, tab in zip(order, st.tabs(labels)):
        with tab:
            ui.combo_cards([c for c in shown if c.day_type == dtype], menu, key_prefix=f"combo_{dtype}",
                           on_add=shared.add_to_cart)

# ---------- Thực đơn theo nhóm món ----------
ui.section_title("Món lẻ")
groups = list(GROUP_ICON)
for group, tab in zip(groups, st.tabs([f"{GROUP_ICON[g]} {g}" for g in groups])):
    with tab:
        ui.item_cards(menu[menu["group"] == group], key_prefix=f"item_{group}", on_add=shared.add_to_cart)

ui.features()
