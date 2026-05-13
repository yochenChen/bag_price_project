from flask import Flask, render_template, redirect, url_for
import pandas as pd

from scraper import scrape_fashionphile

app = Flask(__name__)


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

    return summary.to_dict(orient="records")


cached_rows = []


@app.route("/")
def home():

    global cached_rows

    if not cached_rows:

        products = scrape_fashionphile()

        cached_rows = analyze(products)

    return render_template(
        "index.html",
        rows=cached_rows
    )


@app.route("/refresh")
def refresh():

    global cached_rows

    products = scrape_fashionphile()

    cached_rows = analyze(products)

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)