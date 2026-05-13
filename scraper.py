from playwright.sync_api import sync_playwright
import pandas as pd
import re

URL = "https://www.fashionphile.com/collections/all-bags"
MAX_PRODUCTS = 70

SCROLL_TIMES = 3
SCROLL_AMOUNT = 6000
SCROLL_WAIT_MS = 500

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
    text_upper = str(text).upper()

    for brand in BRANDS:
        if brand in text_upper:
            return brand.title()

    return "Unknown"


def clean_name(text):
    text = re.sub(r"\$\s*[\d,]+", "", str(text))
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_image_url(image):
    if not image:
        return ""

    image = str(image).strip()

    if "," in image and " " in image:
        image = image.split(",")[0].split(" ")[0]

    if image.startswith("//"):
        image = "https:" + image

    return image


def scrape_fashionphile():
    products = []
    seen_links = set()
    browser = None

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--disable-default-apps",
                    "--disable-features=Translate,BackForwardCache",
                    "--blink-settings=imagesEnabled=true"
                ]
            )

            page = browser.new_page(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=90000
            )

            page.wait_for_timeout(6000)

            for _ in range(SCROLL_TIMES):
                page.mouse.wheel(0, SCROLL_AMOUNT)
                page.wait_for_timeout(SCROLL_WAIT_MS)

            links = page.locator("a[href*='/products/']")
            count = links.count()

            print("找到商品連結數:", count)

            for i in range(count):
                if len(products) >= MAX_PRODUCTS:
                    break

                try:
                    link = links.nth(i)

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
                    prices = [p for p in prices if p and p > 100]

                    if not prices:
                        continue

                    price = min(prices)

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
                        image = normalize_image_url(image)

                    except Exception:
                        image = ""

                    products.append({
                        "brand": brand,
                        "name": name,
                        "price": price,
                        "image": image,
                        "link": href
                    })

                    print("成功:", brand, name, price)

                except Exception as e:
                    print("跳過商品:", e)
                    continue

        finally:
            if browser:
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