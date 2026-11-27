# Phân khúc khách hàng đặt đồ ăn online

Phân khúc khách hàng bằng thuật toán **K-Prototypes** (3 cụm) trên dataset khảo sát **Gen Z Việt Nam** về đặt đồ ăn online (361 người, *Data in Brief* 2023, OSF doi 10.17605/OSF.IO/TEPXB), kèm giao diện demo viết bằng Streamlit.

**Demo trực tuyến:** https://phan-khuc-khach-hang.streamlit.app/ (không cần cài đặt; nếu app đang "ngủ", bấm nút đánh thức và chờ khoảng 1 phút)

## Cấu trúc thư mục

| File | Nội dung |
|---|---|
| `app.py` | Giao diện demo (Streamlit): thanh trên cùng và điều hướng giữa các trang |
| `views/` | Các trang: trang chủ, đăng nhập, đăng ký, tài khoản, quản trị |
| `db.py` | Kết nối database: SQLite `users.db` trên máy (không đưa lên git), PostgreSQL khi có cấu hình trong Secrets; schema các bảng |
| `migrate_to_postgres.py` | Chép một lần toàn bộ dữ liệu từ `users.db` sang PostgreSQL |
| `auth.py`, `shared.py` | Tài khoản và phần dùng chung giữa các trang |
| `orders.py` | Giỏ hàng, đặt hàng, trạng thái đơn, đánh giá; suy ra Thái độ / Ý định đặt tiếp của mô hình từ đánh giá và đơn hàng |
| `segmentation.py` | Đọc và mã hóa dữ liệu, huấn luyện K-Prototypes, dự đoán cụm, chiến lược cho từng cụm |
| `data/genz_vn.xlsx` | Dataset Gen Z Việt Nam: 361 người 15–28 tuổi, câu Q1–Q25 thang Likert 7 mức, Q26–Q30 nhân khẩu học |
| `thu_nghiem_vn/` | Chọn số cụm K (`chon_k.py`, 9 biểu đồ, bảng chỉ số) và file Word `ly_do_chon_K.docx` |
| `archive/` | Dataset Ấn Độ 3000 mẫu và script sinh dữ liệu của phiên bản trước (không còn dùng) |
| `export_segment_model.py` | Xuất 3 tâm cụm + tham số chuẩn hóa ra `segment_model.json` (và file test) để chương trình khác tự xếp khách vào nhóm |
| `export_centroids.py` | Ghi tâm cụm qua từng vòng lặp của K-Prototypes ra `centroids_iterations.txt` |
| `kprototypes.ipynb` | Notebook phân tích: mã hóa dữ liệu, chọn số cụm, đặc điểm và chiến lược từng cụm |
| `customer_segments.csv` | Kết quả gán cụm do notebook xuất ra |
| `compare_clustering.py` | So sánh K-Prototypes với K-Means, K-Modes, Hierarchical; xuất `so_sanh_chi_so.csv` và 9 biểu đồ trong `figures/so_sanh/` |
| `.streamlit/config.toml` | Cấu hình giao diện |
| `start.bat`, `stop.bat` | Bật / tắt app demo trên Windows |
| `ui.py` | Giao diện cửa hàng FASTBITE: tông đỏ – vàng, thanh trên cùng, banner, thẻ món, thẻ combo, chân trang |
| `menu.csv` | Thực đơn 66 món, 4 nhóm: Món chính (gà giòn, mì Ý, cơm, burger), Món thêm (khoai, súp, cơm trắng, Mì Ý thêm 7.000₫), Món phụ (tráng miệng), Thức uống; 36 món và giá lẻ tham khảo từ jollibee.com.vn (16/11/2026), 30 món còn lại là món giả định |
| `menu.py` | Thực đơn, lớp Combo, 9 combo mặc định (dùng khi chưa duyệt combo tháng), ưu đãi theo trạng thái khách |
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

**Combo theo tháng** (`combos.py`): đầu mỗi tháng hệ thống gom đơn tháng trước (đơn thật trong database + đơn mô phỏng); cỡ đơn (số người) = số phần món chính trong đơn. **Mỗi cụm 3 combo**: 2 combo ngày thường theo 2 cỡ đơn phổ biến nhất của ngày thường và 1 combo cuối tuần theo cỡ đơn phổ biến nhất của cuối tuần (mỗi cỡ cần từ 20 đơn). Mỗi combo dựng từ các đơn cùng cụm, cùng loại ngày, cùng cỡ, theo ràng buộc:

