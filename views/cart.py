"""Giỏ hàng và đặt hàng (như trang giỏ hàng của web La Che Fresca).

Bên trái: các món trong giỏ, có ô chọn món để đặt, sửa số lượng, xóa. Bên phải: thông tin giao hàng
(điền sẵn từ hồ sơ), phương thức thanh toán, tổng tiền các món được chọn. Đặt xong thì hiện box đánh giá.
"""
import streamlit as st

import orders
import shared
import ui

user = shared.require_login()
cart = shared.cart()
rows = orders.cart_rows(cart)

st.markdown("<h2 style='text-align:center'>🛒 GIỎ HÀNG</h2>", unsafe_allow_html=True)


def show_empty():
    with st.container(key="card"):
        st.markdown("<div style='text-align:center;font-size:3rem'>🛒</div>"
                    "<h5 style='text-align:center'>Giỏ hàng đang trống</h5>", unsafe_allow_html=True)
        _, mid, _ = st.columns([2, 1, 2])
        if mid.button("Chọn món ngay", type="primary", width="stretch"):
            st.switch_page(shared.PAGES["home"])


def set_qty(code):
    cart[code] = int(st.session_state[f"qty_{code}"])


def remove(code):
    cart.pop(code, None)
    for key in (f"qty_{code}", f"sel_{code}"):
        st.session_state.pop(key, None)


def show_cart():
    left, right = st.columns([8, 4], gap="large")
    with left:
        with st.container(key="card"):
            widths = [0.6, 4, 1.6, 1.7, 1.7, 0.8]
            head = st.columns(widths, vertical_alignment="center")
            for col, text in zip(head, ["", "**Món**", "**Đơn giá**", "**Số lượng**", "**Thành tiền**", ""]):
                col.markdown(text)
            for r in rows:
                c = st.columns(widths, vertical_alignment="center")
                if r["available"]:
                    c[0].checkbox("Chọn", value=True, key=f"sel_{r['code']}", label_visibility="collapsed")
                else:  # combo sai loại ngày / hết hạn: khóa ô chọn, khách xóa hoặc đợi đúng ngày
                    st.session_state[f"sel_{r['code']}"] = False
                    c[0].checkbox("Chọn", key=f"sel_{r['code']}", disabled=True, label_visibility="collapsed",
                                  help=r["note"])
                c[1].markdown(f"**{r['name']}**" + (f"  \n:red[{r['note']}]" if r["note"] else ""))
                c[2].markdown(ui.vnd(r["price"]))
                st.session_state[f"qty_{r['code']}"] = r["qty"]  # đồng bộ với giỏ (có thể vừa thêm món ở trang khác)
                c[3].number_input("Số lượng", min_value=1, max_value=orders.MAX_QTY, step=1,
                                  key=f"qty_{r['code']}", on_change=set_qty, args=(r["code"],),
                                  label_visibility="collapsed")
                c[4].markdown(f"**{ui.vnd(r['price'] * r['qty'])}**")
                c[5].button("", key=f"del_{r['code']}", icon=":material/delete:", help="Xóa khỏi giỏ",
                            on_click=remove, args=(r["code"],))
        if st.button("Tiếp tục chọn món", icon=":material/arrow_back:"):
            st.switch_page(shared.PAGES["home"])

    selected = [r for r in rows if r["available"] and st.session_state.get(f"sel_{r['code']}", True)]
    total = sum(r["price"] * r["qty"] for r in selected)
    if any(not r["available"] for r in rows):
        left.warning("Có combo không áp dụng hôm nay hoặc đã hết hạn nên chưa chọn được. "
                     "Bạn có thể xóa khỏi giỏ, hoặc đặt các món còn lại trước.")

    with right:
        with st.form("checkout"):
            st.markdown("#### Thông tin giao hàng")
            name = st.text_input("Họ tên người nhận", value=user["name"], max_chars=100)
            phone = st.text_input("Số điện thoại", value=user["phone"] or "", max_chars=10)
            line = st.text_input("Địa chỉ cụ thể (số nhà, đường)", value=user["address_line"] or "", max_chars=255)
            commune = st.text_input("Phường / Xã", value=user["address_commune"] or "", max_chars=100)
            province = st.text_input("Tỉnh / Thành phố", value=user["address_province"] or "", max_chars=100)
            note = st.text_area("Ghi chú", max_chars=500, height=80)
            payment = st.radio("Phương thức thanh toán", list(orders.PAYMENT_LABEL), format_func=orders.PAYMENT_LABEL.get)
            st.divider()
            c1, c2 = st.columns([3, 2], vertical_alignment="center")
            c1.markdown(f"Tổng thanh toán  \n<small>Đã chọn {len(selected)}/{len(rows)} món</small>", unsafe_allow_html=True)
            c2.markdown(f"<div class='lcf-price' style='text-align:right;font-size:1.5rem'>{ui.vnd(total)}</div>",
                        unsafe_allow_html=True)
            submitted = st.form_submit_button("Đặt hàng", type="primary", width="stretch", icon=":material/payments:")

        if submitted:
            try:
                order_id = orders.place_order(user["user_id"], cart, [r["code"] for r in selected], {
                    "name": name, "phone": phone, "shipping_line": line, "shipping_commune": commune,
                    "shipping_province": province, "note": note, "payment_method": payment},
                    segment=shared.user_segment(user)[0])  # lưu cụm lúc đặt để tạo combo tháng sau
                for r in selected:
                    for key in (f"qty_{r['code']}", f"sel_{r['code']}"):
                        st.session_state.pop(key, None)
                st.session_state["rate_order"] = order_id  # app.py mở box đánh giá ở lần chạy sau
                shared.flash("success", f"Đặt hàng thành công! Mã đơn hàng của bạn: {orders.order_code(order_id)}")
                st.switch_page(shared.PAGES["account"])
            except orders.OrderError as e:
                st.error(str(e))


# Không dùng st.stop(): thanh menu và chân trang (app.py) được vẽ sau khi trang chạy xong
if rows:
    show_cart()
else:
    show_empty()
