from playwright.sync_api import sync_playwright
import pandas as pd
import re

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


def scrape_fashionphile():
    products = []
    seen_links = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(

            headless=True,

            args=[

                "--no-sandbox",

                "--disable-setuid-sandbox",

                "--disable-dev-shm-usage",

                "--disable-gpu",

                "--single-process"

            ]

        )

        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        page.wait_for_timeout(10000)

        for i in range(10):
            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(2000)

        links = page.locator("a[href*='/products/']")
        count = links.count()

        print("找到商品連結數:", count)

        for i in range(count):
            try:
                link = links.nth(i)

                # 跳過隱藏的 menu link
                if not link.is_visible():
                    continue

                href = link.get_attribute("href")

                if not href:
                    continue

                if href.startswith("/"):
                    href = "https://www.fashionphile.com" + href

                if href in seen_links:
                    continue

                seen_links.add(href)

                card = link.locator(
                    "xpath=ancestor::*[self::div or self::li or self::article][.//img][1]"
                )

                if card.count() == 0:
                    continue

                card_text = card.inner_text().strip()

                if "$" not in card_text:
                    continue

                price_matches = re.findall(r"\$\s*[\d,]+", card_text)

                if not price_matches:
                    continue

                prices = [clean_price(p) for p in price_matches]
                prices = [p for p in prices if p]

                if not prices:
                    continue

                price = min(prices)

                if price <= 100:
                    continue

                raw_name = clean_name(card_text)
                lines = [x.strip() for x in raw_name.split("\n") if x.strip()]
                name = " ".join(lines)

                brand = extract_brand(name)

                if brand == "Unknown":
                    continue

                image = ""

                try:
                    img = card.locator("img").first
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

                print("成功:", brand, name, price)

                if len(products) >= MAX_PRODUCTS:
                    break

            except Exception as e:
                print("跳過商品:", e)
                continue

        browser.close()

    print("總共抓到商品數:", len(products))

    return products


if __name__ == "__main__":
    products = scrape_fashionphile()

    df = pd.DataFrame(products)

    df.to_csv(
        "products.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("已產生 products.csv")