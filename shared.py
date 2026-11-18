"""Phần dùng chung giữa các trang: mô hình, thực đơn, người đang đăng nhập, nhãn tiếng Việt, thông báo."""
import streamlit as st

import auth
import combos
import orders
from menu import load_menu, retention_offer
from segmentation import CATEGORY_ORDER, predict_partial, train

# Trang của app (app.py gán khi khởi tạo st.navigation) để các trang gọi st.page_link / st.switch_page
PAGES = {}

# Cột trong users.db -> tên cột của mô hình
FIELD_MAP = {
    "age": "Age", "family_size": "Family size", "gender": "Gender", "marital_status": "Marital Status",
    "occupation": "Occupation", "education": "Educational Qualifications", "output": "Output", "feedback": "Feedback",
}

# Giá trị của mô hình -> nhãn tiếng Việt trên form
OPTION_LABELS = {
    "gender": {"Male": "Nam", "Female": "Nữ"},
    "marital_status": {"Single": "Độc thân", "Married": "Đã kết hôn", "Prefer not to say": "Không muốn trả lời"},
    "occupation": {"Student": "Học sinh, sinh viên", "Employee": "Nhân viên, người đi làm",
                   "Self Employeed": "Tự kinh doanh", "House wife": "Nội trợ"},
    "education": {"Uneducated": "Chưa qua đào tạo", "School": "Phổ thông", "Graduate": "Đại học, cao đẳng",
                  "Post Graduate": "Thạc sĩ", "Ph.D": "Tiến sĩ"},
    "output": {"Yes": "Có, vẫn đặt món online", "No": "Không còn đặt nữa"},
    "feedback": {"Positive": "Hài lòng", "Negative": "Chưa hài lòng"},
}
FIELD_LABELS = {
    "age": "Tuổi", "family_size": "Số người trong gia đình", "gender": "Giới tính",
    "marital_status": "Tình trạng hôn nhân", "occupation": "Nghề nghiệp", "education": "Học vấn",
    "output": "Bạn có tiếp tục đặt món online không?", "feedback": "Bạn có hài lòng với dịch vụ đặt món online?",
}
# Thứ tự lựa chọn giống bộ dữ liệu
for _field, _col in FIELD_MAP.items():
    if _field in OPTION_LABELS:
        assert list(OPTION_LABELS[_field]) == CATEGORY_ORDER[_col], _field


@st.cache_resource(show_spinner="Đang huấn luyện K-Prototypes...")
def load_model():
    return train()


@st.cache_data(show_spinner=False)
def menu():
    return load_menu()


def init_admin():
    """Tạo tài khoản admin lần đầu. Đổi email/mật khẩu trong .streamlit/secrets.toml, mục [admin]."""
    try:
        cfg = dict(st.secrets.get("admin", {}))
    except Exception:  # chưa có file secrets.toml
        cfg = {}
    auth.ensure_admin(cfg.get("email", "admin@fastbite.vn"), cfg.get("password", "Admin@123"))


def current_user():
    user_id = st.session_state.get("user_id")
    user = auth.get_user(user_id) if user_id else None
    if user_id and user is None:
        st.session_state.pop("user_id", None)
    return user


def is_admin(user):
    return bool(user) and user["role"] == "admin"


def user_values(user):
    """8 thuộc tính của mô hình cho một khách: 6 thuộc tính tự khai trong hồ sơ, Output và Feedback suy ra
    từ đơn hàng và đánh giá (orders.behavior). None = bỏ trống, được bỏ qua khi xếp nhóm."""
    values = {col: user.get(field) for field, col in FIELD_MAP.items() if field not in ("output", "feedback")}
    b = orders.behavior(user["user_id"])
    values.update({"Output": b["output"], "Feedback": b["feedback"]})
    return values


def user_segment(user):
    """(tên cụm hoặc None, số thông tin đã dùng) cho khách; ô bỏ trống được bỏ qua."""
    return predict_partial(load_model(), user_values(user))


def user_offer(user, segment):
    """(combo chính, ưu đãi riêng hoặc None) cho khách đã có nhóm."""
    values = user_values(user)
    return (combos.pick_for(segment, user.get("family_size")),
            retention_offer(values["Output"], values["Feedback"]))


def cart():
    return st.session_state.setdefault("cart", {})


def add_to_cart(code, label):
    """Nút Thêm vào giỏ: chưa đăng nhập thì chuyển sang trang đăng nhập (như web)."""
    if current_user() is None:
        flash("warning", "Vui lòng đăng nhập để thêm món vào giỏ hàng.")
        st.switch_page(PAGES["login"])
    try:
        orders.cart_add(cart(), code)
        st.toast(f"Đã thêm \"{label}\" vào giỏ hàng.", icon=":material/shopping_cart:")
    except orders.OrderError as e:
        st.toast(str(e), icon=":material/error:")


@st.dialog("Đánh giá đơn hàng", dismissible=False)
def rating_dialog(order_id):
    """Box đánh giá 1-5 sao cho cả đơn; hiện ngay sau khi đặt hàng hoặc khi bấm Đánh giá trong Đơn hàng của tôi."""
    order = orders.get_order(order_id)
    st.markdown(f"Đơn **{orders.order_code(order_id)}** · {sum(i['quantity'] for i in order['items'])} món · "
                f"{order['total_amount']:,}₫".replace(",", "."))
    st.markdown("Bạn hài lòng với dịch vụ đặt món của FASTBITE như thế nào?")
    stars = st.feedback("stars", key=f"stars_{order_id}")
    comment = st.text_area("Góp ý (không bắt buộc)", max_chars=500, key=f"comment_{order_id}")
    c1, c2 = st.columns(2)
    if c1.button("Gửi đánh giá", type="primary", width="stretch"):
        if stars is None:
            st.error("Vui lòng chọn số sao.")
            return
        try:
            orders.rate_order(current_user()["user_id"], order_id, stars + 1, comment)  # chỉ đánh giá đơn của mình
            flash("success", "Cảm ơn bạn đã đánh giá!")
        except orders.OrderError as e:
            flash("error", str(e))
        st.session_state.pop("rate_order", None)
        st.rerun()
    if c2.button("Bỏ qua", width="stretch"):
        st.session_state.pop("rate_order", None)
        flash("info", "Bạn có thể đánh giá đơn này sau trong mục Đơn hàng của tôi (trang Tài khoản).")
        st.rerun()


def require_login():
    """Chưa đăng nhập thì chuyển sang trang Đăng nhập."""
    user = current_user()
    if user is None:
        flash("warning", "Vui lòng đăng nhập để tiếp tục.")
        st.switch_page(PAGES["login"])
    return user


def require_admin():
    user = require_login()
    if not is_admin(user):
        flash("error", "Trang này chỉ dành cho quản trị viên.")
        st.switch_page(PAGES["home"])
    return user


def redirect_if_logged_in():
    """Trang đăng nhập / đăng ký: đã đăng nhập thì về trang chủ (như web)."""
    if current_user() is not None:
        st.switch_page(PAGES["home"])


def flash(kind, message):
    """Thông báo hiện ở lần chạy sau (giống flash của web), dùng khi chuyển trang."""
    st.session_state.setdefault("_flash", []).append((kind, message))


def show_flash():
    for kind, message in st.session_state.pop("_flash", []):
        getattr(st, kind)(message)


def logout():
    st.session_state.clear()
    flash("success", "Bạn đã đăng xuất.")
