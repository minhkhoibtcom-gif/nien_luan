# Phân khúc khách hàng đặt đồ ăn online

Phân khúc khách hàng bằng thuật toán **K-Prototypes** (4 cụm) trên bộ dữ liệu *Online Food Delivery*, kèm giao diện demo viết bằng Streamlit.

**Demo trực tuyến:** https://phan-khuc-khach-hang.streamlit.app/ (không cần cài đặt; nếu app đang "ngủ", bấm nút đánh thức và chờ khoảng 1 phút)

## Cấu trúc thư mục

| File | Nội dung |
|---|---|
| `app.py` | Giao diện demo (Streamlit) |
| `segmentation.py` | Làm sạch dữ liệu, huấn luyện K-Prototypes, dự đoán cụm, chiến lược cho từng cụm |
| `online food delivery dataset.csv` | Dữ liệu gốc (388 dòng, 285 mẫu sau khi bỏ trùng) |
| `online food delivery dataset 1000.csv` | Dữ liệu mở rộng dùng để huấn luyện: giữ nguyên 388 dòng gốc + 715 dòng tổng hợp, còn 1000 mẫu sau khi bỏ trùng |
| `generate_dataset.py` | Script sinh dữ liệu mở rộng từ dữ liệu gốc |
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

## Dữ liệu mở rộng

Dữ liệu gốc chỉ có 285 mẫu không trùng nên được mở rộng lên 1000 mẫu bằng `generate_dataset.py`. Mỗi mẫu tổng hợp được tạo từ một khách hàng có thật: tuổi lệch ngẫu nhiên ±2, số người trong hộ lệch ±1 (xác suất 30%), mỗi thuộc tính phân loại có 5% khả năng lấy theo một khách khác cùng nghề nghiệp, vị trí lấy theo một mã bưu chính có trong dữ liệu gốc. Mẫu trùng với mẫu đã có bị bỏ. Seed cố định nên chạy lại cho ra cùng kết quả:

```bash
python generate_dataset.py
```

Trên dữ liệu mở rộng, mô hình vẫn cho ra 4 cụm với đặc điểm tương tự dữ liệu gốc. Lưu ý: 715 dòng cuối là dữ liệu tổng hợp, không phải khảo sát thật.

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
