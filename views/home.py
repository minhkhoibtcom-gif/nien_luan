"""Trang chủ (bố cục như trang chủ web La Che Fresca): banner, nhóm món, Dành cho bạn, combo khuyến mãi, thực đơn, cam kết."""
import streamlit as st

import shared
import ui
from menu import CATEGORY_ICON, COMBOS, combos_for

PAGES = shared.PAGES
user = shared.current_user()
menu = shared.menu()

# ---------- Banner ----------
with st.container(key="hero"):
    left, right = st.columns([7, 5], vertical_alignment="center")
    with left:
        ui.html_block('<span class="lcf-badge">Gà giòn · Mì Ý · Burger · Giao nhanh</span>'
                      '<h1>Đồ ăn nhanh nóng hổi,<br>combo hợp túi tiền cho mọi nhà</h1>'
                      '<p class="lcf-lead">Cho chúng tôi biết đôi chút về bạn (tuổi, số người trong gia đình...), '
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
        ui.soft_note(f"<b>Combo gợi ý cho bạn: {ui.esc(combo.name)}</b> (viền vàng)<br>"
                     f"<span style='font-size:.9rem'>Theo thông tin bạn đã điền, bạn thuộc nhóm khách hàng "
                     f"<b>{ui.esc(segment)}</b>. {ui.esc(combo.reason)}</span>")
        ui.combo_cards(combos_for(segment), menu, highlight=combo.combo_id, extra_offer=extra)
    else:
        with st.container(key="card"):
            c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
            if user is None:
                c1.markdown("**Nhận combo khuyến mãi dành riêng cho bạn**  \n"
                            "Đăng ký tài khoản và điền vài thông tin (tuổi, số người trong gia đình...), "
                            "chúng tôi sẽ gợi ý combo hợp với bạn và gia đình.")
                if c2.button("Đăng ký", key="cta_register", type="primary", width="stretch"):
                    st.switch_page(PAGES["register"])
            else:
                c1.markdown("**Nhận combo khuyến mãi dành riêng cho bạn**  \n"
                            "Điền tuổi hoặc số người trong gia đình (và các thông tin khác nếu muốn) "
                            "trong trang Tài khoản để nhận gợi ý.")
                if c2.button("Điền thông tin", key="cta_profile", type="primary", width="stretch"):
                    st.switch_page(PAGES["account"])

# ---------- Combo khuyến mãi ----------
ui.section_title("Combo khuyến mãi")
ui.combo_cards(COMBOS, menu)

# ---------- Thực đơn theo nhóm món ----------
ui.section_title("Món lẻ")
categories = list(CATEGORY_ICON)
for cat, tab in zip(categories, st.tabs([f"{CATEGORY_ICON[c]} {c}" for c in categories])):
    with tab:
        ui.item_cards(menu[menu["category"] == cat])

ui.features()
