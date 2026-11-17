# Phân khúc khách hàng đặt đồ ăn online

Phân khúc khách hàng bằng thuật toán **K-Prototypes** (4 cụm) trên bộ dữ liệu *Online Food Delivery*, kèm giao diện demo viết bằng Streamlit.

**Demo trực tuyến:** https://phan-khuc-khach-hang.streamlit.app/ (không cần cài đặt; nếu app đang "ngủ", bấm nút đánh thức và chờ khoảng 1 phút)

## Cấu trúc thư mục

| File | Nội dung |
|---|---|
| `app.py` | Giao diện demo (Streamlit): thanh trên cùng và điều hướng giữa các trang |
| `views/` | Các trang: trang chủ, đăng nhập, đăng ký, tài khoản, quản trị |
| `auth.py`, `shared.py` | Tài khoản (SQLite `users.db`, không đưa lên git) và phần dùng chung giữa các trang |
| `segmentation.py` | Làm sạch dữ liệu, huấn luyện K-Prototypes, dự đoán cụm, chiến lược cho từng cụm |
| `online food delivery dataset.csv` | Dữ liệu gốc (388 dòng, 285 mẫu sau khi bỏ trùng) |
| `online food delivery dataset 3000.csv` | Dữ liệu mở rộng dùng để huấn luyện: giữ nguyên 388 dòng gốc + 2715 dòng tổng hợp, còn 3000 mẫu sau khi bỏ trùng |
| `online food delivery dataset 1000.csv` | Bản mở rộng cũ 1000 mẫu (không còn dùng; chính là phần đầu của bản 3000) |
| `generate_dataset.py` | Script sinh dữ liệu mở rộng từ dữ liệu gốc |
| `export_segment_model.py` | Xuất 4 tâm cụm + tham số chuẩn hóa ra `segment_model.json` (và file test) để chương trình khác tự xếp khách vào nhóm |
| `kprototypes.ipynb` | Notebook phân tích: khám phá dữ liệu, chọn số cụm, đánh giá |
| `customer_segments.csv` | Kết quả gán cụm do notebook xuất ra |
| `.streamlit/config.toml` | Cấu hình giao diện |
| `start.bat`, `stop.bat` | Bật / tắt app demo trên Windows |
| `ui.py` | Giao diện cửa hàng FASTBITE: tông đỏ – vàng, thanh trên cùng, banner, thẻ món, thẻ combo, chân trang |
| `menu.csv` | Thực đơn: 35 món, giá lẻ tham khảo từ jollibee.com.vn (16/11/2026) |
| `menu.py` | 8 combo khuyến mãi cho 4 cụm, chọn combo theo nhóm và số người trong hộ, ưu đãi theo trạng thái khách |
| `assets/` | Logo FASTBITE; `assets/products/` để bổ sung ảnh món và combo (xem `README.txt` trong đó) |

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

Trên Windows có thể bấm đúp `start.bat` thay cho các lệnh trên: lần đầu script tự tạo `venv` và cài thư viện, sau đó bật app và mở trình duyệt. Bấm đúp `stop.bat` để tắt app.

Trình duyệt sẽ tự mở http://localhost:8501. Lần đầu mở, mô hình phải huấn luyện mất vài giây, các lần sau sẽ dùng lại kết quả đã lưu.

## Các chức năng

App đóng vai cửa hàng đồ ăn nhanh **FASTBITE** (tên giả định của đồ án, không liên quan tới Jollibee); bố cục theo web bán sữa La Che Fresca (đồ án CT275), thực đơn dùng món và giá lẻ của Jollibee để minh họa.

**Combo khuyến mãi** (giá lẻ tính tự động từ `menu.csv`; cỡ combo chọn theo số người trong hộ):

| Cụm | Combo | Giá lẻ → giá combo |
|---|---|---|
| Sinh viên hộ nhỏ | SV Tiết Kiệm (1 người), SV Đôi Bạn (2–3 người) | 47k → 39k, 119k → 95k |
| Sinh viên hộ đông | Hội Bạn 4 Người, Hội Bạn 6 Người (5–6 người) | 294k → 245k, 415k → 349k |
| Người đi làm trẻ | Trưa Văn Phòng (1 người), Tối Cặp Đôi (2–3 người); hộ từ 4 người dùng Cả Nhà 4 Người | 83k → 75k, 245k → 219k |
| Người có gia đình hộ đông | Cả Nhà 4 Người (3–4 người), Cả Nhà 5–6 Người | 314k → 269k, 428k → 369k |

