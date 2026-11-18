# Phân khúc khách hàng đặt đồ ăn online

Phân khúc khách hàng bằng thuật toán **K-Prototypes** (4 cụm) trên bộ dữ liệu *Online Food Delivery*, kèm giao diện demo viết bằng Streamlit.

**Demo trực tuyến:** https://phan-khuc-khach-hang.streamlit.app/ (không cần cài đặt; nếu app đang "ngủ", bấm nút đánh thức và chờ khoảng 1 phút)

## Cấu trúc thư mục

| File | Nội dung |
|---|---|
| `app.py` | Giao diện demo (Streamlit): thanh trên cùng và điều hướng giữa các trang |
| `views/` | Các trang: trang chủ, đăng nhập, đăng ký, tài khoản, quản trị |
| `auth.py`, `shared.py` | Tài khoản (SQLite `users.db`, không đưa lên git) và phần dùng chung giữa các trang |
| `orders.py` | Giỏ hàng, đặt hàng, trạng thái đơn, đánh giá; suy ra Output/Feedback của mô hình từ đơn hàng (lưu cùng `users.db`) |
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
| `menu.csv` | Thực đơn 36 món, 4 nhóm: Món chính (gà giòn, mì Ý, cơm, burger), Món thêm (khoai, súp, cơm trắng, Mì Ý thêm 7.000₫), Món phụ (tráng miệng), Thức uống; giá lẻ tham khảo từ jollibee.com.vn (16/11/2026) |
| `menu.py` | Thực đơn, lớp Combo, 8 combo mặc định (dùng khi chưa duyệt combo tháng), ưu đãi theo trạng thái khách |
| `combos.py` | Combo theo tháng: đề xuất từ số lượng món mỗi cụm mua vào ngày thường / cuối tuần tháng trước, duyệt, combo đang áp dụng |
| `simulate_orders.py`, `simulated_orders.csv` | Sinh 10.000 đơn mô phỏng (tháng 10/2026) làm dữ liệu tạo combo tháng đầu |
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

**Combo theo tháng** (`combos.py`): đầu mỗi tháng hệ thống gom đơn tháng trước (đơn thật trong `users.db` + đơn mô phỏng); cỡ đơn (số người) = số phần món chính trong đơn. **Mỗi cụm 3 combo**: 2 combo ngày thường theo 2 cỡ đơn phổ biến nhất của ngày thường và 1 combo cuối tuần theo cỡ đơn phổ biến nhất của cuối tuần (mỗi cỡ cần từ 20 đơn). Mỗi combo dựng từ các đơn cùng cụm, cùng loại ngày, cùng cỡ, theo ràng buộc:

- **Món chính** (gà giòn, mì Ý, cơm, burger): đúng bằng số người, có thể khác loại nhưng **tối đa 2 loại**.
- **Thức uống**: đúng bằng số người và **cùng một loại**.
- **Món thêm** (khoai, súp): số phần trung bình mỗi đơn, tối đa 2 loại; **Cơm trắng và Mì Ý thêm không có trong combo** (chỉ bán lẻ).
- **Món phụ** (tráng miệng): không quá số người, tối đa 2 loại; **2 cụm sinh viên (thu nhập thấp) không có món phụ**.
- Giá = giá lẻ giảm 10% rồi làm tròn xuống giá đuôi 5.000₫ hoặc 9.000₫ gần nhất (vd 102.600₫ → 99.000₫), nên thực giảm từ 10% trở lên.

Admin xem lý do, sửa giá rồi **duyệt**; chưa duyệt thì khách tiếp tục thấy combo đã duyệt gần nhất (chưa từng duyệt thì thấy 8 combo mặc định bên dưới). **Combo ngày thường đặt được mọi ngày** (cuối tuần hiện và đặt được cả combo ngày thường lẫn combo cuối tuần); **combo cuối tuần chỉ đặt được Thứ 7–CN**, ngày thường vẫn xem được nhưng nút đặt bị khóa, trong giỏ bị khóa và ghi "Chỉ áp dụng Thứ 7–CN". Combo gợi ý cho khách là combo đặt được hôm nay có số người gần số người trong hộ nhất.

Khi đặt combo, đơn lưu **từng món** trong combo; thành tiền của combo được chia cho các món theo tỷ lệ giá lẻ (tổng đúng bằng giá combo), kèm mã combo. Đơn còn lưu loại ngày và cụm của khách lúc đặt để làm dữ liệu cho tháng sau.

**Đơn mô phỏng** (`simulate_orders.py` → `simulated_orders.csv`): 10.000 đơn tháng 10/2026 của 3000 khách trong dataset, mỗi cụm có thói quen riêng theo ngày thường/cuối tuần (sinh viên hộ nhỏ ăn một mình món rẻ, hội bạn đặt nhóm cuối tuần, dân văn phòng ăn trưa ngày thường và tối cuối tuần cho 2 người, gia đình đặt cả nhà cuối tuần). Đây là **dữ liệu giả lập** để có combo cho tháng đầu; có đơn thật thì được cộng vào. Sinh lại: `python simulate_orders.py 10000 2026-10`.

**Combo mặc định** (thiết kế tay, áp dụng mọi ngày, chỉ dùng khi chưa có combo tháng nào được duyệt; cỡ combo theo số người trong hộ):

