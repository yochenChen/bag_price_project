from flask import Flask, render_template
import pandas as pd

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

    summary["average_price"] = summary["average_price"].round(0).astype(int)
    summary["lowest_price"] = summary["lowest_price"].astype(int)
    summary["highest_price"] = summary["highest_price"].astype(int)

    summary = summary.sort_values(
        by=["brand", "name"],
        ascending=[True, True]
    )

    return summary.to_dict(orient="records")


@app.route("/")
def home():
    df = pd.read_csv("products.csv")
    products = df.to_dict(orient="records")
    rows = analyze(products)

    return render_template("index.html", rows=rows)


if __name__ == "__main__":
    app.run(debug=True)