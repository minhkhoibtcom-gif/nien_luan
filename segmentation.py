"""Mô hình phân khúc khách hàng trên dataset Gen Z Việt Nam: cùng quy trình và tham số với kprototypes.ipynb.

Dữ liệu: data/genz_vn.xlsx, khảo sát 361 người 15–28 tuổi về đặt đồ ăn qua ứng dụng
(Data in Brief 2023, OSF doi 10.17605/OSF.IO/TEPXB). Mỗi câu Likert 7 mức được đổi sang điểm 1–7.

7 thuộc tính đưa vào K-Prototypes:
- Cột số (chuẩn hóa z-score):
  Tuổi (giữa nhóm tuổi Q27), Thu nhập (giữa nhóm thu nhập Q29, triệu đồng/tháng),
  Thái độ = trung bình Q19–Q21 (bài báo gốc ký hiệu ATT), Ý định đặt tiếp = trung bình Q22–Q25 (INT).
- Cột phân loại: Giới tính (Q26), Hôn nhân (Q30), Học vấn (Q28).
K = 3 chọn theo thu_nghiem_vn/chon_k.py (Silhouette, Davies–Bouldin, Calinski–Harabasz, độ ổn định).
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from kmodes.kprototypes import KPrototypes
from sklearn.preprocessing import StandardScaler

DATA_FILE = Path(__file__).parent / "data" / "genz_vn.xlsx"

K = 3
SEED = 42
N_INIT = 5
ATT = "Thái độ"
INT = "Ý định đặt tiếp"
NUM_COLS = ["Tuổi", "Thu nhập", ATT, INT]
CAT_COLS = ["Giới tính", "Hôn nhân", "Học vấn"]
CAT_IDX = list(range(len(NUM_COLS), len(NUM_COLS) + len(CAT_COLS)))
LIKERT_RANGE = (1, 7)
AGE_LIMITS = (15, 28)        # khoảng tuổi của khảo sát Gen Z

# Mã hóa câu trả lời của file Excel (tiếng Anh) sang giá trị dùng trong app
LIKERT = {"Totally disagree": 1, "Disagree": 2, "More or less disagree": 3, "Neutral": 4,
          "More or less agree": 5, "Agree": 6, "Totally agree": 7}
AGE_GROUPS = {"15-18 years old": ("15–18", 16.5), "19-22 years old": ("19–22", 20.5),
              "23-25 years old": ("23–25", 24), "26-28 years old": ("26–28", 27)}
INCOME_GROUPS = {"Dưới 10 triệu": 5, "10–20 triệu": 15, "20–30 triệu": 25, "30–40 triệu": 35, "Trên 40 triệu": 45}
INCOME_RAW = {"< 10,000,000 VND": "Dưới 10 triệu", "10,000,000 VND - 20,000,000 VND": "10–20 triệu",
              "20,000,000 VND – 30,000,000 VND": "20–30 triệu", "30,000,000 VND – 40,000,000 VND": "30–40 triệu",
              "> 40,000,000 VND": "Trên 40 triệu"}
GENDER_RAW = {"Male": "Nam", "Female": "Nữ"}
MARITAL_RAW = {"Single": "Độc thân", "Married": "Đã kết hôn"}
EDUCATION_RAW = {"High school or lesser": "THPT trở xuống", "Professional certificate": "Chứng chỉ nghề",
                 "College diploma": "Cao đẳng", "University undergraduate degree": "Đại học",
                 "Postgraduate degree": "Sau đại học"}

CATEGORY_ORDER = {
    "Giới tính": list(GENDER_RAW.values()),
    "Hôn nhân": list(MARITAL_RAW.values()),
    "Học vấn": list(EDUCATION_RAW.values()),
    "Nhóm tuổi": [label for label, _ in AGE_GROUPS.values()],
    "Nhóm thu nhập": list(INCOME_GROUPS),
}

SEGMENT_ORDER = ["Sinh viên thu nhập thấp", "Người đi làm thu nhập khá", "Khách trung thành"]

# Chiến lược cho từng cụm, chỉ dùng các tính năng hệ thống đang có: combo theo tháng của cụm
# (ngày thường / cuối tuần, cỡ theo số người, admin duyệt), ưu đãi kèm theo trạng thái khách
# (còn đặt món trong 30 ngày, hài lòng theo số sao đánh giá), đánh giá sau đơn.
STRATEGIES = {
    "Sinh viên thu nhập thấp": [
        "Trẻ nhất (khoảng 21 tuổi), đa số thu nhập dưới 10 triệu và độc thân: combo không có món phụ, "
        "giữ giá mỗi suất thấp.",
        "Combo ngày thường cỡ 1–2 người, đặt được mọi ngày, phù hợp bữa ăn nhanh hằng ngày.",
        "Combo cuối tuần cho nhóm bạn 2–3 người; cỡ combo tháng sau đề xuất từ đơn của cụm tháng này "
        "(tab Combo theo tháng), admin duyệt rồi áp dụng.",
    ],
    "Người đi làm thu nhập khá": [
        "Nhóm đông nhất, thu nhập cao nhất, đa số đã kết hôn nhưng thái độ và ý định đặt tiếp thấp nhất: "
        "ưu tiên kéo khách đặt lại.",
        "Khách hơn 30 ngày không đặt hoặc đánh giá thấp được tự động kèm voucher mời quay lại (20.000₫–50.000₫), "
        "combo kèm cam kết giao đúng giờ.",
        "Combo gia đình 2–4 người cho bữa tối và cuối tuần, có món phụ.",
    ],
    "Khách trung thành": [
        "Thái độ và ý định đặt tiếp cao nhất: không cần giảm sâu, giữ các món cụm này mua nhiều nhất trong combo.",
        "Combo 1–3 người có món phụ, đặt được mọi ngày; combo cuối tuần cho nhóm nhỏ.",
        "Nhắc khách đánh giá sau mỗi đơn để giữ mức hài lòng và phát hiện sớm đơn bị chấm thấp.",
    ],
}


@dataclass
class SegmentModel:
    kp: KPrototypes
    scaler: StandardScaler
    segment_names: dict
    customers: pd.DataFrame   # dữ liệu đã mã hóa, thêm cột Cluster và Segment
    num_range: dict           # (min, max) hợp lệ của từng cột số theo thang đo của khảo sát


def load_customers(path=DATA_FILE):
    """Đọc file Excel của khảo sát và mã hóa: Likert -> điểm, nhóm tuổi / thu nhập -> số giữa nhóm."""
    raw = pd.read_excel(path)
    likert = raw[[f"Q{i}" for i in range(19, 26)]].apply(lambda s: s.map(LIKERT))
    if likert.isna().any().any():
        raise ValueError("Có câu trả lời Likert không nằm trong bảng mã LIKERT")
    df = pd.DataFrame({
        "Tuổi": raw["Q27"].map(lambda v: AGE_GROUPS[v][1]),
        "Thu nhập": raw["Q29"].map(INCOME_RAW).map(INCOME_GROUPS),
        ATT: likert[["Q19", "Q20", "Q21"]].mean(axis=1).round(3),
        INT: likert[["Q22", "Q23", "Q24", "Q25"]].mean(axis=1).round(3),
        "Giới tính": raw["Q26"].map(GENDER_RAW),
        "Hôn nhân": raw["Q30"].map(MARITAL_RAW),
        "Học vấn": raw["Q28"].map(EDUCATION_RAW),
        "Nhóm tuổi": raw["Q27"].map(lambda v: AGE_GROUPS[v][0]),
        "Nhóm thu nhập": raw["Q29"].map(INCOME_RAW),
    })
    if df.isna().any().any():
        raise ValueError("Có giá trị không mã hóa được:\n" + str(df[df.isna().any(axis=1)].head()))
    return df


def _name_segments(data, labels):
    """Đặt tên cố định vì số thứ tự cụm do thuật toán sinh ra là tùy ý: cụm có ý định đặt tiếp cao nhất là
    Khách trung thành; trong hai cụm còn lại, cụm trẻ hơn là Sinh viên thu nhập thấp."""
    means = data.groupby(labels)[NUM_COLS].mean()
    loyal = means[INT].idxmax()
    rest = means.drop(index=loyal).sort_values("Tuổi").index
    return {rest[0]: "Sinh viên thu nhập thấp", rest[1]: "Người đi làm thu nhập khá", loyal: "Khách trung thành"}


def train(path=DATA_FILE):
    df = load_customers(path)
    data = df[NUM_COLS + CAT_COLS].copy()

    scaler = StandardScaler().fit(data[NUM_COLS])
    X = data.copy()
    X[NUM_COLS] = scaler.transform(data[NUM_COLS])

    kp = KPrototypes(n_clusters=K, init="Cao", n_init=N_INIT, random_state=SEED)
    labels = kp.fit_predict(X.to_numpy(dtype=object), categorical=CAT_IDX)

    names = _name_segments(data, labels)
    customers = df.copy()
    customers["Cluster"] = labels
    customers["Segment"] = pd.Categorical(customers["Cluster"].map(names),
                                          categories=SEGMENT_ORDER, ordered=True)
    num_range = {"Tuổi": AGE_LIMITS, "Thu nhập": (min(INCOME_GROUPS.values()), max(INCOME_GROUPS.values())),
                 ATT: LIKERT_RANGE, INT: LIKERT_RANGE}
    return SegmentModel(kp, scaler, names, customers, num_range)


def predict(model, customers):
    """Trả về tên cụm cho một DataFrame có đủ các cột NUM_COLS và CAT_COLS."""
    X = customers[NUM_COLS + CAT_COLS].copy()
    X[NUM_COLS] = model.scaler.transform(X[NUM_COLS]).astype(float)
    labels = model.kp.predict(X.to_numpy(dtype=object), categorical=CAT_IDX)
    return [model.segment_names[label] for label in labels]


def out_of_range(model, values):
    """Các cột số có giá trị nằm ngoài thang đo của khảo sát (VD tuổi ngoài 15–28)."""
    return [c for c in NUM_COLS if values.get(c) is not None
            and not model.num_range[c][0] <= float(values[c]) <= model.num_range[c][1]]


def predict_partial(model, values):
    """Xếp một khách vào cụm khi có thể thiếu một số thuộc tính (None = bỏ trống).

    Khoảng cách K-Prototypes chỉ tính trên các thuộc tính đã có:
        tổng (giá trị số chuẩn hóa - tâm)^2 + gamma * số thuộc tính phân loại khác tâm.
    Giá trị số ngoài thang đo của khảo sát được kéo về biên (VD tuổi 35 tính như 28, tuổi lớn nhất của
    khảo sát Gen Z). Đủ cả 7 thuộc tính (trong thang đo) thì cho đúng kết quả như predict().
    Cần ít nhất Tuổi hoặc Thu nhập; thiếu cả hai thì trả về None.
    Trả về (tên cụm hoặc None, số thuộc tính đã dùng).
    """
    kp = model.kp
    num_centroids = kp._enc_cluster_centroids[0]
    cat_centroids = kp.cluster_centroids_[:, len(NUM_COLS):]
    used = [c for c in NUM_COLS + CAT_COLS if values.get(c) is not None]
    if not any(c in used for c in ("Tuổi", "Thu nhập")):
        return None, len(used)

    best, best_dist = None, float("inf")
    for k in range(len(num_centroids)):
        dist = 0.0
        for i, col in enumerate(NUM_COLS):
            if values.get(col) is not None:
                x = float(np.clip(float(values[col]), *model.num_range[col]))
                z = (x - model.scaler.mean_[i]) / model.scaler.scale_[i]
                dist += (z - num_centroids[k][i]) ** 2
        mismatch = sum(1 for i, col in enumerate(CAT_COLS)
                       if values.get(col) is not None and values[col] != cat_centroids[k][i])
        dist += kp.gamma * mismatch
        if dist < best_dist:  # bằng nhau thì giữ cụm đứng trước, giống numpy.argmin
            best, best_dist = k, dist
    return model.segment_names[best], len(used)


def segment_profile(customers):
    """Bảng đặc điểm từng cụm, giá trị biến số ở thang đo gốc."""
    g = customers.groupby("Segment", observed=True)
    return pd.DataFrame({
        "Số khách": g.size(),
        "Tỷ lệ (%)": g.size() / len(customers) * 100,
        "Tuổi TB": g["Tuổi"].mean(),
        "Thu nhập TB (triệu)": g["Thu nhập"].mean(),
        "Thu nhập dưới 10 triệu (%)": g["Nhóm thu nhập"].agg(lambda s: (s == "Dưới 10 triệu").mean() * 100),
        f"{ATT} TB (1–7)": g[ATT].mean(),
        f"{INT} TB (1–7)": g[INT].mean(),
        "Nữ (%)": g["Giới tính"].agg(lambda s: (s == "Nữ").mean() * 100),
        "Đã kết hôn (%)": g["Hôn nhân"].agg(lambda s: (s == "Đã kết hôn").mean() * 100),
        "Học vấn phổ biến": g["Học vấn"].agg(lambda s: s.mode()[0]),
    }).round(2)
