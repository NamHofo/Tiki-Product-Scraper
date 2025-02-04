## 1. Giới thiệu

Dự án này tập trung vào việc xử lý dữ liệu sản phẩm và triển khai môi trường tính toán trên Google Cloud Platform (GCP). Mục tiêu chính là thu thập, xử lý và phân tích dữ liệu nhằm hỗ trợ các quyết định kinh doanh.

## 2. Các công việc đã thực hiện

### 2.1. Chuẩn bị dữ liệu

- Thu thập dữ liệu sản phẩm từ nguồn web scraping.
- Lưu trữ dữ liệu ở các định dạng khác nhau như `.xlsx`, `.json`.
- Kiểm tra và làm sạch dữ liệu trước khi xử lý.

### 2.2. Thiết lập môi trường trên GCP

- Tạo máy ảo trên Google Compute Engine với tên `hofnam-vm`.
- Cấu hình firewall để mở cổng 22 và 2222 cho SSH.
- Kiểm tra trạng thái VM, thiết lập SSH key và xác thực kết nối.

### 2.3. Chuyển dữ liệu lên GCP

- Sử dụng `gcloud compute scp` để chuyển tệp dữ liệu lên máy ảo GCP.
- Gặp lỗi liên quan đến kết nối SSH qua cổng 2222 và đã khắc phục bằng cách mở cổng trong firewall.

### 2.4. Cấu hình môi trường Python

- Cài đặt Python và các thư viện cần thiết (`aiohttp`, `pandas`, `openpyxl`, `aiofiles`, `tqdm`).
- Xử lý lỗi liên quan đến môi trường quản lý gói trên Linux.
- Tạo và sử dụng virtual environment (`venv`) để quản lý gói Python độc lập.

### 2.5. Chạy script trên nền background

- Sử dụng lệnh `nohup python3 code.py > output.log 2>&1 &` để chạy script mà không bị gián đoạn khi thoát phiên SSH.
- Kiểm tra tiến trình bằng `ps aux | grep python`.

## 3. Kết quả đạt được

- Đã thiết lập thành công môi trường làm việc trên GCP.
- Chuyển dữ liệu lên máy ảo GCP để xử lý.
- Chạy các script Python để xử lý dữ liệu một cách tự động.

## 4. Hướng phát triển tiếp theo

- Tối ưu hóa quá trình xử lý dữ liệu.
- Tạo pipeline tự động hóa việc thu thập và xử lý dữ liệu.
- Kết hợp thêm các công cụ phân tích dữ liệu để đưa ra insight có giá trị.
