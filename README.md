# **Project 02: Tiki Product Scraper**

## **Chức Năng Chính**

1. **Thu Thập Dữ Liệu Sản Phẩm**:
    - Mỗi sản phẩm được truy xuất qua API với `product_id`, và các thông tin như tên, giá, mô tả, và hình ảnh được thu thập.
    - Dữ liệu thu thập được được lưu dưới dạng file JSON.
2. **Quản Lý Rate Limit và Lỗi**:
    - Hệ thống tự động xử lý **Rate Limit** từ API và có cơ chế retry để tiếp tục thu thập dữ liệu nếu gặp lỗi mạng hoặc lỗi API.
    - Tất cả các lỗi từ API đều được ghi lại, và các sản phẩm bị lỗi sẽ được lưu riêng biệt để người dùng có thể xử lý sau.
3. **Checkpoint và Tiếp Tục Sau Khi Bị Crash**:
    - Hệ thống hỗ trợ **checkpointing**, cho phép lưu lại danh sách các `product_id` đã được xử lý thành công. Điều này giúp tiếp tục thu thập từ điểm bị gián đoạn mà không phải bắt đầu lại từ đầu khi bị crash hoặc dừng đột ngột.
4. **Chạy Theo Batch**:
    - Quá trình thu thập dữ liệu được chia thành nhiều **batch** (lô sản phẩm) để tránh quá tải yêu cầu và giúp quản lý việc gửi yêu cầu API hiệu quả.
---

## **1. Thông tin dự án**

- **Tên dự án:** Project 02 - Tiki Product Scraper
- **Ngày bắt đầu:** 03/02/2025
- **Ngày hoàn thành:** 06/02/2025
- **Công cụ sử dụng:** Google Cloud Platform (GCP), Python, gcloud CLI, aiohttp, pandas, openpyxl, aiofiles, tqdm

---

## **2. Mục tiêu**

Dự án này nhằm mục đích tải thông tin chi tiết của **200,000 sản phẩm** từ trang thương mại điện tử Tiki và lưu trữ dữ liệu dưới dạng các file JSON. Mỗi file JSON sẽ chứa thông tin của khoảng **1,000 sản phẩm** để dễ dàng quản lý.

---

## **3. Yêu cầu chính**

### **3.1. Tải danh sách sản phẩm**

