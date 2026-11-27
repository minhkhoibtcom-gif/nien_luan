"""Trang quản trị (chỉ admin): các trang phân tích của niên luận và danh sách tài khoản khách hàng."""
import altair as alt
import pandas as pd
import streamlit as st

import auth
import combos
import db
import orders
import shared
import ui
from menu import DEFAULT_COMBOS, combo_lines, list_price, retention_offer
from segmentation import (AGE_LIMITS, ATT, CAT_COLS, CATEGORY_ORDER, INCOME_GROUPS, INT, SEGMENT_ORDER,
                          STRATEGIES, predict, segment_profile)

shared.require_admin()

# Tông màu FASTBITE: đỏ, vàng, xanh ngọc, xanh đậm, cam
PALETTE = ["#d62828", "#f6aa1c", "#2a9d8f", "#264653", "#e76f51"]
YELLOW = "#f6aa1c"  # nền sáng: chữ trên nền này dùng màu tối
INK = "#2b2d42"


def label(col):
    return col


def sizes_chart(customers):
    sizes = customers["Segment"].value_counts().reindex(SEGMENT_ORDER).rename("Số khách").reset_index()
    sizes["Tỷ lệ"] = sizes["Số khách"] / len(customers)
    sizes["Nhãn"] = [f"{n} khách ({p:.1%})" for n, p in zip(sizes["Số khách"], sizes["Tỷ lệ"])]
    sizes["Thứ tự"] = range(len(sizes))
    base = alt.Chart(sizes).encode(
        theta=alt.Theta("Số khách:Q", stack=True),
        order=alt.Order("Thứ tự:Q"),
        color=alt.Color("Segment:N", title="Cụm", sort=SEGMENT_ORDER,
                        scale=alt.Scale(domain=SEGMENT_ORDER, range=PALETTE[:len(SEGMENT_ORDER)]),
                        legend=alt.Legend(orient="right", labelLimit=260)),
        tooltip=[alt.Tooltip("Segment:N", title="Cụm"), "Số khách:Q",
                 alt.Tooltip("Tỷ lệ:Q", format=".1%")],
    )
    sizes["Nhãn ngắn"] = [f"{p:.1%}\n{n} khách" for n, p in zip(sizes["Số khách"], sizes["Tỷ lệ"])]
    sizes["Màu chữ"] = [INK if color == YELLOW else "white" for color in PALETTE[:len(sizes)]]
    pie = base.mark_arc(outerRadius=140, stroke="white", strokeWidth=2)
    labels = alt.Chart(sizes).mark_text(radius=90, fontSize=13, fontWeight="bold", lineBreak="\n", lineHeight=16).encode(
        theta=alt.Theta("Số khách:Q", stack=True),
        order=alt.Order("Thứ tự:Q"),
        text="Nhãn ngắn:N",
        color=alt.Color("Màu chữ:N", scale=None),
    )
    return (pie + labels).properties(height=320)


def composition_chart(customers, col):
    order = CATEGORY_ORDER[col]
    pct = (pd.crosstab(customers["Segment"], customers[col], normalize="index") * 100)
    pct = pct.reindex(index=SEGMENT_ORDER, columns=order, fill_value=0)

    rows = []
    for segment, row in pct.iterrows():
        start = 0.0
        for value in order:
            rows.append({"Segment": segment, "Giá trị": value, "Tỷ lệ": row[value],
                         "start": start, "end": start + row[value],
                         "mid": start + row[value] / 2,
                         "Nhãn": f"{row[value]:.0f}%" if row[value] >= 12 else "",
                         "yellow": PALETTE[order.index(value)] == YELLOW})
            start += row[value]
    long = pd.DataFrame(rows)

    y = alt.Y("Segment:N", sort=SEGMENT_ORDER, title=None, axis=alt.Axis(labelLimit=260, ticks=False))
    bars = alt.Chart(long).mark_bar(height=34, stroke="white", strokeWidth=2).encode(
        x=alt.X("start:Q", title="% khách trong cụm", axis=alt.Axis(tickCount=5),
                scale=alt.Scale(domain=[0, 100])),
        x2="end:Q",
        y=y,
        color=alt.Color("Giá trị:N", title=label(col),
                        scale=alt.Scale(domain=order, range=PALETTE[:len(order)]),
                        sort=order, legend=alt.Legend(orient="top", labelLimit=200)),
        tooltip=["Segment:N", alt.Tooltip("Giá trị:N", title=label(col)),
                 alt.Tooltip("Tỷ lệ:Q", title="Tỷ lệ (%)", format=".1f")],
    )
    labels = alt.Chart(long).mark_text(fontSize=12).encode(
        x="mid:Q", y=y, text="Nhãn:N",
        color=alt.condition("datum.yellow", alt.value(INK), alt.value("white")),
    )
    return (bars + labels).properties(height=260)


