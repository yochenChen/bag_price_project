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
MAX_PRODUCTS = 100000000
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


def extract_brand(text):
    text_upper = text.upper()

    for brand in BRANDS:
        if brand in text_upper:
            return brand.title()

    return "Unknown"


def clean_name(text):
    text = re.sub(r"\$\s*[\d,]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def scrape_fashionphile():
    driver = get_driver()
    driver.get(URL)
    time.sleep(8)

    for i in range(8):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")

    products = []
    seen_links = set()

    for link in product_links:
        try:
            href = link.get_attribute("href")

            if not href or href in seen_links:
                continue

            seen_links.add(href)

            card = link.find_element(
                By.XPATH,
                "./ancestor::*[self::div or self::li or self::article][.//img][1]"
            )

            card_text = card.text.strip()

            if "$" not in card_text:
                continue

            price_matches = re.findall(r"\$\s*[\d,]+", card_text)

            if not price_matches:
                continue

            price = clean_price(price_matches[-1])

            if not price or price <= 100:
                continue

            raw_name = clean_name(card_text)
            lines = [x.strip() for x in raw_name.split("\n") if x.strip()]

            if len(lines) >= 2:
                name = " ".join(lines)
            else:
                name = raw_name

            brand = extract_brand(name)

            if brand == "Unknown":
                continue

            image = ""

            try:
                img = card.find_element(By.CSS_SELECTOR, "img")
                image = (
                    img.get_attribute("src")
                    or img.get_attribute("data-src")
                    or img.get_attribute("srcset")
                    or ""
                )

                if "," in image and " " in image:
                    image = image.split(",")[0].split(" ")[0]

            except:
                image = ""

            products.append({
                "brand": brand,
                "name": name,
                "price": price,
                "image": image,
                "link": href
            })

            if len(products) >= MAX_PRODUCTS:
                break

        except Exception as e:
            continue

    driver.quit()

    print("成功抓到商品數:", len(products))

    return products


def analyze(products):
    df = pd.DataFrame(products)

    if df.empty:
        return []

    summary = (
        df.groupby(["brand", "name"])
        .agg(
            average_price=("price", "mean"),
            lowest_price=("price", "min"),
            highest_price=("price", "max"),
            product_count=("price", "count"),
            image=("image", "first"),
            link=("link", "first"),
            product_price=("price", "first")
        )
        .reset_index()
    )

    summary["average_price"] = summary["average_price"].round(0).astype(int)

    summary = summary.sort_values(
        by=["brand", "name"],
        ascending=[True, True]
    )

    return summary.to_dict(orient="records")


@app.route("/")
def home():
    products = scrape_fashionphile()
    rows = analyze(products)

    return render_template("index.html", rows=rows)


if __name__ == "__main__":
    app.run(debug=True)