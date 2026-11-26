"""App phân khúc khách hàng cho cửa hàng đồ ăn nhanh FASTBITE (tên giả định), bố cục theo web bán sữa La Che Fresca.
Chạy: python -m streamlit run app.py

Các trang (thư mục views/):
- Trang chủ: ai cũng xem được; khách đã điền thông tin thấy mục "Dành cho bạn" (combo theo nhóm khách).
- Đăng nhập, Đăng ký: chỉ hiện khi chưa đăng nhập (bố cục 2 cột như trang đăng nhập của web).
- Tài khoản: thông tin cá nhân + thông tin để xếp nhóm (đều không bắt buộc), nhóm và combo gợi ý.
- Quản trị: chỉ admin; các trang phân tích của niên luận và danh sách tài khoản khách hàng.
"""
import streamlit as st

import db
import shared
import ui

st.set_page_config(page_title=ui.SITE_NAME, page_icon=str(ui.LOGO), layout="wide")
ui.apply_theme()
try:
    shared.init_admin()
except db.DatabaseUnavailable:
    st.error("Không kết nối được database. Kiểm tra URL PostgreSQL trong Secrets, kết nối mạng, "
             "hoặc database đang bị tạm dừng trên trang quản lý (Supabase / Neon), rồi tải lại trang.")
    st.stop()

home = st.Page("views/home.py", title="Trang chủ", icon=":material/home:", default=True)
login = st.Page("views/login.py", title="Đăng nhập", icon=":material/login:", url_path="dang-nhap")
register = st.Page("views/register.py", title="Đăng ký", icon=":material/person_add:", url_path="dang-ky")
account = st.Page("views/account.py", title="Tài khoản", icon=":material/person:", url_path="tai-khoan")
admin = st.Page("views/admin.py", title="Quản trị", icon=":material/monitoring:", url_path="quan-tri")
cart = st.Page("views/cart.py", title="Giỏ hàng", icon=":material/shopping_cart:", url_path="gio-hang")
shared.PAGES.update(home=home, login=login, register=register, account=account, admin=admin, cart=cart)

user = shared.current_user()
# Luôn đăng ký đủ các trang (menu ẩn, thanh trên cùng tự vẽ) để st.switch_page tới được mọi trang;
# quyền xem do từng trang kiểm tra (shared.require_login / require_admin).
page = st.navigation([home, login, register, account, admin, cart], position="hidden")

auth_page = page.url_path in (login.url_path, register.url_path)
navbar = (st.container(key="navbar", horizontal=True, horizontal_alignment="distribute",
                       vertical_alignment="center") if not auth_page else None)
shared.show_flash()

# Box đánh giá ngay sau khi đặt hàng (views/cart.py đặt cờ rate_order)
if user is not None and st.session_state.get("rate_order"):
    shared.rating_dialog(st.session_state["rate_order"])

page.run()

# Vẽ thanh trên cùng sau khi trang chạy xong để số món trong giỏ cập nhật ngay khi vừa thêm
if navbar is not None:
    with navbar:
        # 3 nhóm: logo | liên kết | lời chào + nút; mỗi nhóm rộng vừa nội dung nên chữ không bị cắt
        if ui.brand_button():
            st.switch_page(home)
        with st.container(horizontal=True, width="content", vertical_alignment="center", gap="medium"):
            st.page_link(home, label="Trang chủ", icon=":material/home:")
            if user is not None:
                st.page_link(cart, label=f"Giỏ hàng ({sum(shared.cart().values())})", icon=":material/shopping_cart:")
                st.page_link(account, label="Tài khoản", icon=":material/person:")
                if shared.is_admin(user):
                    st.page_link(admin, label="Quản trị", icon=":material/monitoring:")
        with st.container(horizontal=True, width="content", vertical_alignment="center", gap="small"):
            if user is None:
                st.page_link(login, label="Đăng nhập", icon=":material/login:")
                if st.button("Đăng ký", type="primary"):
                    st.switch_page(register)
            else:
                st.markdown(f'<span class="lcf-hello">Xin chào, {ui.esc(user["name"])}</span>',
                            unsafe_allow_html=True, width="content")
                if st.button("Đăng xuất"):
                    shared.logout()
                    st.switch_page(home)

if not auth_page:
    ui.footer(about="Đồ án niên luận: phân khúc khách hàng đặt đồ ăn online bằng K-Prototypes, "
              "gợi ý combo khuyến mãi cho từng nhóm khách.")