def show_strategy(segment):
    st.markdown("\n".join(f"- {text}" for text in STRATEGIES[segment]))


def show_combos(segment, highlight=None, extra=None):
    """Combo khuyến mãi đang áp dụng của cụm; highlight = combo chọn cho khách (viền vàng)."""
    mine = combos.for_segment(segment)
    ui.soft_note("<br>".join(f"<b>{ui.esc(c.name)}</b> ({ui.esc(c.people)}, {combos.DAY_SHORT[c.day_type]}): "
                             f"<span style='font-size:.9rem'>{ui.esc(c.reason)}</span>" for c in mine))
    ui.combo_cards(mine, shared.menu(), highlight=highlight, extra_offer=extra, columns=3)


model = shared.load_model()
customers = model.customers
profile = segment_profile(customers)

ui.hero("Trang quản trị", "")
st.write("")

tab_orders, tab_combos, tab_new, tab_overview, tab_list, tab_accounts = st.tabs(
    ["Đơn hàng", "Combo theo tháng", "Tạo thử khách mới", "Tổng quan các cụm", "Danh sách khách hàng",
     "Tài khoản khách hàng"])

# ---------- Combo theo tháng: đề xuất từ số lượng món mỗi cụm mua theo ngày thường / cuối tuần ----------
with tab_combos:
    month = combos.current_month()
    prev = combos.previous_month(month)
    combos.ensure_proposals(month)  # đầu tháng tự tạo đề xuất (chưa áp dụng cho tới khi duyệt)
    shown, shown_month = combos.displayed()
    st.markdown(f"#### Combo tháng {combos.month_label(month)}")
    if shown_month == month:
        st.success(f"Khách đang thấy {len(shown)} combo đã duyệt của tháng {combos.month_label(month)}.")
    elif shown_month:
        st.warning(f"Chưa duyệt combo nào của tháng này, khách đang thấy combo tháng {combos.month_label(shown_month)}.")
    else:
        st.warning(f"Chưa từng duyệt combo theo tháng, khách đang thấy {len(DEFAULT_COMBOS)} combo mặc định (áp dụng mọi ngày).")

    lines = combos.order_lines(prev)
    summary = combos.cell_summary(lines)
    if summary.empty:
        st.info(f"Chưa có đơn nào của tháng {combos.month_label(prev)} để tạo đề xuất.")
    else:
        st.markdown(f"**Số đơn tháng {combos.month_label(prev)} theo cụm × loại ngày**")
        pivot = summary.pivot(index="segment", columns="day_type", values="orders").reindex(SEGMENT_ORDER)
        pivot = pivot.rename(columns={"weekday": "Ngày thường", "weekend": "Cuối tuần"}).fillna(0).astype(int)
        st.dataframe(pivot, width="stretch")
        st.caption(f"Gồm {int(summary['real'].sum())} đơn thật và {int(summary['simulated'].sum())} đơn mô phỏng "
                   "(simulated_orders.csv, dữ liệu giả lập để minh họa).")
        c1, c2, c3 = st.columns(3)
        seg_pick = c1.selectbox("Xem món mua nhiều nhất của cụm", SEGMENT_ORDER, key="cm_seg")
        day_pick = c2.selectbox("Loại ngày", ["weekday", "weekend"], key="cm_day",
                                format_func={"weekday": "Ngày thường", "weekend": "Cuối tuần"}.get)
        sizes = combos.size_summary(lines, seg_pick, day_pick)
        size_pick = c3.selectbox("Cỡ đơn (số người)", list(sizes.index), key="cm_size",
                                 format_func=lambda s: f"{s} người ({sizes[s]} đơn)")
        n, avg = combos.item_averages(lines, seg_pick, day_pick, shared.menu(), size_pick)
        if n:
            st.dataframe(avg.head(10).rename(columns={"name": "Món", "group": "Nhóm món",
                                                      "avg": "Số phần TB / đơn"})[["Món", "Nhóm món", "Số phần TB / đơn"]]
                         .round(2), width="stretch", hide_index=True)

    if st.button("Tạo lại đề xuất từ dữ liệu tháng trước", icon=":material/refresh:",
                 help="Thay các đề xuất chưa duyệt; combo đã duyệt giữ nguyên"):
        combos.save_proposals(month, combos.suggest(month)[0])
        shared.flash("success", "Đã tạo lại đề xuất combo.")
        st.rerun()

    menu = shared.menu()
    all_month = combos.month_combos(month)
    proposed = [c for c in all_month if c.status == "proposed"]
    if proposed and st.button(f"Duyệt tất cả {len(proposed)} đề xuất", type="primary", icon=":material/done_all:"):
        for c in proposed:
            combos.approve(c.combo_id)
        shared.flash("success", f"Đã duyệt {len(proposed)} combo tháng {combos.month_label(month)}.")
        st.rerun()
    for c in all_month:
        lp = list_price(c, menu)
        status = {"proposed": "Chờ duyệt", "active": "Đang áp dụng", "rejected": "Đã bỏ"}[c.status]
        with st.expander(f"{c.icon} {c.name} · {c.segment} · {combos.DAY_SHORT[c.day_type]} · "
                         f"{ui.vnd(c.price)} · {status}"):
            st.markdown("\n".join(f"- {x}" for x in combo_lines(c, menu)))
            st.caption(f"{c.reason}  \nGiá lẻ {ui.vnd(lp)} → giá combo {ui.vnd(c.price)} "
                       f"(giảm {1 - c.price / lp:.0%}). {c.offer}")
            if c.status != "active":
                p1, p2, p3 = st.columns([2, 1, 1], vertical_alignment="bottom")
                price = p1.number_input("Giá combo (₫)", min_value=1000, max_value=lp, step=1000, value=c.price,
                                        key=f"price_{c.combo_id}")
                if p2.button("Duyệt", key=f"ok_{c.combo_id}", type="primary", width="stretch"):
                    combos.approve(c.combo_id, price)
                    shared.flash("success", f"Đã duyệt {c.name}.")
                    st.rerun()
                if c.status == "proposed" and p3.button("Bỏ", key=f"no_{c.combo_id}", width="stretch"):
                    combos.reject(c.combo_id)
                    st.rerun()

