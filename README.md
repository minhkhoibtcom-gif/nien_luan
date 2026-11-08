# Phân khúc khách hàng đặt đồ ăn online

Phân khúc khách hàng bằng thuật toán **K-Prototypes** (4 cụm) trên bộ dữ liệu *Online Food Delivery*, kèm giao diện demo viết bằng Streamlit.

**Demo trực tuyến:** https://phan-khuc-khach-hang.streamlit.app/ (không cần cài đặt; nếu app đang "ngủ", bấm nút đánh thức và chờ khoảng 1 phút)

## Cấu trúc thư mục

| File | Nội dung |
|---|---|
| `app.py` | Giao diện demo (Streamlit) |
| `segmentation.py` | Làm sạch dữ liệu, huấn luyện K-Prototypes, dự đoán cụm, chiến lược cho từng cụm |
| `online food delivery dataset.csv` | Dữ liệu gốc |
| `kprototypes.ipynb` | Notebook phân tích: khám phá dữ liệu, chọn số cụm, đánh giá |
| `customer_segments.csv` | Kết quả gán cụm do notebook xuất ra |
| `.streamlit/config.toml` | Cấu hình giao diện |

## Chạy demo trên máy

Yêu cầu: **Python 3.11 trở lên** (khi phát triển dùng Python 3.14).

```bash
git clone <link-repo>
cd nien_luan

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python -m streamlit run app.py
```

Trình duyệt sẽ tự mở http://localhost:8501. Lần đầu mở, mô hình phải huấn luyện mất vài giây, các lần sau sẽ dùng lại kết quả đã lưu.

## Các chức năng

- **Phân khúc khách mới**: nhập thông tin một khách hàng để xem khách đó thuộc cụm nào, kèm đặc điểm và chiến lược marketing gợi ý cho cụm đó.
- **Tổng quan các cụm**: quy mô từng cụm, bảng đặc điểm, biểu đồ thành phần theo từng thuộc tính.
- **Danh sách khách hàng**: xem, lọc toàn bộ khách hàng theo cụm và tải danh sách về dạng CSV.

## Dữ liệu mẫu để thử

Mỗi dòng dưới đây được xếp vào một cụm khác nhau:

| Tuổi | Số người trong hộ | Giới tính | Hôn nhân | Nghề nghiệp | Học vấn | Output | Feedback | Cụm |
|---|---|---|---|---|---|---|---|---|
| 20 | 2 | Female | Single | Student | Graduate | Yes | Positive | Sinh viên hộ nhỏ |
| 21 | 6 | Male | Single | Student | Graduate | Yes | Positive | Sinh viên hộ đông |
| 26 | 2 | Male | Single | Employee | Post Graduate | Yes | Positive | Người đi làm trẻ |
| 31 | 5 | Female | Married | Employee | Graduate | No | Negative | Người có gia đình hộ đông |

## Chạy notebook (không bắt buộc)

Notebook dùng thêm một số thư viện không có trong `requirements.txt`:

```bash
pip install jupyter matplotlib gower
```
