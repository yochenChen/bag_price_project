from flask import Flask, render_template, redirect, url_for
import pandas as pd
import os

from scraper import scrape_fashionphile

app = Flask(__name__)

CSV_FILE = "products.csv"


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
            link=("link", "first")
        )
        .reset_index()
    )

    summary["average_price"] = (
        summary["average_price"]
        .round(0)
        .astype(int)
    )

    summary["lowest_price"] = (
        summary["lowest_price"]
        .astype(int)
    )

    summary["highest_price"] = (
        summary["highest_price"]
        .astype(int)
    )

    summary = summary.sort_values(
        by=["brand", "name"],
        ascending=[True, True]
    )

    return summary.to_dict(orient="records")


@app.route("/")
def home():

    # 如果沒有 CSV 就自動爬一次
    if not os.path.exists(CSV_FILE):

        products = scrape_fashionphile()

        pd.DataFrame(products).to_csv(
            CSV_FILE,
            index=False,
            encoding="utf-8-sig"
        )

    df = pd.read_csv(CSV_FILE)

    products = df.to_dict(orient="records")

    rows = analyze(products)

    return render_template(
        "index.html",
        rows=rows
    )


@app.route("/refresh")
def refresh():

    print("開始重新爬蟲...")

    products = scrape_fashionphile()

    df = pd.DataFrame(products)

    # 覆蓋舊 CSV
    df.to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("CSV 已更新")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)