# ---------- Đơn hàng (như tab Đơn hàng của web: lọc, tìm, chuyển trạng thái) ----------
ACTION_LABEL = {"shipping": "Xác nhận & giao", "completed": "Hoàn tất", "cancelled": "Hủy đơn"}
with tab_orders:
    counts, revenue = orders.order_stats()
    m = st.columns(4)
    m[0].metric("Chờ xác nhận", counts.get("pending", 0))
    m[1].metric("Đang giao", counts.get("shipping", 0))
    m[2].metric("Hoàn tất", counts.get("completed", 0))
    m[3].metric("Doanh thu (đơn hoàn tất)", ui.vnd(revenue))
    f1, f2 = st.columns([1, 2])
    status = f1.selectbox("Trạng thái", ["all"] + list(orders.STATUS_LABEL),
                          format_func=lambda s: "Tất cả" if s == "all" else orders.STATUS_LABEL[s])
    query = f2.text_input("Tìm theo mã đơn, tên hoặc SĐT người nhận", placeholder="VD: DH00000001")
    found = orders.all_orders(status, query)
    if not found:
        st.info("Không có đơn hàng phù hợp.")
    for o in found:
        title = (f"{orders.order_code(o['order_id'])} · {o['name']} · {o['created_at'][:16]} · "
                 f"{ui.vnd(o['total_amount'])} · {orders.STATUS_LABEL[o['status']]}")
        with st.expander(title):
            st.markdown("\n".join(f"- {title} = {ui.vnd(total)}" + (f"  \n  <small>{detail}</small>" if detail else "")
                                  for title, detail, total in orders.display_lines(o)), unsafe_allow_html=True)
            if o.get("segment"):
                st.caption(f"Cụm lúc đặt: {o['segment']} · {combos.DAY_LABEL.get(o['day_type'], '')}")
            st.caption(f"Tài khoản: {o['email']} · Người nhận: {o['name']} · {o['phone']}  \n"
                       f"Địa chỉ: {o['shipping_line']}, {o['shipping_commune']}, {o['shipping_province']}  \n"
                       f"{orders.PAYMENT_LABEL[o['payment_method']]}"
                       + (f"  \nGhi chú: {o['note']}" if o["note"] else "")
                       + (f"  \nĐánh giá: {'★' * o['rating']}{'☆' * (5 - o['rating'])}"
                          + (f" — {o['rating_comment']}" if o["rating_comment"] else "") if o["rating"]
                          else "  \nChưa đánh giá"))
            nexts = orders.NEXT_STATUS.get(o["status"], [])
            if nexts:
                bcols = st.columns(len(nexts) + 2)
                for col, nxt in zip(bcols, nexts):
                    if col.button(ACTION_LABEL[nxt], key=f"st_{o['order_id']}_{nxt}", width="stretch",
                                  type="secondary" if nxt == "cancelled" else "primary"):
                        try:
                            orders.set_status(o["order_id"], nxt)
                            shared.flash("success", f"Đơn {orders.order_code(o['order_id'])}: "
                                                    f"{orders.STATUS_LABEL[nxt]}.")
                        except orders.OrderError as e:
                            shared.flash("error", str(e))
                        st.rerun()

