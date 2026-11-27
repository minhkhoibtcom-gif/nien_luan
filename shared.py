"""Phần dùng chung giữa các trang: mô hình, thực đơn, người đang đăng nhập, nhãn tiếng Việt, thông báo."""
import streamlit as st

import auth
import combos
import orders
from menu import load_menu, retention_offer
from segmentation import ATT, CATEGORY_ORDER, INCOME_GROUPS, INT, NUM_COLS, CAT_COLS, predict_partial, train

# Trang của app (app.py gán khi khởi tạo st.navigation) để các trang gọi st.page_link / st.switch_page
PAGES = {}

# Cột trong database -> cột của mô hình (Thái độ, Ý định đặt tiếp lấy từ đơn hàng và đánh giá)
FIELD_MAP = {"age": "Tuổi", "income": "Thu nhập", "gender": "Giới tính", "marital_status": "Hôn nhân",
             "education": "Học vấn"}
N_FEATURES = len(NUM_COLS) + len(CAT_COLS)
# Lựa chọn của các ô chọn trên form; giá trị lưu trong database chính là giá trị của mô hình
OPTIONS = {"income": CATEGORY_ORDER["Nhóm thu nhập"], "gender": CATEGORY_ORDER["Giới tính"],
           "marital_status": CATEGORY_ORDER["Hôn nhân"], "education": CATEGORY_ORDER["Học vấn"]}
FIELD_LABELS = {
    "age": "Tuổi", "income": "Thu nhập mỗi tháng", "gender": "Giới tính", "marital_status": "Tình trạng hôn nhân",
    "education": "Học vấn", "party_size": "Bạn thường đặt cho mấy người?",
}


@st.cache_resource(show_spinner=False)
def _train_model():
    return train()


# Vòng tròn xoay giữa màn hình (không kèm chữ) trong lúc huấn luyện mô hình lần đầu
_SPINNER = """
<style>
@keyframes fb-spin { to { transform: rotate(360deg); } }
.fb-loading { position: fixed; inset: 0; z-index: 999999; display: flex; align-items: center;
              justify-content: center; background: rgba(255, 243, 224, .65); }
.fb-loading div { width: 56px; height: 56px; border-radius: 50%; border: 6px solid #f6aa1c;
                  border-top-color: #d62828; animation: fb-spin .8s linear infinite; }
</style>
<div class="fb-loading" role="status" aria-label="Đang tải"><div></div></div>
"""
_model_ready = False


def load_model():
    global _model_ready
    if _model_ready:
        return _train_model()
    holder = st.empty()
    holder.html(_SPINNER)
    try:
        model = _train_model()
    finally:
        holder.empty()
    _model_ready = True
    return model


@st.cache_data(show_spinner=False)
def menu():
    return load_menu()


def init_admin():
    """Tạo tài khoản admin lần đầu. Đổi email/mật khẩu trong .streamlit/secrets.toml, mục [admin]."""
    try:
        cfg = dict(st.secrets.get("admin", {}))
    except Exception:  # chưa có file secrets.toml
        cfg = {}
    auth.ensure_admin(cfg.get("email", "admin@.com"), cfg.get("password", "Admin@123"))


SESSION_COOKIE = "fb_session"


def login_user(user_id):
    """Đăng nhập trong phiên Streamlit hiện tại và hẹn ghi cookie để F5 / mở lại trình duyệt vẫn đăng nhập."""
    st.session_state["user_id"] = user_id
    token = auth.create_session(user_id)
    st.session_state["_session_token"] = token
    st.session_state["_cookie"] = token


def sync_cookie():
    """Ghi hoặc xóa cookie phiên trong trình duyệt (Streamlit chỉ đọc được cookie nên ghi bằng JavaScript).
    Gọi ở mỗi lần chạy app; chỉ vẽ khi có việc cần làm (sau đăng nhập / đăng xuất)."""
    if "_cookie" not in st.session_state:
        return
    token = st.session_state.pop("_cookie")
    age = auth.SESSION_DAYS * 86400 if token else 0
    st.html(f"""<script>
document.cookie = "{SESSION_COOKIE}={token or ''}; path=/; max-age={age}; SameSite=Lax"
  + (location.protocol === "https:" ? "; Secure" : "");
</script>""", unsafe_allow_javascript=True)


def _restore_login():
    """Phiên Streamlit mới (F5, mở tab mới): đăng nhập lại từ cookie nếu mã phiên còn hạn. Chỉ thử một lần mỗi phiên."""
    if st.session_state.get("_cookie_checked"):
        return
    st.session_state["_cookie_checked"] = True
    token = st.context.cookies.get(SESSION_COOKIE)
    user_id = auth.session_user(token)
    if user_id:
        st.session_state["user_id"] = user_id
        st.session_state["_session_token"] = token


def current_user():
    if "user_id" not in st.session_state:
        _restore_login()
    user_id = st.session_state.get("user_id")
    user = auth.get_user(user_id) if user_id else None
    if user_id and user is None:
        st.session_state.pop("user_id", None)
    return user


def is_admin(user):
    return bool(user) and user["role"] == "admin"


def user_values(user, behavior=None):
    """7 thuộc tính của mô hình cho một khách: 5 thuộc tính tự khai trong hồ sơ, Thái độ và Ý định đặt tiếp suy ra
    từ đánh giá và đơn hàng (orders.behavior). None = bỏ trống, được bỏ qua khi xếp nhóm."""
    values = {}
    for field, col in FIELD_MAP.items():
        value = user.get(field)
        if field in OPTIONS and value not in OPTIONS[field]:  # bỏ trống, hoặc giá trị của dataset cũ
            value = None
        values[col] = value
    if values["Thu nhập"] is not None:
        values["Thu nhập"] = INCOME_GROUPS[values["Thu nhập"]]
    b = behavior or orders.behavior(user["user_id"])
    values.update({ATT: b["attitude"], INT: b["intention"]})
    return values


def user_segment(user):
    """(tên cụm hoặc None, số thông tin đã dùng) cho khách; ô bỏ trống được bỏ qua."""
    return predict_partial(load_model(), user_values(user))


def user_offer(user, segment):
    """(combo chính, ưu đãi riêng hoặc None) cho khách đã có nhóm: cỡ combo theo số người khách thường đặt,
    ưu đãi theo việc còn đặt món trong 30 ngày và mức hài lòng."""
    b = orders.behavior(user["user_id"])
    return combos.pick_for(segment, user.get("party_size")), retention_offer(b["output"], b["feedback"])


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
    auth.delete_session(st.session_state.get("_session_token"))
    st.session_state.clear()
    st.session_state["_cookie_checked"] = True  # cookie cũ vẫn còn trong st.context.cookies của phiên này
    st.session_state["_cookie"] = None          # xóa cookie ở lần chạy sau
    flash("success", "Bạn đã đăng xuất.")
