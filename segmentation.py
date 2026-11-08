"""Mô hình phân khúc khách hàng: cùng quy trình và tham số với kprototypes.ipynb."""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from kmodes.kprototypes import KPrototypes
from sklearn.preprocessing import StandardScaler

DATA_FILE = Path(__file__).parent / "online food delivery dataset.csv"

K = 4
NUM_COLS = ["Age", "Family size"]
CAT_COLS = ["Gender", "Marital Status", "Occupation",
            "Educational Qualifications", "Output", "Feedback"]
CAT_IDX = list(range(len(NUM_COLS), len(NUM_COLS) + len(CAT_COLS)))

CATEGORY_ORDER = {
    "Gender": ["Male", "Female"],
    "Marital Status": ["Single", "Married", "Prefer not to say"],
    "Occupation": ["Student", "Employee", "Self Employeed", "House wife"],
    "Educational Qualifications": ["Uneducated", "School", "Graduate", "Post Graduate", "Ph.D"],
    "Output": ["Yes", "No"],
    "Feedback": ["Positive", "Negative"],
    "Monthly Income": ["No Income", "Below Rs.10000", "10001 to 25000",
                       "25001 to 50000", "More than 50000"],
}
HIGH_INCOME = ["25001 to 50000", "More than 50000"]

# Tên hiển thị trên giao diện (dữ liệu và mô hình vẫn dùng tên cột gốc).
# Giả định của đề tài: Output = Yes nghĩa là khách tiếp tục đặt món online.
DISPLAY_NAMES = {"Output": "Tiếp tục đặt món"}
HIDDEN_COLS = ["latitude", "longitude", "Output"]  # chỉ ẩn ở bảng danh sách và CSV

SEGMENT_ORDER = ["Sinh viên hộ nhỏ", "Sinh viên hộ đông",
                 "Người đi làm trẻ", "Người có gia đình hộ đông"]

STRATEGIES = {
    "Sinh viên hộ nhỏ": [
        "Nhóm đông nhất nhưng đa số chưa có thu nhập: ưu tiên mã giảm giá sinh viên và ưu đãi theo khung giờ.",
        "Thiết kế suất ăn một người giá thấp, miễn phí giao hàng cho đơn nhỏ.",
        "Tiếp cận qua mạng xã hội và hợp tác với trường đại học, câu lạc bộ sinh viên.",
    ],
    "Sinh viên hộ đông": [
        "Nhóm có tỷ lệ tiếp tục đặt món và phản hồi tích cực cao nhất: tập trung giữ chân bằng chương trình điểm thưởng.",
        "Khuyến khích giới thiệu bạn bè, thưởng cho cả người giới thiệu và người được giới thiệu.",
        "Đẩy combo nhóm và combo gia đình để tăng giá trị mỗi đơn.",
    ],
    "Người đi làm trẻ": [
        "Đa số có thu nhập trên 25.000, phần lớn đang đi làm nên cần sự tiện lợi: tung gói giao bữa trưa văn phòng và gói đăng ký theo tháng.",
        "Cam kết thời gian giao đúng giờ, gợi ý thực đơn cao cấp hơn thay vì giảm giá sâu.",
        "Thu thập phản hồi sau đơn hàng để cải thiện tỷ lệ phản hồi tích cực còn ở mức trung bình.",
    ],
    "Người có gia đình hộ đông": [
        "Đa số có thu nhập trên 25.000 nhưng tỷ lệ tiếp tục đặt món và phản hồi tích cực thấp nhất: ưu tiên khảo sát lý do không hài lòng trước khi chi cho quảng cáo.",
        "Cải thiện chất lượng dịch vụ, rồi gửi ưu đãi mời quay lại cho khách từng phản hồi tiêu cực.",
        "Giới thiệu combo gia đình và đặt lịch trước cho bữa tối, cuối tuần.",
    ],
}


@dataclass
class SegmentModel:
    kp: KPrototypes
    scaler: StandardScaler
    segment_names: dict
    customers: pd.DataFrame  # dữ liệu đã làm sạch, thêm cột Cluster và Segment


def load_customers(path=DATA_FILE):
    """Đọc và làm sạch dữ liệu giống notebook."""
    df = pd.read_csv(path).drop(columns=["Unnamed: 13"])
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()
    return df.drop_duplicates().reset_index(drop=True)


def _name_segments(data, labels):
    """Gán tên theo Family size và Age vì số thứ tự cụm do thuật toán sinh ra là tùy ý."""
    means = data.groupby(labels)[NUM_COLS].mean().sort_values("Family size")
    small_family = means.iloc[:2].sort_values("Age").index
    large_family = means.iloc[2:].sort_values("Age").index
    return {
        small_family[0]: "Sinh viên hộ nhỏ",
        large_family[0]: "Sinh viên hộ đông",
        small_family[1]: "Người đi làm trẻ",
        large_family[1]: "Người có gia đình hộ đông",
    }


def train(path=DATA_FILE):
    df = load_customers(path)
    data = df[NUM_COLS + CAT_COLS].copy()

    scaler = StandardScaler().fit(data[NUM_COLS])
    X = data.copy()
    X[NUM_COLS] = scaler.transform(data[NUM_COLS])

    kp = KPrototypes(n_clusters=K, init="Cao", n_init=5, random_state=42)
    labels = kp.fit_predict(X.to_numpy(), categorical=CAT_IDX)

    names = _name_segments(data, labels)
    customers = df.copy()
    customers["Cluster"] = labels
    customers["Segment"] = pd.Categorical(customers["Cluster"].map(names),
                                          categories=SEGMENT_ORDER, ordered=True)
    return SegmentModel(kp, scaler, names, customers)


def predict(model, customers):
    """Trả về tên cụm cho một DataFrame có đủ các cột NUM_COLS và CAT_COLS."""
    X = customers[NUM_COLS + CAT_COLS].copy()
    X[NUM_COLS] = model.scaler.transform(X[NUM_COLS]).astype(float)
    labels = model.kp.predict(X.to_numpy(dtype=object), categorical=CAT_IDX)
    return [model.segment_names[label] for label in labels]


def segment_profile(customers):
    """Bảng đặc điểm từng cụm, giá trị biến số ở thang đo gốc."""
    g = customers.groupby("Segment", observed=True)
    return pd.DataFrame({
        "Số khách": g.size(),
        "Tỷ lệ (%)": g.size() / len(customers) * 100,
        "Age TB": g["Age"].mean(),
        "Family size TB": g["Family size"].mean(),
        "Gender phổ biến": g["Gender"].agg(lambda s: s.mode()[0]),
        "Marital Status phổ biến": g["Marital Status"].agg(lambda s: s.mode()[0]),
        "Occupation phổ biến": g["Occupation"].agg(lambda s: s.mode()[0]),
        "Education phổ biến": g["Educational Qualifications"].agg(lambda s: s.mode()[0]),
        "Tiếp tục đặt món (%)": g["Output"].agg(lambda s: (s == "Yes").mean() * 100),
        "Feedback = Positive (%)": g["Feedback"].agg(lambda s: (s == "Positive").mean() * 100),
        "Không có thu nhập (%)": g["Monthly Income"].agg(lambda s: (s == "No Income").mean() * 100),
        "Thu nhập > 25.000 (%)": g["Monthly Income"].agg(lambda s: s.isin(HIGH_INCOME).mean() * 100),
    }).round(1)
