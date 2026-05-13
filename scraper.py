import csv
import time
import requests

BASE_URL = "https://www.fashionphile.com"
COLLECTION_HANDLE = "all-bags"
CSV_FILE = "products.csv"

MAX_PRODUCTS = 1000
MAX_WORKERS = 2
REQUEST_TIMEOUT = 10
SLEEP_SECONDS = 1
SAVE_EVERY_ROW = True
DOWNLOAD_IMAGES = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def clean_price(value):
    if value is None:
        return None

    try:
        return int(float(value))
    except:
        return None


def get_product_page_url(product):
    handle = product.get("handle", "")

    if handle:
        return f"{BASE_URL}/products/{handle}"

    return ""


def get_image_url(product):
    images = product.get("images", [])

    if images and isinstance(images, list):
        return images[0].get("src", "")

    image = product.get("image")

    if isinstance(image, dict):
        return image.get("src", "")

    return ""


def get_price(product):
    variants = product.get("variants", [])

    prices = []

    for variant in variants:
        price = clean_price(variant.get("price"))

        if price:
            prices.append(price)

    if prices:
        return min(prices)

    return None


def fetch_collection_page(session, page):
    url = (
        f"{BASE_URL}/collections/"
        f"{COLLECTION_HANDLE}/products.json"
        f"?limit=250&page={page}"
    )

    response = session.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    return data.get("products", [])


def product_to_row(product):
    brand = product.get("vendor", "").strip()
    name = product.get("title", "").strip()
    image = get_image_url(product)
    url = get_product_page_url(product)
    price = get_price(product)

    if not brand or not name or not price or not url:
        return None

    return {
        "brand": brand,
        "name": name,
        "image": image,
        "url": url,
        "price": price
    }


def scrape_fashionphile():
    products = []
    seen_urls = set()

    with requests.Session() as session:

        page = 1

        while len(products) < MAX_PRODUCTS:

            try:
                product_list = fetch_collection_page(session, page)
            except Exception as e:
                print("抓取失敗:", e)
                break

            if not product_list:
                break

            for product in product_list:

                row = product_to_row(product)

                if not row:
                    continue

                if row["url"] in seen_urls:
                    continue

                seen_urls.add(row["url"])
                products.append(row)

                if len(products) >= MAX_PRODUCTS:
                    break

            page += 1
            time.sleep(SLEEP_SECONDS)

    return products


def save_to_csv(products):
    fieldnames = ["brand", "name", "image", "url", "price"]

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for product in products:
            writer.writerow(product)


def refresh_csv():
    products = scrape_fashionphile()
    save_to_csv(products)
    return products


if __name__ == "__main__":
    products = refresh_csv()
    print(f"已更新 {CSV_FILE}，共 {len(products)} 筆")