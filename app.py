from flask import Flask, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd
import time
import re

app = Flask(__name__)

URL = "https://www.fashionphile.com/collections/all-bags"
MAX_PRODUCTS = 30

BRANDS = [
    "CHANEL", "HERMES", "LOUIS VUITTON", "GUCCI", "PRADA",
    "FENDI", "CELINE", "DIOR", "CHRISTIAN DIOR",
    "SAINT LAURENT", "YSL", "BOTTEGA VENETA",
    "BALENCIAGA", "GOYARD", "MIU MIU", "BURBERRY",
    "VALENTINO", "LOEWE", "CARTIER", "ROLEX",
    "CHLOE", "JACQUEMUS"
]


def clean_price(text):
    if not text:
        return None

    match = re.search(r"\$\s*([\d,]+)", str(text))

    if match:
        return int(match.group(1).replace(",", ""))

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


def get_product_links(driver):
    driver.get(URL)
    time.sleep(8)

    for i in range(6):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")

    product_links = []

    for link in links:
        href = link.get_attribute("href")

        if href and "/products/" in href and href not in product_links:
            product_links.append(href)

    return product_links[:MAX_PRODUCTS]


def get_title(driver):
    try:
        return driver.find_element(By.TAG_NAME, "h1").text.strip()
    except:
        return driver.title.strip()


def get_image(driver):
    selectors = [
        "meta[property='og:image']",
        "img[src*='cdn.shopify']",
        "img"
    ]

    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)

            if selector.startswith("meta"):
                image = element.get_attribute("content")
            else:
                image = element.get_attribute("src")

            if image:
                return image
        except:
            pass

    return ""


def get_price(driver):
    time.sleep(2)

    price_selectors = [
        "[data-cy*='price']",
        "[data-testid*='price']",
        "[class*='price']",
        "[class*='Price']",
        "span",
        "div"
    ]

    for selector in price_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)

            for element in elements:
                text = element.text.strip()

                if "$" not in text:
                    continue

                price = clean_price(text)

                if price and price > 100:
                    return price
        except:
            pass

    page_text = driver.find_element(By.TAG_NAME, "body").text
    prices = re.findall(r"\$\s*[\d,]+", page_text)

    valid_prices = []

    for p in prices:
        price = clean_price(p)

        if price and price > 100:
            valid_prices.append(price)

    if valid_prices:
        return max(valid_prices)

    return None


def scrape_fashionphile():
    driver = get_driver()

    product_links = get_product_links(driver)

    print("準備爬商品數:", len(product_links))

    products = []

    for index, link in enumerate(product_links, start=1):

        try:
            print(f"正在爬第 {index} 個商品:", link)

            driver.get(link)
            time.sleep(5)

            title = get_title(driver)
            image = get_image(driver)
            price = get_price(driver)

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

            print("成功:", brand, title, price)

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
    rows = analyze(products)

    return render_template(
        "index.html",
        rows=rows
    )


if __name__ == "__main__":
    app.run(debug=True)