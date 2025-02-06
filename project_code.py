import aiohttp
import aiofiles
import asyncio
import json
import re
from tqdm import tqdm
import pandas as pd
import random
import nest_asyncio
import logging
import os


# API endpoint
API_URL = "https://api.tiki.vn/product-detail/api/v1/products/{}"

# Số lượng sản phẩm mỗi file
BATCH_SIZE = 1000

# Chuẩn hóa nội dung description (loại bỏ HTML)
def clean_description(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)  # Xoá thẻ HTML
    text = re.sub(r'\s+', ' ', text).strip()  # Xóa khoảng trắng thừa
    return text

async def fetch_product(session, product_id, max_retries=5):
    url = API_URL.format(product_id)
    retries = 0
    backoff_factor = 1
    while retries < max_retries:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "url_key": data.get("url_key"),
                        "price": data.get("price"),
                        "description": clean_description(data.get("description")),
                        "images_url": [img.get("base_url") for img in data.get("images", []) if "base_url" in img]
                    }
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', random.randint(3, 10)))
                    logging.info(f"Product ID: {product_id}")
                    logging.info(f"Rate limit hit. Retrying after {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    retries += 1
                else:
                    logging.info(f"API returned status {response.status} for product_id {product_id}")
                    return {"id": product_id, "error": f"API returned status {response.status}"}
        except aiohttp.ClientError as e:
            logging.info(f"Network error: {e}. Retrying...")
            retries += 1
            await asyncio.sleep(backoff_factor * (2 ** retries))
        except Exception as e:
            logging.info(f"Unexpected error: {e}. Retrying...")
            retries += 1
            await asyncio.sleep(backoff_factor * (2 ** retries))
    return {"id": product_id, "error": "Max retries exceeded"}


# Hàm xử lý lấy dữ liệu theo batch
async def fetch_all_products(product_ids):
    tasks = []
    semaphore = asyncio.Semaphore(150)
    async with aiohttp.ClientSession() as session:
        async def bound_fetch(product_id):
            async with semaphore:  # Hạn chế số lượng request đồng thời
                return await fetch_product(session, product_id)

        tasks = [bound_fetch(p_id) for p_id in product_ids]
        results = await asyncio.gather(*tasks)

    # Lọc sản phẩm hợp lệ và sản phẩm có lỗi
    successful_products = [] #Danh sách các sản phẩm thành công
    failed_products = []  # Danh sách các sản phẩm lỗi
    for result in results:
        if isinstance(result, dict) and 'error' in result:  # Nếu có lỗi
            failed_products.append(result)  # Lưu sản phẩm có lỗi và lý do
        else:
            successful_products.append(result)  # Lưu sản phẩm hợp lệ

    return successful_products, failed_products




# Hàm chia nhỏ danh sách thành từng batch
def split_list(lst, batch_size):
    for i in range(0, len(lst), batch_size):
        yield lst[i:i + batch_size]

# Hàm lưu dữ liệu vào file JSON
async def save_to_json(data, file_index):
    filename = f"products_{file_index}.json"
    async with aiofiles.open(filename, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=4, ensure_ascii=False))
    logging.info(f"Saved to: {filename}")

# Chạy toàn bộ quy trình
async def main():
    # 1. Đọc danh sách product_id từ file Excel
    df = pd.read_excel("products-0-200000.xlsx", engine="openpyxl")

    # 2. Lấy cột chứa product_id
    product_ids = df.iloc[:, 0].astype(str).tolist()

    #Lấy 200000 sản phẩm để bắt đầu cào
    product_ids = product_ids[:100]

    logging.info(f"Total products (for testing): {len(product_ids)}")

    # 4. Chia thành từng batch
    batches = list(split_list(product_ids, BATCH_SIZE))

    all_failed_products = []  # Danh sách lỗi tổng

    # 5. Tải dữ liệu theo batch
    for index, batch in enumerate(tqdm(batches, desc="Fetching data")):
        product_data, failed_products = await fetch_all_products(batch)

        # Lưu các sản phẩm hợp lệ
        if product_data:
            await save_to_json(product_data, f"{index+1}")

        # Lưu sản phẩm lỗi
        all_failed_products.extend(failed_products)

    # 6. Lưu danh sách lỗi vào file riêng nếu có lỗi
    if all_failed_products:
        await save_to_json(all_failed_products, "errors")
        logging.info(f"⚠️ Save errors to errors.json")



# Tạo thư mục logs nếu chưa có
os.makedirs("logs", exist_ok=True)

# Cấu hình logging
log_file = "logs/output.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,  # Ghi từ INFO trở lên
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Ghi log
logging.info("Start")
try:
   nest_asyncio.apply() # Apply nest_asyncio to allow nested event loops
   asyncio.run(main())
except ZeroDivisionError as e:
    logging.error(f"Error: {e}")

logging.info("END")



