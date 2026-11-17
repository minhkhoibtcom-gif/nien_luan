"""App phân khúc khách hàng cho cửa hàng đồ ăn nhanh FASTBITE (tên giả định), bố cục theo web bán sữa La Che Fresca.
Chạy: python -m streamlit run app.py

Các trang (thư mục views/):
- Trang chủ: ai cũng xem được; khách đã điền thông tin thấy mục "Dành cho bạn" (combo theo nhóm khách).
- Đăng nhập, Đăng ký: chỉ hiện khi chưa đăng nhập (bố cục 2 cột như trang đăng nhập của web).
- Tài khoản: thông tin cá nhân + thông tin để xếp nhóm (đều không bắt buộc), nhóm và combo gợi ý.
- Quản trị: chỉ admin; các trang phân tích của niên luận và danh sách tài khoản khách hàng.
"""
import streamlit as st

import shared
import ui

st.set_page_config(page_title=ui.SITE_NAME, page_icon=str(ui.LOGO), layout="wide")
ui.apply_theme()
shared.init_admin()

home = st.Page("views/home.py", title="Trang chủ", icon=":material/home:", default=True)
login = st.Page("views/login.py", title="Đăng nhập", icon=":material/login:", url_path="dang-nhap")
register = st.Page("views/register.py", title="Đăng ký", icon=":material/person_add:", url_path="dang-ky")
account = st.Page("views/account.py", title="Tài khoản", icon=":material/person:", url_path="tai-khoan")
admin = st.Page("views/admin.py", title="Quản trị", icon=":material/monitoring:", url_path="quan-tri")
shared.PAGES.update(home=home, login=login, register=register, account=account, admin=admin)

user = shared.current_user()
# Luôn đăng ký đủ các trang (menu ẩn, thanh trên cùng tự vẽ) để st.switch_page tới được mọi trang;
# quyền xem do từng trang kiểm tra (shared.require_login / require_admin).
page = st.navigation([home, login, register, account, admin], position="hidden")

auth_page = page.url_path in (login.url_path, register.url_path)
if not auth_page:
    with st.container(key="navbar"):
        if user is None:
            cols = st.columns([4, 1.3, 3, 1.3, 1.2], vertical_alignment="center")
            with cols[0]:
                ui.brand()
            cols[1].page_link(home, label="Trang chủ", icon=":material/home:")
            cols[3].page_link(login, label="Đăng nhập", icon=":material/login:")
            if cols[4].button("Đăng ký", type="primary", width="stretch"):
                st.switch_page(register)
        else:
            cols = st.columns([4, 1.3, 1.3, 1.3, 2.2, 1.3], vertical_alignment="center")
            with cols[0]:
                ui.brand()
            cols[1].page_link(home, label="Trang chủ", icon=":material/home:")
            cols[2].page_link(account, label="Tài khoản", icon=":material/person:")
            if shared.is_admin(user):
                cols[3].page_link(admin, label="Quản trị", icon=":material/monitoring:")
            cols[4].markdown(f'<div class="lcf-hello">Xin chào, {ui.esc(user["name"])}</div>', unsafe_allow_html=True)
            if cols[5].button("Đăng xuất", width="stretch"):
                shared.logout()
                st.switch_page(home)

shared.show_flash()
page.run()

if not auth_page:
    ui.footer("Đồ án niên luận: phân khúc khách hàng đặt đồ ăn online bằng K-Prototypes trên bộ dữ liệu "
              "Online Food Delivery (mở rộng 3000 mẫu), gợi ý combo khuyến mãi cho từng nhóm khách.")
