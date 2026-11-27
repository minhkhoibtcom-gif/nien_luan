"""Tài khoản của tôi (như hoso.php của web): thông tin cá nhân, thông tin để xếp nhóm, nhóm và combo gợi ý.

Mọi ô đều không bắt buộc (trừ họ tên đã có từ lúc đăng ký). Ô bỏ trống được bỏ qua khi xếp nhóm:
cần ít nhất tuổi hoặc thu nhập để xếp được nhóm. "Thường đặt cho mấy người" chỉ dùng để chọn cỡ combo.
"""
import streamlit as st

import auth
import orders
import shared
import ui
import combos

user = shared.require_login()

ui.hero(f"Xin chào, {user['name']}",
        f"{user['email']} · Thành viên từ {user['created_at'][8:10]}/{user['created_at'][5:7]}/{user['created_at'][:4]}",
        ["Quản trị viên"] if shared.is_admin(user) else [])
st.write("")


def choice(field):
    """Ô chọn có thể bỏ trống; trả về giá trị của mô hình (Nam, Độc thân...) hoặc None."""
    options = shared.OPTIONS[field]
    current = user.get(field)
    return st.selectbox(shared.FIELD_LABELS[field], options,
                        index=options.index(current) if current in options else None,
                        placeholder="Chọn...", key=f"f_{field}")


left, right = st.columns([7, 5], gap="large")
with left:
    with st.form("profile"):
        st.markdown("#### Thông tin cá nhân")
        name = st.text_input("Họ tên", value=user["name"], max_chars=100)
        st.text_input("Email", value=user["email"], disabled=True, help="Email hiện không thể thay đổi.")
        phone = st.text_input("Số điện thoại", value=user["phone"] or "", max_chars=10)
        address_line = st.text_input("Địa chỉ (số nhà, đường)", value=user["address_line"] or "", max_chars=255)
        c1, c2 = st.columns(2)
        address_commune = c1.text_input("Phường/Xã", value=user["address_commune"] or "", max_chars=100)
        address_province = c2.text_input("Tỉnh/Thành phố", value=user["address_province"] or "", max_chars=100)
        c1, c2 = st.columns(2)
        age = c1.number_input(shared.FIELD_LABELS["age"], min_value=10, max_value=100, value=user["age"],
                              step=1)
        with c2:
            income = choice("income")
        c1, c2 = st.columns(2)
        with c1:
            gender = choice("gender")
            education = choice("education")
        with c2:
            marital_status = choice("marital_status")
            party_size = st.number_input(shared.FIELD_LABELS["party_size"], min_value=1, max_value=20,
                                         value=user["party_size"], step=1, placeholder="Số người",
                                         help="Chỉ dùng để gợi ý combo đúng cỡ, không dùng để xếp nhóm.")
        st.caption("Ngoài họ tên, mọi ô đều không bắt buộc; ô bỏ trống được bỏ qua. Tuổi, thu nhập, giới tính, "
                   "hôn nhân, học vấn dùng để xếp nhóm và gợi ý combo (cần ít nhất tuổi hoặc thu nhập). "
                   "Thái độ và ý định đặt tiếp được lấy từ đánh giá và đơn hàng của bạn.")
        saved = st.form_submit_button("Lưu thông tin", type="primary")

    if saved:
        try:
            auth.update_profile(user["user_id"], {
                "name": name, "phone": phone, "address_line": address_line,
                "address_commune": address_commune, "address_province": address_province,
                "age": age, "income": income, "gender": gender, "marital_status": marital_status,
                "education": education, "party_size": party_size,
            })
            shared.flash("success", "Đã lưu thông tin.")
            st.rerun()
        except auth.AuthError as e:
            st.error(str(e))

    with st.expander("Đổi mật khẩu"):
        with st.form("password", border=False):
            old = st.text_input("Mật khẩu hiện tại", type="password")
            new = st.text_input("Mật khẩu mới", type="password", placeholder=f"Từ {auth.PASSWORD_MIN} ký tự")
            new2 = st.text_input("Nhập lại mật khẩu mới", type="password")
            if st.form_submit_button("Đổi mật khẩu"):
                try:
                    auth.change_password(user["user_id"], old, new, new2)
                    st.success("Đã đổi mật khẩu.")
                except auth.AuthError as e:
                    st.error(str(e))

segment, _ = shared.user_segment(user)
combo, extra = shared.user_offer(user, segment) if segment else (None, None)
with right:
    # Đã xếp được nhóm thì không hiện thẻ; chưa đủ thông tin thì nhắc khách điền tuổi hoặc thu nhập
    if segment is None:
        with st.container(key="segment_card"):
            st.markdown("#### Nhóm khách hàng của bạn")
            st.info("Chưa xếp được nhóm. Hãy điền tuổi hoặc thu nhập (và các thông tin khác nếu muốn) "
                    "rồi bấm Lưu thông tin.")

    # ---------- Đơn hàng của tôi ----------
    st.markdown("#### Đơn hàng của tôi")
    my_orders = orders.user_orders(user["user_id"])
    if not my_orders:
        st.caption("Bạn chưa có đơn hàng nào.")
    for o in my_orders:
        with st.container(border=True):
            h1, h2 = st.columns([3, 2], vertical_alignment="center")
            h1.markdown(f"**{orders.order_code(o['order_id'])}** <small>{o['created_at'][:16]}</small>",
                        unsafe_allow_html=True)
            h2.badge(orders.STATUS_LABEL[o["status"]], color=orders.STATUS_COLOR[o["status"]])
            st.markdown("\n".join(f"- {title} — {ui.vnd(total)}" + (f"  \n  <small>{detail}</small>" if detail else "")
                                  for title, detail, total in orders.display_lines(o)), unsafe_allow_html=True)
            st.caption(f"Giao tới: {o['name']} · {o['phone']} · {o['shipping_line']}, {o['shipping_commune']}, "
                       f"{o['shipping_province']}  \n{orders.PAYMENT_LABEL[o['payment_method']]}"
                       + (f"  \nGhi chú: {o['note']}" if o["note"] else ""))
            b1, b2, b3 = st.columns([2, 1.3, 1.3], vertical_alignment="center")
            b1.markdown(f"<span class='lcf-price'>{ui.vnd(o['total_amount'])}</span>", unsafe_allow_html=True)
            if o["rating"]:
                b2.markdown(f"<span style='color:#f6aa1c'>{'★' * o['rating']}{'☆' * (5 - o['rating'])}</span>",
                            unsafe_allow_html=True, help=o["rating_comment"] or None)
            elif o["status"] != "cancelled" and b2.button("Đánh giá", key=f"rate_{o['order_id']}", width="stretch"):
                st.session_state["rate_order"] = o["order_id"]
                st.rerun()
            if o["status"] == "pending" and b3.button("Hủy đơn", key=f"cancel_{o['order_id']}", width="stretch"):
                try:
                    orders.cancel_order(user["user_id"], o["order_id"])
                    shared.flash("success", f"Đã hủy đơn hàng {orders.order_code(o['order_id'])}.")
                except orders.OrderError as e:
                    shared.flash("error", str(e))
                st.rerun()

if segment is not None:
    ui.section_title("Combo khuyến mãi cho bạn")
    ui.combo_cards(combos.for_segment(segment), shared.menu(), highlight=combo.combo_id, extra_offer=extra,
                   key_prefix="acc", on_add=shared.add_to_cart)
