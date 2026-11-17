"""Tài khoản của tôi (như hoso.php của web): thông tin cá nhân, thông tin để xếp nhóm, nhóm và combo gợi ý.

Mọi ô đều không bắt buộc (trừ họ tên đã có từ lúc đăng ký). Ô bỏ trống được bỏ qua khi xếp nhóm:
cần ít nhất tuổi hoặc số người trong gia đình để xếp được nhóm.
"""
import streamlit as st

import auth
import shared
import ui
from menu import combos_for

user = shared.require_login()
L = shared.OPTION_LABELS
customers = shared.load_model().customers
AGE_RANGE = (int(customers["Age"].min()), int(customers["Age"].max()))
FAMILY_RANGE = (int(customers["Family size"].min()), int(customers["Family size"].max()))

ui.hero(f"Xin chào, {user['name']}",
        f"{user['email']} · Thành viên từ {user['created_at'][8:10]}/{user['created_at'][5:7]}/{user['created_at'][:4]}",
        ["Quản trị viên"] if shared.is_admin(user) else [])
st.write("")


def choice(field):
    """Ô chọn có thể bỏ trống; trả về giá trị của mô hình (Male, Single...) hoặc None."""
    options = list(L[field])
    current = user.get(field)
    return st.selectbox(shared.FIELD_LABELS[field], options, format_func=L[field].get,
                        index=options.index(current) if current in options else None,
                        placeholder="Bỏ qua (không trả lời)", key=f"f_{field}")


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

        st.markdown("#### Thông tin để nhận gợi ý")
        st.caption("Không bắt buộc, ô nào bỏ trống sẽ được bỏ qua. Cần ít nhất tuổi hoặc số người trong gia đình "
                   "để xếp bạn vào nhóm khách hàng.")
        c1, c2 = st.columns(2)
        age = c1.number_input(shared.FIELD_LABELS["age"], min_value=10, max_value=100, value=user["age"],
                              step=1, placeholder="Bỏ qua")
        family_size = c2.number_input(shared.FIELD_LABELS["family_size"], min_value=1, max_value=20,
                                      value=user["family_size"], step=1, placeholder="Bỏ qua")
        c1, c2 = st.columns(2)
        with c1:
            gender = choice("gender")
            occupation = choice("occupation")
        with c2:
            marital_status = choice("marital_status")
            education = choice("education")
        output = choice("output")
        feedback = choice("feedback")
        saved = st.form_submit_button("Lưu thông tin", type="primary")

    if saved:
        try:
            auth.update_profile(user["user_id"], {
                "name": name, "phone": phone, "address_line": address_line,
                "address_commune": address_commune, "address_province": address_province,
                "age": age, "family_size": family_size, "gender": gender, "marital_status": marital_status,
                "occupation": occupation, "education": education, "output": output, "feedback": feedback,
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

segment, used = shared.user_segment(user)
with right:
    with st.container(key="segment_card"):
        st.markdown("#### Nhóm khách hàng của bạn")
        if segment is None:
            st.info("Chưa xếp được nhóm. Hãy điền tuổi hoặc số người trong gia đình (và các thông tin khác nếu muốn) "
                    "rồi bấm Lưu thông tin.")
        else:
            st.markdown(f'<span class="lcf-badge" style="font-size:1rem">{ui.esc(segment)}</span>',
                        unsafe_allow_html=True)
            combo, extra = shared.user_offer(user, segment)
            st.markdown(f"**Combo gợi ý: {combo.name}** ({combo.people})")
            if extra:
                st.markdown(f"Ưu đãi riêng: {extra}")
            st.caption(f"Dựa trên {used}/8 thông tin bạn đã điền. Điền càng đủ, gợi ý càng sát.")
            if user["age"] is not None and not AGE_RANGE[0] <= user["age"] <= AGE_RANGE[1] or \
                    user["family_size"] is not None and not FAMILY_RANGE[0] <= user["family_size"] <= FAMILY_RANGE[1]:
                st.warning(f"Thông tin nằm ngoài khoảng dữ liệu huấn luyện (tuổi {AGE_RANGE[0]}–{AGE_RANGE[1]}, "
                           f"số người trong gia đình {FAMILY_RANGE[0]}–{FAMILY_RANGE[1]}), gợi ý chỉ mang tính tham khảo.")
        if user["profile_updated_at"]:
            st.caption(f"Cập nhật lần cuối: {user['profile_updated_at']}")

if segment is not None:
    ui.section_title("Combo khuyến mãi cho bạn")
    ui.combo_cards(combos_for(segment), shared.menu(), highlight=combo.combo_id, extra_offer=extra)
