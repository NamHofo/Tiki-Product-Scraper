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
from typing import List, Dict, Tuple, Any
from config import API_URL, BATCH_SIZE


# Chuẩn hóa nội dung description (loại bỏ HTML)
def clean_description(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)  # Xoá thẻ HTML
    text = re.sub(r'\s+', ' ', text).strip()  # Xóa khoảng trắng thừa
    return text

async def fetch_product(session: aiohttp.ClientSession, product_id: str, max_retries: int = 5) -> Dict[str, Any]:
    url: str = API_URL.format(product_id)
    retries: int = 0
    backoff_factor: int = 1
    while retries < max_retries:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    logging.info(f"Product ID: {product_id} successed!")
                    data: Dict[str, Any] = await response.json()
                    return {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "url_key": data.get("url_key"),
                        "price": data.get("price"),
                        "description": clean_description(data.get("description")),
                        "images_url": [img.get("base_url") for img in data.get("images", []) if "base_url" in img]
                    }
                elif response.status == 429:
                    retry_after: int = int(response.headers.get('Retry-After', random.randint(3, 10)))
                    logging.info(f"Product ID: {product_id} \n Error: {response.status}")
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
            logging.info(f"Product ID: {product_id}")
            logging.info(f"Unexpected error: {e}. Retrying...")
            retries += 1
            await asyncio.sleep(backoff_factor * (2 ** retries))
    return {"id": product_id, "error": "Max retries exceeded"}

# Hàm xử lý lấy dữ liệu theo batch
async def fetch_all_products(product_ids: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    tasks: List[asyncio.Task] = []
    semaphore: asyncio.Semaphore = asyncio.Semaphore(150)
    headers: Dict[str, str] = {'User-Agent': 'Trình thu thập dữ liệu Tiki của tôi'}
    async with aiohttp.ClientSession(headers=headers) as session:
        async def bound_fetch(product_id: str) -> Dict[str, Any]:
            async with semaphore:  # Hạn chế số lượng request đồng thời
                return await fetch_product(session, product_id)

        tasks = [bound_fetch(p_id) for p_id in product_ids]
        results: List[Dict[str, Any]] = await asyncio.gather(*tasks)

    # Lọc sản phẩm hợp lệ và sản phẩm có lỗi
    successful_products: List[Dict[str, Any]] = []  # Danh sách các sản phẩm thành công
    failed_products: List[Dict[str, Any]] = []  # Danh sách các sản phẩm lỗi
    for result in results:
        if isinstance(result, dict) and 'error' in result:  # Nếu có lỗi
            failed_products.append(result)  # Lưu sản phẩm có lỗi và lý do
        else:
            successful_products.append(result)  # Lưu sản phẩm hợp lệ

    return successful_products, failed_products

# Hàm chia nhỏ danh sách thành từng batch
def split_list(lst: List[Any], batch_size: int) -> List[List[Any]]:
    for i in range(0, len(lst), batch_size):
        yield lst[i:i + batch_size]

# Hàm lưu dữ liệu vào file JSON
async def save_to_json(data: List[Dict[str, Any]], file_index: str, error: bool = False) -> None:
    filename: str = f"products_{file_index}.json"
    try:
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=4, ensure_ascii=False))
        logging.info(f"Saved to: {filename}")
    except Exception as e:
        logging.error(f"Failed to save to {filename}: {e}")

# Tạo checkpoint để lưu các product_id đã duyệt qua phòng khi crash
async def save_checkpoint(state: Dict[str, Any]) -> None:
    try:
        temp_filename = "checkpoint_temp.json"
        final_filename = "checkpoint.json"
        async with aiofiles.open(temp_filename, "w", encoding="utf-8") as f:
            await f.write(json.dumps(state, indent=4, ensure_ascii=False))
        os.replace(temp_filename, final_filename)
        logging.info(f"Checkpoint saved")
    except Exception as e:
        logging.error(f"Failed to save checkpoint: {e}")

async def load_checkpoint() -> Dict[str, Any]:
    if os.path.exists("checkpoint.json"):
        try:
            async with aiofiles.open("checkpoint.json", "r", encoding="utf-8") as f:
                data = await f.read()
                return json.loads(data)
        except Exception as e:
            logging.error(f"Failed to load checkpoint: {e}")
    return {"processed_ids": []}

# Chạy toàn bộ quy trình
async def main() -> None:
    # 1. Đọc danh sách product_id từ file Excel
    df: pd.DataFrame = pd.read_excel("products-0-200000.xlsx", engine="openpyxl")
    
    # 2. Lấy cột chứa product_id
    product_ids: List[str] = df.iloc[:, 0].astype(str).tolist()

    # Kiểm tra danh sách rỗng
    if not product_ids:
        logging.info("No products found in the Excel file.")
        return

    # Lấy 200000 sản phẩm để bắt đầu cào
    product_ids = product_ids[:100]

    # 2.1. Kiểm tra checkpoint (nếu có)
    checkpoint: Dict[str, Any] = await load_checkpoint()
    processed_ids: List[str] = checkpoint.get("processed_ids", [])

    logging.info(f"Total products (for testing): {len(product_ids)}")

    # 4. Chia thành từng batch
    batches: List[List[str]] = list(split_list(product_ids, BATCH_SIZE))

    all_failed_products: List[Dict[str, Any]] = []  # Danh sách lỗi tổng

    # 5. Tải dữ liệu theo batch
    for index, batch in enumerate(tqdm(batches, desc="Fetching data")):
        product_data, failed_products = await fetch_all_products(batch)

        # Lưu các sản phẩm hợp lệ
        if product_data:
            await save_to_json(product_data, f"{index+1}")
            processed_ids.extend([data['id'] for data in product_data])
            
        # Lưu sản phẩm lỗi
        all_failed_products.extend(failed_products)

        # Lưu checkpoint
        state = {"processed_ids": processed_ids}
        await save_checkpoint(state)
# Tạo thư mục logs nếu chưa có
os.makedirs("logs", exist_ok=True)

# Cấu hình logging
log_file: str = "logs/output.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,  # Ghi từ INFO trở lên
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Ghi log
logging.info("Start")
try:
    nest_asyncio.apply()  # Apply nest_asyncio to allow nested event loops
    asyncio.run(main())
except ZeroDivisionError as e:
    logging.error(f"Error: {e}")

logging.info("END")