Kèm ưu đãi theo trạng thái của khách (Output, Feedback): còn đặt và hài lòng → tích điểm; còn đặt nhưng chưa hài lòng → voucher xin lỗi 20k; đã ngừng nhưng từng hài lòng → voucher 30k; đã ngừng và chưa hài lòng → voucher 50k + hoàn tiền nếu giao trễ.

**Khách hàng**

- **Trang chủ**: banner, nhóm món, "Dành cho bạn" (các combo của nhóm khách, combo hợp nhất viền vàng kèm ưu đãi riêng), tất cả combo khuyến mãi, món lẻ theo nhóm món.
- **Đăng ký / Đăng nhập**: mật khẩu 8–72 ký tự (băm scrypt), sai 5 lần liên tiếp thì khóa 15 phút.
- **Tài khoản**: họ tên, số điện thoại, địa chỉ và 8 thông tin của mô hình (tuổi, số người trong gia đình, giới tính, hôn nhân, nghề nghiệp, học vấn, có tiếp tục đặt món online, mức hài lòng). Tất cả đều không bắt buộc; ô bỏ trống được bỏ qua khi xếp nhóm (khoảng cách K-Prototypes chỉ tính trên thông tin đã điền, cần ít nhất tuổi hoặc số người trong gia đình). Có đổi mật khẩu.

**Quản trị** (chỉ admin; tài khoản tạo sẵn lần đầu chạy: `admin@fastbite.vn` / `Admin@123`, đổi bằng mục `[admin]` với `email`, `password` trong `.streamlit/secrets.toml`)

- **Phân khúc khách mới**: nhập thông tin một khách hàng để xem khách đó thuộc cụm nào, kèm đặc điểm, chiến lược marketing, combo khuyến mãi (theo số người trong hộ) và ưu đãi kèm theo.
- **Tổng quan các cụm**: quy mô từng cụm, bảng đặc điểm, biểu đồ thành phần theo từng thuộc tính, bảng tổng hợp combo và combo của từng cụm.
- **Danh sách khách hàng**: xem, lọc toàn bộ khách hàng của bộ dữ liệu theo cụm và tải danh sách về dạng CSV.
- **Tài khoản khách hàng**: các tài khoản đã đăng ký trong app, thông tin đã điền, nhóm, combo và ưu đãi riêng của từng người, tải CSV.

Lưu ý: đăng nhập giữ trong phiên làm việc của trình duyệt, tải lại trang (F5) sẽ phải đăng nhập lại. Trên Streamlit Cloud, `users.db` bị xóa mỗi khi app khởi động lại.

## Dữ liệu mở rộng

Dữ liệu gốc chỉ có 285 mẫu không trùng nên được mở rộng lên 3000 mẫu bằng `generate_dataset.py`. Mỗi mẫu tổng hợp được tạo từ một khách hàng có thật: tuổi lệch ngẫu nhiên ±2, số người trong hộ lệch ±1 (xác suất 30%), mỗi thuộc tính phân loại có 5% khả năng lấy theo một khách khác cùng nghề nghiệp, `Customer Type` tính lại từ số người trong hộ, vị trí lấy theo một mã bưu chính có trong dữ liệu gốc. Mẫu trùng với mẫu đã có bị bỏ. Seed cố định nên chạy lại cho ra cùng kết quả (tham số là số mẫu, mặc định 3000):

```bash
python generate_dataset.py
```

Trên dữ liệu mở rộng, mô hình vẫn cho ra 4 cụm với đặc điểm tương tự dữ liệu gốc. Lưu ý: 2715 dòng cuối (khoảng 90% bộ 3000 mẫu) là dữ liệu tổng hợp, không phải khảo sát thật.

## Dữ liệu mẫu để thử

Mỗi dòng dưới đây được xếp vào một cụm khác nhau:

| Tuổi | Số người trong hộ | Giới tính | Hôn nhân | Nghề nghiệp | Học vấn | Output | Feedback | Cụm |
|---|---|---|---|---|---|---|---|---|
| 20 | 2 | Female | Single | Student | Graduate | Yes | Positive | Sinh viên hộ nhỏ |
| 21 | 6 | Male | Single | Student | Graduate | Yes | Positive | Sinh viên hộ đông |
| 27 | 2 | Male | Married | Employee | Graduate | Yes | Positive | Người đi làm trẻ |
| 31 | 5 | Female | Married | Employee | Graduate | No | Negative | Người có gia đình hộ đông |

## Chạy notebook (không bắt buộc)

Notebook dùng thêm một số thư viện không có trong `requirements.txt`:

```bash
pip install jupyter matplotlib gower
```