| Cụm | Combo | Giá lẻ → giá combo |
|---|---|---|
| Sinh viên hộ nhỏ | SV Tiết Kiệm (1 người), SV Đôi Bạn (2–3 người) | 47k → 39k, 119k → 95k |
| Sinh viên hộ đông | Hội Bạn 4 Người, Hội Bạn 6 Người (5–6 người) | 294k → 245k, 415k → 349k |
| Người đi làm trẻ | Trưa Văn Phòng (1 người), Tối Cặp Đôi (2–3 người); hộ từ 4 người dùng Cả Nhà 4 Người | 83k → 75k, 245k → 219k |
| Người có gia đình hộ đông | Cả Nhà 4 Người (3–4 người), Cả Nhà 5–6 Người | 314k → 269k, 428k → 369k |

Kèm ưu đãi theo trạng thái của khách (Output, Feedback): còn đặt và hài lòng → không có ưu đãi thêm; còn đặt nhưng chưa hài lòng → voucher xin lỗi 20k; đã ngừng nhưng từng hài lòng → voucher 30k; đã ngừng và chưa hài lòng → voucher 50k + hoàn tiền nếu giao trễ.

**Khách hàng**

- **Trang chủ**: banner, nhóm món, "Dành cho bạn" (combo ngày thường và cuối tuần của nhóm khách, combo áp dụng hôm nay viền vàng kèm ưu đãi riêng), combo khuyến mãi của tháng chia tab Ngày thường / Cuối tuần (tab hôm nay đứng trước), món lẻ theo nhóm món.
- **Đăng ký / Đăng nhập**: mật khẩu 8–72 ký tự (băm scrypt), sai 5 lần liên tiếp thì khóa 15 phút.
- **Giỏ hàng / Đặt hàng** (giống web La Che Fresca): nút "Thêm vào giỏ" trên mỗi combo và món (phải đăng nhập); giỏ hàng có ô chọn món, sửa số lượng, xóa; form giao hàng điền sẵn từ hồ sơ, thanh toán COD hoặc chuyển khoản; chỉ đặt các món được chọn.
- **Đánh giá**: đặt xong hiện box chấm 1–5 sao cho cả đơn (kèm góp ý); có thể bỏ qua và đánh giá sau trong "Đơn hàng của tôi".
- **Tài khoản**: một form "Thông tin cá nhân" gồm họ tên, số điện thoại, địa chỉ và 6 thông tin cho mô hình (tuổi, số người trong gia đình, giới tính, hôn nhân, nghề nghiệp, học vấn), đều không bắt buộc. "Đơn hàng của tôi": trạng thái đơn, hủy đơn đang chờ xác nhận, đánh giá đơn chưa đánh giá. Có đổi mật khẩu.
- **Xếp nhóm**: 2 thuộc tính còn lại của mô hình không hỏi khách mà suy ra từ đơn hàng — *tiếp tục đặt món* = có đơn chưa hủy trong 30 ngày gần nhất (từng đặt nhưng lâu hơn = không; chưa đặt đơn nào = bỏ qua), *hài lòng* = sao trung bình từ 4 (chưa đánh giá = bỏ qua). Khoảng cách K-Prototypes chỉ tính trên thông tin đã có; cần ít nhất tuổi hoặc số người trong gia đình.

**Quản trị** (chỉ admin; tài khoản tạo sẵn lần đầu chạy: `admin@fastbite.vn` / `Admin@123`, đổi bằng mục `[admin]` với `email`, `password` trong `.streamlit/secrets.toml`)

- **Đơn hàng**: số đơn chờ xác nhận / đang giao / hoàn tất, doanh thu; lọc theo trạng thái, tìm theo mã đơn, tên, SĐT; chuyển trạng thái Chờ xác nhận → Đang giao → Hoàn tất (hoặc Hủy); xem đánh giá, cụm và loại ngày lúc đặt.
- **Combo theo tháng**: số đơn tháng trước theo cụm × loại ngày (thật / mô phỏng), món mua nhiều nhất của từng ô, danh sách đề xuất kèm lý do và giá lẻ → giá combo; sửa giá, duyệt, bỏ, duyệt tất cả, tạo lại đề xuất.
- **Phân khúc khách mới**: nhập thông tin một khách hàng để xem khách đó thuộc cụm nào, kèm đặc điểm, chiến lược marketing, combo khuyến mãi (theo số người trong hộ) và ưu đãi kèm theo.
- **Tổng quan các cụm**: quy mô từng cụm, bảng đặc điểm, biểu đồ thành phần theo từng thuộc tính, bảng tổng hợp combo và combo của từng cụm.
- **Danh sách khách hàng**: xem, lọc toàn bộ khách hàng của bộ dữ liệu theo cụm và tải danh sách về dạng CSV.
- **Tài khoản khách hàng**: các tài khoản đã đăng ký trong app, thông tin đã điền, số đơn, sao trung bình, hai thuộc tính suy ra từ đơn hàng, nhóm, combo và ưu đãi riêng của từng người, tải CSV.

Lưu ý: đăng nhập và giỏ hàng giữ trong phiên làm việc của trình duyệt, tải lại trang (F5) sẽ phải đăng nhập lại và giỏ hàng trống (đơn đã đặt vẫn được lưu). Trên Streamlit Cloud, `users.db` bị xóa mỗi khi app khởi động lại.

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