- **Món chính** (gà giòn, mì Ý, cơm, burger): đúng bằng số người, có thể khác loại nhưng **tối đa 2 loại**.
- **Thức uống**: đúng bằng số người và **cùng một loại**.
- **Món thêm** (khoai, súp): số phần trung bình mỗi đơn, tối đa 2 loại; **Cơm trắng và Mì Ý thêm không có trong combo** (chỉ bán lẻ).
- **Món phụ** (tráng miệng): không quá số người, tối đa 2 loại; **cụm Sinh viên thu nhập thấp không có món phụ**.
- Giá = giá lẻ giảm 10% rồi làm tròn xuống giá đuôi 5.000₫ hoặc 9.000₫ gần nhất (vd 102.600₫ → 99.000₫), nên thực giảm từ 10% trở lên.

Admin xem lý do, sửa giá rồi **duyệt**; chưa duyệt thì khách tiếp tục thấy combo đã duyệt gần nhất (chưa từng duyệt thì thấy 9 combo mặc định bên dưới). **Combo ngày thường đặt được mọi ngày** (cuối tuần hiện và đặt được cả combo ngày thường lẫn combo cuối tuần); **combo cuối tuần chỉ đặt được Thứ 7–CN**, ngày thường vẫn xem được nhưng nút đặt bị khóa, trong giỏ bị khóa và ghi "Chỉ áp dụng Thứ 7–CN". Combo gợi ý cho khách là combo đặt được hôm nay có số người gần số người khách thường đặt nhất (ô không bắt buộc trong hồ sơ; bỏ trống thì gợi ý combo nhỏ nhất).

Khi đặt combo, đơn lưu **từng món** trong combo; thành tiền của combo được chia cho các món theo tỷ lệ giá lẻ (tổng đúng bằng giá combo), kèm mã combo. Đơn còn lưu loại ngày và cụm của khách lúc đặt để làm dữ liệu cho tháng sau.

**Đơn mô phỏng** (`simulate_orders.py` → `simulated_orders.csv`): 10.000 đơn tháng 10/2026 của 361 khách trong dataset, khách có ý định đặt tiếp cao đặt nhiều hơn. Dataset không có số người trong hộ nên mỗi cụm có phân bố số người mỗi đơn riêng (sinh viên 1–2 người, người đi làm 2–4 người, khách trung thành 1–3 người, cuối tuần đông hơn) và thói quen món riêng theo ngày thường/cuối tuần. Đây là **dữ liệu giả lập** để có combo cho tháng đầu; có đơn thật thì được cộng vào. Sinh lại: `python simulate_orders.py 10000 2026-10`.

**Combo mặc định** (thiết kế tay, áp dụng mọi ngày, chỉ dùng khi chưa có combo tháng nào được duyệt; giá = giá lẻ giảm 10% rồi làm tròn đuôi 5k/9k; cỡ combo theo số người khách thường đặt):

| Cụm | Combo | Giá lẻ → giá combo |
|---|---|---|
| Sinh viên thu nhập thấp | SV Tiết Kiệm (1 người), SV Đôi Bạn (2), Hội Bạn 3 Người; không có món phụ | 47k → 39k, 119k → 105k, 166k → 149k |
| Người đi làm thu nhập khá | Tối Cặp Đôi (2 người), Cả Nhà 3 Người, Cả Nhà 4 Người | 205k → 179k, 272k → 239k, 376k → 335k |
| Khách trung thành | Trưa Quen Thuộc (1 người), Đôi Bạn Thân (2), Nhóm Nhỏ 3 Người | 98k → 85k, 160k → 139k, 297k → 265k |

Kèm ưu đãi theo trạng thái của khách (còn đặt trong 30 ngày, hài lòng = sao TB từ 4): còn đặt và hài lòng → không có ưu đãi thêm; còn đặt nhưng chưa hài lòng → voucher xin lỗi 20k; đã ngừng nhưng từng hài lòng → voucher 30k; đã ngừng và chưa hài lòng → voucher 50k + hoàn tiền nếu giao trễ.

**Khách hàng**

