"""Đăng ký: cùng bố cục với trang đăng nhập (như dangky.php của web). Đăng ký xong tự đăng nhập."""
import streamlit as st

import auth
import shared
import ui

PAGES = shared.PAGES
shared.redirect_if_logged_in()

left, right = st.columns([7, 5], gap="large")
with left:
    ui.auth_hero()
with right:
    with st.container(key="auth_card"):
        st.markdown("## Đăng ký")
        with st.form("register", border=False):
            name = st.text_input("Họ tên", max_chars=100, placeholder="Họ tên")
            email = st.text_input("Email", max_chars=100, placeholder="Email")
            phone = st.text_input("Số điện thoại (không bắt buộc)", max_chars=10, placeholder="Số điện thoại")
            password = st.text_input("Mật khẩu", type="password", placeholder=f"Từ {auth.PASSWORD_MIN} ký tự")
            confirm = st.text_input("Nhập lại mật khẩu", type="password", placeholder="Nhập lại mật khẩu")
            submitted = st.form_submit_button("Đăng ký", type="primary", width="stretch")
        if submitted:
            try:
                st.session_state["user_id"] = auth.register(name, email, password, confirm, phone)
                shared.flash("success", "Đăng ký thành công! Hãy điền thêm vài thông tin để nhận gợi ý combo.")
                st.switch_page(PAGES["account"])
            except auth.AuthError as e:
                st.error(str(e))
        st.markdown("<p style='text-align:center;margin:1rem 0 .3rem'>Đã có tài khoản?</p>", unsafe_allow_html=True)
        st.page_link(PAGES["login"], label="Đăng nhập", icon=":material/login:")
        st.page_link(PAGES["home"], label="Về trang chủ", icon=":material/arrow_back:")