# ---------- Tạo thử khách mới ----------
with tab_new:
    with st.form("new_customer"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Tuổi", min_value=10, max_value=90, value=22, step=1)
            income = st.selectbox("Thu nhập mỗi tháng", CATEGORY_ORDER["Nhóm thu nhập"])
            gender = st.selectbox("Giới tính", CATEGORY_ORDER["Giới tính"])
            marital = st.selectbox("Hôn nhân", CATEGORY_ORDER["Hôn nhân"])
        with col2:
            education = st.selectbox("Học vấn", CATEGORY_ORDER["Học vấn"], index=3)
            attitude = st.slider(f"{ATT} (1–7)", 1.0, 7.0, 4.5, 0.25,
                                 help="Mức đánh giá tích cực về việc đặt đồ ăn online (trung bình câu Q19–Q21).")
            intention = st.slider(f"{INT} (1–7)", 1.0, 7.0, 4.75, 0.25,
                                  help="Ý định tiếp tục đặt đồ ăn online (trung bình câu Q22–Q25).")
            party = st.number_input("Thường đặt cho mấy người", min_value=1, max_value=20, value=2, step=1,
                                    help="Chỉ dùng để chọn cỡ combo, không dùng để xếp nhóm.")
        submitted = st.form_submit_button("Xác định cụm", type="primary")

    if submitted:
        new_customer = pd.DataFrame([{
            "Tuổi": min(max(age, AGE_LIMITS[0]), AGE_LIMITS[1]), "Thu nhập": INCOME_GROUPS[income],
            ATT: attitude, INT: intention, "Giới tính": gender, "Hôn nhân": marital, "Học vấn": education,
        }])
        segment = predict(model, new_customer)[0]
        p = profile.loc[segment]

        st.subheader(f"Khách hàng thuộc cụm: {segment}")
        if not AGE_LIMITS[0] <= age <= AGE_LIMITS[1]:
            st.warning(f"Khảo sát chỉ gồm người {AGE_LIMITS[0]}–{AGE_LIMITS[1]} tuổi; tuổi {age} được tính như "
                       f"{min(max(age, AGE_LIMITS[0]), AGE_LIMITS[1])}, kết quả kém tin cậy hơn.")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Quy mô cụm", f"{p['Số khách']} khách", f"{p['Tỷ lệ (%)']}% tổng số", delta_color="off")
        m2.metric("Tuổi trung bình của cụm", p["Tuổi TB"])
        m3.metric("Thu nhập TB của cụm", f"{p['Thu nhập TB (triệu)']} triệu")
        m4.metric(f"{INT} TB của cụm", p[f"{INT} TB (1–7)"])

        st.markdown("**Chiến lược tiếp thị đề xuất**")
        show_strategy(segment)
        st.caption("Các cụm chồng lấn khá nhiều nên kết quả mang tính tham khảo, "
                   "khách ở gần ranh giới có thể phù hợp với cả cụm lân cận.")

        combo = combos.pick_for(segment, party)
        # Ưu đãi giữ chân: ý định đặt tiếp dưới 4 coi như không còn đặt, thái độ dưới 4 coi như chưa hài lòng
        extra = retention_offer("Yes" if intention >= 4 else "No", "Positive" if attitude >= 4 else "Negative")
        if combo is None:
            st.info("Hôm nay cụm này chưa có combo đặt được.")
        else:
            st.markdown(f"**Combo khuyến mãi cho khách này hôm nay: {combo.name}** "
                        f"({combos.DAY_LABEL[combo.day_type]})" + (f"; ưu đãi riêng: {extra}" if extra else ""))
        show_combos(segment, highlight=combo.combo_id if combo else None, extra=extra)

# ---------- Tổng quan các cụm ----------
with tab_overview:
    st.subheader("Số khách hàng theo cụm")
    st.altair_chart(sizes_chart(customers), width="stretch")

    st.subheader("Đặc điểm từng cụm")
    st.dataframe(profile.astype(str).T, width="stretch")

    st.subheader("Cơ cấu thuộc tính trong từng cụm")
    attribute = st.selectbox("Chọn thuộc tính", ["Nhóm tuổi", "Nhóm thu nhập"] + CAT_COLS, format_func=label)
    st.altair_chart(composition_chart(customers, attribute), width="stretch")

    st.subheader("Chiến lược tiếp thị")
    for segment in SEGMENT_ORDER:
        with st.expander(f"{segment} ({profile.loc[segment, 'Số khách']} khách)"):
            show_strategy(segment)

    st.subheader("Combo khuyến mãi đang áp dụng theo cụm")
    menu = shared.menu()
    st.dataframe(pd.DataFrame([{
        "Cụm": c.segment, "Combo": c.name, "Áp dụng": combos.DAY_SHORT[c.day_type], "Phục vụ": c.people,
        "Giá lẻ": list_price(c, menu), "Giá combo": c.price,
        "Giảm (%)": round((1 - c.price / list_price(c, menu)) * 100), "Ưu đãi": c.offer}
        for c in combos.displayed()[0]]), width="stretch", hide_index=True)
    for segment, tab in zip(SEGMENT_ORDER, st.tabs(SEGMENT_ORDER)):
        with tab:
            show_combos(segment)

# ---------- Danh sách khách hàng (bộ dữ liệu) ----------
with tab_list:
    chosen = st.multiselect("Lọc theo cụm", SEGMENT_ORDER, default=SEGMENT_ORDER)
    shown = customers[customers["Segment"].isin(chosen)]
    st.write(f"Đang hiển thị {len(shown)} / {len(customers)} khách hàng")
    columns = ["Segment"] + [c for c in customers.columns if c not in ("Segment", "Cluster")]
    table = shown[columns].rename(columns={"Segment": "Cụm", "Thu nhập": "Thu nhập (triệu)"})
    st.dataframe(table, width="stretch", hide_index=True)
    st.download_button("Tải danh sách đang hiển thị (CSV)",
                       table.to_csv(index=False).encode("utf-8-sig"),
                       file_name="customer_segments_filtered.csv", mime="text/csv")

# ---------- Tài khoản khách hàng đã đăng ký trong app ----------
with tab_accounts:
    rows = []
    behaviors = orders.behavior_all()  # 1 truy vấn cho mọi khách thay vì 2 truy vấn x 3 lần mỗi khách
    for u in auth.all_customers():
        b = behaviors[u["user_id"]]
        segment, used = shared.user_segment(u, b)
        address = ", ".join(x for x in (u["address_line"], u["address_commune"], u["address_province"]) if x)
        offer = shared.user_offer(u, segment, b) if segment else (None, None)
        rows.append({
            "Mã": u["user_id"], "Họ tên": u["name"], "Email": u["email"], "SĐT": u["phone"] or "",
            "Địa chỉ": address, "Tuổi": u["age"],
            **{shared.FIELD_LABELS[f]: u[f] if u[f] in shared.OPTIONS[f] else ""
               for f in ("income", "gender", "marital_status", "education")},
            "Thường đặt cho": u["party_size"],
            "Số đơn": b["orders"], "Đơn gần nhất": (b["last_order"] or "")[:10],
            f"Đơn {orders.ACTIVE_DAYS} ngày": b["recent_orders"], "Sao TB": b["avg_rating"],
            ATT: b["attitude"], INT: b["intention"],
            "Số thông tin dùng": f"{used}/{shared.N_FEATURES}", "Nhóm": segment or "Chưa xếp được",
            "Combo gợi ý": offer[0].name if offer[0] else "", "Ưu đãi riêng": offer[1] or "",
            "Ngày đăng ký": u["created_at"][:10],
        })
    accounts = pd.DataFrame(rows)
    if accounts.empty:
        st.info("Chưa có khách hàng nào đăng ký.")
    else:
        counts = accounts["Nhóm"].value_counts()
        cols = st.columns(len(SEGMENT_ORDER) + 1)
        for col, name in zip(cols, SEGMENT_ORDER + ["Chưa xếp được"]):
            col.metric(name, int(counts.get(name, 0)))
        group = st.selectbox("Lọc theo nhóm", ["Tất cả"] + SEGMENT_ORDER + ["Chưa xếp được"])
        shown = accounts if group == "Tất cả" else accounts[accounts["Nhóm"] == group]
        st.dataframe(shown, width="stretch", hide_index=True)
        st.download_button("Tải danh sách tài khoản (CSV)", shown.to_csv(index=False).encode("utf-8-sig"),
                           file_name="tai_khoan_khach_hang.csv", mime="text/csv")
    st.caption(f"Dữ liệu tài khoản, đơn hàng và combo lưu trong: {db.describe()}")