- **Trang chủ**: banner, nhóm món, "Dành cho bạn" (combo ngày thường và cuối tuần của nhóm khách, combo áp dụng hôm nay viền vàng kèm ưu đãi riêng), combo khuyến mãi của tháng chia tab Ngày thường / Cuối tuần (tab hôm nay đứng trước), món lẻ theo nhóm món.
- **Đăng ký / Đăng nhập**: mật khẩu 8–72 ký tự (băm scrypt), sai 5 lần liên tiếp thì khóa 15 phút.
- **Giỏ hàng / Đặt hàng** (giống web La Che Fresca): nút "Thêm vào giỏ" trên mỗi combo và món (phải đăng nhập); giỏ hàng có ô chọn món, sửa số lượng, xóa; form giao hàng điền sẵn từ hồ sơ, thanh toán COD hoặc chuyển khoản; chỉ đặt các món được chọn.
- **Đánh giá**: đặt xong hiện box chấm 1–5 sao cho cả đơn (kèm góp ý); có thể bỏ qua và đánh giá sau trong "Đơn hàng của tôi".
- **Tài khoản**: một form "Thông tin cá nhân" gồm họ tên, số điện thoại, địa chỉ, 5 thông tin cho mô hình (tuổi, nhóm thu nhập, giới tính, hôn nhân, học vấn) và số người thường đặt (chỉ để chọn cỡ combo), đều không bắt buộc. "Đơn hàng của tôi": trạng thái đơn, hủy đơn đang chờ xác nhận, đánh giá đơn chưa đánh giá. Có đổi mật khẩu.
- **Xếp nhóm**: 2 thuộc tính còn lại của mô hình (thang 1–7 như khảo sát) không hỏi khách mà suy ra — *Thái độ* = sao đánh giá trung bình đổi từ thang 1–5 sang 1–7 (chưa đánh giá = bỏ qua), *Ý định đặt tiếp* = số đơn chưa hủy trong 30 ngày: 0 đơn → 3, 1 đơn → 4,5, từ 2 đơn → 6 (chưa đặt đơn nào = bỏ qua). Khoảng cách K-Prototypes chỉ tính trên thông tin đã có; cần ít nhất tuổi hoặc thu nhập. Tuổi ngoài 15–28 (khoảng tuổi của khảo sát) được tính như tuổi gần nhất trong khoảng, kèm cảnh báo.

**Quản trị** (chỉ admin; tài khoản tạo sẵn lần đầu chạy: `admin@fastbite.vn` / `Admin@123`, đổi bằng mục `[admin]` với `email`, `password` trong `.streamlit/secrets.toml`)

- **Đơn hàng**: số đơn chờ xác nhận / đang giao / hoàn tất, doanh thu; lọc theo trạng thái, tìm theo mã đơn, tên, SĐT; chuyển trạng thái Chờ xác nhận → Đang giao → Hoàn tất (hoặc Hủy); xem đánh giá, cụm và loại ngày lúc đặt.
- **Combo theo tháng**: số đơn tháng trước theo cụm × loại ngày (thật / mô phỏng), món mua nhiều nhất của từng ô, danh sách đề xuất kèm lý do và giá lẻ → giá combo; sửa giá, duyệt, bỏ, duyệt tất cả, tạo lại đề xuất.
- **Tạo thử khách mới**: nhập thông tin một khách hàng để xem khách đó thuộc cụm nào, kèm đặc điểm, chiến lược marketing, combo khuyến mãi (theo số người thường đặt) và ưu đãi kèm theo.
- **Tổng quan các cụm**: quy mô từng cụm, bảng đặc điểm, biểu đồ thành phần theo từng thuộc tính, bảng tổng hợp combo và combo của từng cụm.
- **Danh sách khách hàng**: xem, lọc toàn bộ khách hàng của bộ dữ liệu theo cụm và tải danh sách về dạng CSV.
- **Tài khoản khách hàng**: các tài khoản đã đăng ký trong app, thông tin đã điền, số đơn, sao trung bình, Thái độ và Ý định đặt tiếp suy ra, nhóm, combo và ưu đãi riêng của từng người, tải CSV.

Lưu ý: đăng nhập và giỏ hàng giữ trong phiên làm việc của trình duyệt, tải lại trang (F5) sẽ phải đăng nhập lại và giỏ hàng trống (đơn đã đặt vẫn được lưu). Trên Streamlit Cloud, `users.db` bị xóa mỗi khi app khởi động lại; muốn giữ dữ liệu thì dùng PostgreSQL (mục dưới).

## Lưu dữ liệu bằng PostgreSQL (Supabase)

Mặc định app lưu tài khoản, đơn hàng và combo trong SQLite `users.db`. Khi có mục `[postgres]` trong Secrets (hoặc biến môi trường `DATABASE_URL`), app chuyển sang PostgreSQL, code không cần sửa. Dòng cuối tab **Quản trị → Tài khoản khách hàng** cho biết app đang lưu ở đâu.

