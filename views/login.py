"""Đăng nhập: bên trái banner thương hiệu, bên phải thẻ form (như dangnhap.php của web)."""
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
        st.markdown("## Đăng nhập")
        with st.form("login", border=False):
            email = st.text_input("Email", placeholder="Email")
            password = st.text_input("Mật khẩu", type="password", placeholder="Mật khẩu")
            submitted = st.form_submit_button("Đăng nhập", type="primary", width="stretch")
        if submitted:
            try:
                st.session_state["user_id"] = auth.login(email, password)
                user = auth.get_user(st.session_state["user_id"])
                shared.flash("success", f"Xin chào {user['name']}!")
                st.switch_page(PAGES["admin"] if user["role"] == "admin" else PAGES["home"])
            except auth.AuthError as e:
                st.error(str(e))
        st.markdown("<p style='text-align:center;margin:1rem 0 .3rem'>Chưa có tài khoản?</p>", unsafe_allow_html=True)
        st.page_link(PAGES["register"], label="Đăng ký", icon=":material/person_add:")
        st.page_link(PAGES["home"], label="Về trang chủ", icon=":material/arrow_back:")
