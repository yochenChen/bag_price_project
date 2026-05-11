from flask import Flask, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

import pandas as pd
import time
import re
import json

app = Flask(__name__)

URL = "https://www.fashionphile.com/collections/all-bags"
MAX_PRODUCTS = 30

BRANDS = [
    "CHANEL", "HERMES", "LOUIS VUITTON", "GUCCI", "PRADA",
    "FENDI", "CELINE", "DIOR", "CHRISTIAN DIOR",
    "SAINT LAURENT", "YSL", "BOTTEGA VENETA",
    "BALENCIAGA", "GOYARD", "MIU MIU", "BURBERRY",
    "VALENTINO", "LOEWE", "CARTIER", "ROLEX"
]


def clean_price(text):
    if not text:
        return None

    text = str(text).replace(",", "")
    match = re.search(r"(\d+(\.\d+)?)", text)

    if match:
        return int(float(match.group(1)))

    return None


def extract_brand(title):
    upper_title = title.upper()

    for brand in BRANDS:
        if brand in upper_title:
            return brand.title()

    return "Unknown"


def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    return driver


def extract_product_data(soup):
    title = "Unknown"
    price = None
    image = ""

    # 1. 優先抓 JSON-LD，這通常是最準的商品資料
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            data = json.loads(script.string)

            if isinstance(data, list):
                data_list = data
            else:
                data_list = [data]

            for item in data_list:
                if item.get("@type") == "Product":
                    title = item.get("name", title)

                    img = item.get("image")
                    if isinstance(img, list) and len(img) > 0:
                        image = img[0]
                    elif isinstance(img, str):
                        image = img

                    offers = item.get("offers")
                    if isinstance(offers, dict):
                        price = clean_price(offers.get("price"))

                    if title != "Unknown" and price:
                        return title, price, image

        except:
            pass

    # 2. 備用：抓 h1
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # 3. 備用：抓 og:title
    if title == "Unknown":
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            title = meta_title.get("content").strip()

    # 4. 備用：抓 og:image
    meta_image = soup.find("meta", property="og:image")
    if meta_image and meta_image.get("content"):
        image = meta_image.get("content")

    # 5. 備用：只抓看起來像價格的 meta
    meta_price = soup.find("meta", property="product:price:amount")
    if meta_price and meta_price.get("content"):
        price = clean_price(meta_price.get("content"))

    return title, price, image


def scrape_fashionphile():
    driver = get_driver()

    driver.get(URL)
    time.sleep(8)

    for i in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")

    product_links = []

    for link in links:
        href = link.get_attribute("href")

        if href and "/products/" in href and href not in product_links:
            product_links.append(href)

    product_links = product_links[:MAX_PRODUCTS]

    print("準備爬商品數:", len(product_links))

    products = []

    for index, link in enumerate(product_links, start=1):
        try:
            print(f"正在爬第 {index} 個商品:", link)

            driver.get(link)
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            title, price, image = extract_product_data(soup)

            if not price:
                print("沒有抓到價格，跳過:", link)
                continue

            brand = extract_brand(title)

            products.append({
                "brand": brand,
                "name": title,
                "price": price,
                "image": image,
                "link": link
            })

        except Exception as e:
            print("商品爬取失敗:", e)

    driver.quit()

    print("成功抓到商品數:", len(products))

    return products


def analyze(products):
    df = pd.DataFrame(products)

    if df.empty:
        return []

    summary = (
        df.groupby("brand")["price"]
        .agg(
            average_price="mean",
            lowest_price="min",
            highest_price="max",
            product_count="count"
        )
        .reset_index()
    )

    summary["average_price"] = summary["average_price"].round(0).astype(int)

    final_df = df.merge(summary, on="brand", how="left")

    final_df = final_df[
        [
            "brand",
            "average_price",
            "lowest_price",
            "highest_price",
            "product_count",
            "name",
            "image",
            "link",
            "price"
        ]
    ]

    final_df = final_df.sort_values(
        by=["brand", "price"],
        ascending=[True, True]
    )

    return final_df.to_dict(orient="records")


@app.route("/")
def home():
    products = scrape_fashionphile()
    table_data = analyze(products)

    return render_template(
        "index.html",
        rows=table_data
    )


if __name__ == "__main__":
    app.run(debug=True)