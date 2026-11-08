"""Giao diện demo phân khúc khách hàng. Chạy: python -m streamlit run app.py"""
import altair as alt
import pandas as pd
import streamlit as st

from segmentation import (CAT_COLS, CATEGORY_ORDER, DISPLAY_NAMES, HIDDEN_COLS,
                          SEGMENT_ORDER, STRATEGIES, predict, segment_profile, train)

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
YELLOW = "#eda100"
INK = "#0b0b0b"

st.set_page_config(page_title="Phân khúc khách hàng", layout="wide")


def label(col):
    return DISPLAY_NAMES.get(col, col)


@st.cache_resource(show_spinner="Đang huấn luyện K-Prototypes...")
def load_model():
    return train()


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


model = load_model()
customers = model.customers
profile = segment_profile(customers)

st.title("Phân khúc khách hàng đặt đồ ăn online")
st.caption(f"Thuật toán K-Prototypes, 4 cụm, huấn luyện trên {len(customers)} khách hàng sau khi làm sạch dữ liệu.")

tab_new, tab_overview, tab_list = st.tabs(
    ["Phân khúc khách mới", "Tổng quan các cụm", "Danh sách khách hàng"])

# ---------- Phân khúc khách mới ----------
with tab_new:
    age_min, age_max = int(customers["Age"].min()), int(customers["Age"].max())
    fam_min, fam_max = int(customers["Family size"].min()), int(customers["Family size"].max())

    with st.form("new_customer"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Tuổi (Age)", min_value=10, max_value=90, value=22, step=1)
            family = st.number_input("Số người trong hộ (Family size)", min_value=1, max_value=20, value=3, step=1)
            gender = st.selectbox("Giới tính (Gender)", CATEGORY_ORDER["Gender"])
            marital = st.selectbox("Hôn nhân (Marital Status)", CATEGORY_ORDER["Marital Status"])
        with col2:
            occupation = st.selectbox("Nghề nghiệp (Occupation)", CATEGORY_ORDER["Occupation"])
            education = st.selectbox("Học vấn (Educational Qualifications)",
                                     CATEGORY_ORDER["Educational Qualifications"], index=2)
            output = st.selectbox("Tiếp tục đặt món (Output)", CATEGORY_ORDER["Output"],
                                  help="Cột Output trong dữ liệu. Đề tài giả định Yes nghĩa là khách tiếp tục đặt món online.")
            feedback = st.selectbox("Phản hồi (Feedback)", CATEGORY_ORDER["Feedback"])
        submitted = st.form_submit_button("Xác định cụm", type="primary")

    if submitted:
        new_customer = pd.DataFrame([{
            "Age": age, "Family size": family, "Gender": gender,
            "Marital Status": marital, "Occupation": occupation,
            "Educational Qualifications": education, "Output": output, "Feedback": feedback,
        }])
        segment = predict(model, new_customer)[0]
        p = profile.loc[segment]

        st.subheader(f"Khách hàng thuộc cụm: {segment}")
        if not (age_min <= age <= age_max and fam_min <= family <= fam_max):
            st.warning(f"Giá trị nằm ngoài khoảng dữ liệu huấn luyện (tuổi {age_min}–{age_max}, "
                       f"số người trong hộ {fam_min}–{fam_max}), kết quả kém tin cậy hơn.")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Quy mô cụm", f"{p['Số khách']} khách", f"{p['Tỷ lệ (%)']}% tổng số", delta_color="off")
        m2.metric("Tuổi trung bình của cụm", p["Age TB"])
        m3.metric("Tỷ lệ tiếp tục đặt món của cụm", f"{p['Tiếp tục đặt món (%)']}%")
        m4.metric("Phản hồi tích cực của cụm", f"{p['Feedback = Positive (%)']}%")

        st.markdown("**Chiến lược tiếp thị đề xuất**")
        show_strategy(segment)
        st.caption("Các cụm chồng lấn khá nhiều nên kết quả mang tính tham khảo, "
                   "khách ở gần ranh giới có thể phù hợp với cả cụm lân cận.")

# ---------- Tổng quan các cụm ----------
with tab_overview:
    st.subheader("Số khách hàng theo cụm")
    st.altair_chart(sizes_chart(customers), width="stretch")

    st.subheader("Đặc điểm từng cụm")
    st.dataframe(profile.astype(str).T, width="stretch")
    st.caption("Monthly Income không tham gia phân cụm, chỉ dùng để tham khảo khi mô tả cụm.")

    st.subheader("Cơ cấu thuộc tính trong từng cụm")
    attribute = st.selectbox("Chọn thuộc tính", CAT_COLS + ["Monthly Income"], format_func=label)
    st.altair_chart(composition_chart(customers, attribute), width="stretch")

    st.subheader("Chiến lược tiếp thị")
    for segment in SEGMENT_ORDER:
        with st.expander(f"{segment} ({profile.loc[segment, 'Số khách']} khách)"):
            show_strategy(segment)

# ---------- Danh sách khách hàng ----------
with tab_list:
    chosen = st.multiselect("Lọc theo cụm", SEGMENT_ORDER, default=SEGMENT_ORDER)
    shown = customers[customers["Segment"].isin(chosen)]
    st.write(f"Đang hiển thị {len(shown)} / {len(customers)} khách hàng")
    columns = ["Segment"] + [c for c in customers.columns
                             if c not in ("Segment", "Cluster", *HIDDEN_COLS)]
    table = shown[columns].rename(columns=DISPLAY_NAMES)
    st.dataframe(table, width="stretch", hide_index=True)
    st.download_button("Tải danh sách đang hiển thị (CSV)",
                       table.to_csv(index=False).encode("utf-8-sig"),
                       file_name="customer_segments_filtered.csv", mime="text/csv")