1. Tạo project miễn phí trên [supabase.com](https://supabase.com) (đặt mật khẩu database, chọn vùng gần Việt Nam, ví dụ Singapore).
2. Trong project bấm **Connect**, chọn chuỗi kết nối **Session pooler** (dùng được trên mạng IPv4 như Streamlit Cloud), thay `[YOUR-PASSWORD]` bằng mật khẩu database.
3. Khai báo chuỗi đó:
   - Trên máy: chép `.streamlit/secrets.toml.example` thành `.streamlit/secrets.toml` (file này không đưa lên git) và sửa `url`.
   - Trên Streamlit Cloud: trang quản lý app → **Settings → Secrets**, dán mục `[postgres]` (và `[admin]` nếu muốn đổi tài khoản admin).

   ```toml
   [postgres]
   url = "postgresql://postgres.xxxx:MAT_KHAU@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"
   ```
4. Chạy app: lần đầu app tự tạo các bảng và tài khoản admin trên PostgreSQL.
5. (Tùy chọn) Chép dữ liệu đang có trong `users.db` sang, chạy một lần trên máy đã khai báo `secrets.toml`:

   ```bash
   venv\Scripts\python migrate_to_postgres.py            # dừng nếu PostgreSQL đã có dữ liệu
   venv\Scripts\python migrate_to_postgres.py --replace  # xóa dữ liệu trên PostgreSQL rồi chép lại
   ```

Lưu ý: project miễn phí của Supabase có thể bị tạm dừng sau một thời gian không dùng, khi đó app báo "Không kết nối được database"; vào trang Supabase bấm khôi phục project rồi tải lại app. Xem dữ liệu trong **Table Editor** của Supabase. Bỏ mục `[postgres]` thì app quay về SQLite.

## Dữ liệu

`data/genz_vn.xlsx` là dữ liệu khảo sát công khai của bài báo trên *Data in Brief* (2023) về hành vi đặt đồ ăn qua ứng dụng của Gen Z Việt Nam: 361 người, không có giá trị thiếu. `segmentation.load_customers` mã hóa như sau:

- **Tuổi** (Q27) và **Thu nhập** (Q29) được hỏi theo nhóm nên lấy giá trị giữa nhóm (16,5 / 20,5 / 24 / 27 tuổi; 5 / 15 / 25 / 35 / 45 triệu đồng/tháng).
- **Thái độ** = trung bình Q19–Q21 (Cronbach alpha 0,80), **Ý định đặt tiếp** = trung bình Q22–Q25 (alpha 0,84), thang 1–7.
- **Giới tính** (Q26), **Hôn nhân** (Q30), **Học vấn** (Q28) giữ dạng phân loại.

K = 3 được chọn trong `thu_nghiem_vn/` (Elbow không có điểm gãy rõ; K = 3 tốt hơn hoặc ngang K = 4 ở Silhouette, Davies–Bouldin, Calinski–Harabasz và ổn định hơn rõ rệt). Ba cụm: **Sinh viên thu nhập thấp** (132 người), **Người đi làm thu nhập khá** (155), **Khách trung thành** (74).

## Dữ liệu mẫu để thử

Mỗi dòng dưới đây được xếp vào một cụm khác nhau (tab Quản trị → Tạo thử khách mới):

| Tuổi | Thu nhập | Thái độ | Ý định đặt tiếp | Giới tính | Hôn nhân | Học vấn | Cụm |
|---|---|---|---|---|---|---|---|
| 20 | Dưới 10 triệu | 4,25 | 4,5 | Nữ | Độc thân | Cao đẳng | Sinh viên thu nhập thấp |
| 27 | 20–30 triệu | 4,0 | 4,25 | Nữ | Đã kết hôn | Đại học | Người đi làm thu nhập khá |
| 24 | 10–20 triệu | 5,75 | 6,0 | Nam | Độc thân | Đại học | Khách trung thành |

## Chạy notebook (không bắt buộc)

Notebook dùng thêm một số thư viện không có trong `requirements.txt`:

```bash
pip install jupyter matplotlib gower
```

## So sánh thuật toán phân cụm

```bash
venv\Scripts\python compare_clustering.py
```

Chạy 4 thuật toán với K = 2…8 trên dataset 361 người (vài giây), ghi chỉ số vào `so_sanh_chi_so.csv` và vẽ:

1. Silhouette (Gower), Davies–Bouldin, Calinski–Harabasz theo K
2. Các chỉ số và thời gian chạy tại K = 3
3. Hình chiếu FAMD 2 chiều, tô màu theo cụm
4. Biểu đồ silhouette từng điểm
5. Heatmap ARI giữa các thuật toán
6. Bảng chéo nhãn cụm K-Prototypes × từng thuật toán
7. Kích thước các cụm
8. Tâm cụm theo thu nhập và ý định đặt tiếp
9. Cây phân cấp (dendrogram)