- Sử dụng danh sách `product_id` được cung cấp tại đường dẫn: [Danh sách sản phẩm](https://1drv.ms/u/s!AukvlU4z92FZgp4xIlzQ4giHVa5Lpw?e=qDXctn).
- Danh sách này chứa các ID của sản phẩm cần lấy thông tin.

### **3.2. Lấy thông tin chi tiết sản phẩm**

- Sử dụng API của Tiki để lấy thông tin sản phẩm:
    
    ```
    https://api.tiki.vn/product-detail/api/v1/products/{product_id}
    ```
    
- Các thông tin cần lấy:
    - `id`: ID của sản phẩm.
    - `name`: Tên sản phẩm.
    - `url_key`: URL key của sản phẩm.
    - `price`: Giá sản phẩm.
    - `description`: Mô tả sản phẩm (cần được chuẩn hóa).
    - `images_url`: Danh sách URL hình ảnh sản phẩm.

### **3.3. Chuẩn hóa mô tả sản phẩm**

- Loại bỏ các thẻ HTML, ký tự đặc biệt và khoảng trắng thừa trong trường `description` để đảm bảo dữ liệu sạch.

### **3.4. Lưu dữ liệu thành file JSON**

- Mỗi file JSON chứa thông tin của **1,000 sản phẩm**.
- Định dạng tên file: `products_1.json`, `products_2.json`, ...
- Các sản phẩm không thể tải thành công sẽ được lưu vào `errors.json`.

### **3.5. Tối ưu hóa tốc độ lấy dữ liệu**

- Sử dụng **đa luồng (multithreading)** hoặc **đa tiến trình (multiprocessing)** để tăng tốc độ tải dữ liệu.
- Dùng **asyncio** và **aiohttp** để gửi nhiều yêu cầu API đồng thời thay vì tuần tự.
- Hạn chế số lượng request đồng thời bằng **semaphore** để tránh bị giới hạn.

---

## **4. Quy trình thực hiện**

### **4.1. Kết nối tới VM trên Google Cloud**

```
 gcloud compute ssh hofnam-vm --zone=us-central1-c --ssh-flag="-p 2222"
```

### **4.2. Upload file chứa danh sách ID lên VM**

```
gcloud compute scp products-0-200000.xlsx hofnam-vm:~ --zone=us-central1-c --scp-flag="-P 2222"
```

### **4.3. Tạo môi trường ảo để chạy code trên VM**

```
python3 -m venv myenv
```

### **4.4. Upload file code lên VM**

```
gcloud compute scp code.py hofnam-vm:~ --zone=us-central1-c --scp-flag="-P 2222"
```

### **4.5. Kích hoạt môi trường ảo**

```
source myenv/bin/activate
```

### **4.6. Cài đặt các thư viện cần thiết trên VM**

```
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip git
pip3 install aiohttp pandas openpyxl aiofiles tqdm
```

### **4.7. Chạy chương trình bằng lệnh nohup để chạy nền**

```
nohup python3 code.py > output.log 2>&1 &
```

---

## **5. Mô tả về mã nguồn (code.py)**

Mã nguồn **code.py** sử dụng Python **asyncio** và **aiohttp** để thu thập dữ liệu từ API của Tiki. Dưới đây là các bước chính:

### **5.1. Cấu hình API và batch size**

- Sử dụng API của Tiki để lấy dữ liệu sản phẩm.
- Cấu hình mỗi file JSON chứa 1,000 sản phẩm.

### **5.2. Xử lý mô tả sản phẩm**

- Sử dụng regex để loại bỏ thẻ HTML và khoảng trắng thừa.

### **5.3. Hàm lấy dữ liệu sản phẩm (`fetch_product`)**

- Gửi yêu cầu đến API để lấy dữ liệu sản phẩm.
- Nếu gặp lỗi 429 (rate limit), chương trình sẽ đợi một thời gian trước khi thử lại.
- Nếu lỗi vượt quá số lần thử cho phép, sản phẩm sẽ được đánh dấu là lỗi.

### **5.4. Hàm lấy dữ liệu nhiều sản phẩm cùng lúc (`fetch_all_products`)**

- Sử dụng **asyncio.Semaphore(100)** để giới hạn số lượng request đồng thời.
- Sử dụng `asyncio.gather()` để chạy nhiều request cùng lúc.
- Phân loại sản phẩm thành danh sách thành công và thất bại.

### **5.5. Hàm lưu dữ liệu vào JSON**

- Dữ liệu sau khi thu thập sẽ được lưu vào file JSON theo từng batch.
- Sản phẩm có lỗi sẽ được lưu riêng vào `errors.json`.

### **5.6. Hàm chính (`main`)**

1. Đọc danh sách `product_id` từ file Excel.
2. Chia danh sách thành các batch nhỏ (1,000 sản phẩm/batch).
3. Gửi yêu cầu lấy dữ liệu theo từng batch.
4. Lưu dữ liệu vào các file JSON.
5. Ghi log lỗi nếu có sản phẩm không tải được.

### **5.7. Chạy chương trình**

- Sử dụng `asyncio.run(main())` để thực thi chương trình.
- `nest_asyncio.apply()` được sử dụng để hỗ trợ môi trường tương tác.

---
## **Hướng Dẫn Sử Dụng**

1. **Chuẩn Bị Dữ Liệu Đầu Vào**:
    - Tạo một tệp Excel có tên `products-0-200000.xlsx` chứa danh sách các `product_id`. Đây là đầu vào cho chương trình.
2. **Chạy Chương Trình**:
    - Để bắt đầu quá trình thu thập dữ liệu, bạn có thể chạy tệp `main.py`:
3. **Xem Kết Quả**:
    - Các sản phẩm hợp lệ sẽ được lưu vào các tệp JSON, mỗi tệp tương ứng với một batch sản phẩm.
    - Các sản phẩm bị lỗi sẽ được lưu vào các tệp JSON khác với tên tương ứng, ví dụ: `errors_1.json`.
4. **Tiếp Tục Sau Khi Bị Crash**:
    - Nếu chương trình bị gián đoạn giữa chừng (do crash, timeout, v.v.), các `product_id` đã được xử lý thành công sẽ được lưu lại trong tệp `checkpoint.json`.
    - Khi chạy lại chương trình, nó sẽ kiểm tra và tiếp tục từ điểm dừng của lần chạy trước mà không cần xử lý lại các sản phẩm đã hoàn thành.

## **6. Kết luận**

Dự án này giúp tự động hóa việc thu thập dữ liệu sản phẩm từ Tiki một cách nhanh chóng và hiệu quả. Với việc sử dụng **asyncio**, **aiohttp**, và **gcloud**, chương trình có thể:

- **Tải dữ liệu đồng thời** từ API để giảm thời gian chạy.
- **Xử lý lỗi linh hoạt**, tránh bị chặn bởi rate limit.
- **Lưu dữ liệu có cấu trúc** giúp dễ dàng phân tích sau này.

Việc triển khai trên Google Cloud VM đảm bảo quá trình chạy không bị gián đoạn và có thể xử lý khối lượng lớn dữ liệu mà không ảnh hưởng đến máy tính cá nhân.
