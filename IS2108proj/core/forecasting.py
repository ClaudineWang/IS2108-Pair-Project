from pathlib import Path
import joblib
from django.conf import settings
from core.models import OrderItem, Product
import pandas as pd

MODEL_PATH = (
    Path(settings.BASE_DIR)
    / "core"
    / "ml_models"
    / "demand_model.joblib"
)


def load_demand_model():
    artifact = joblib.load(MODEL_PATH)

    return (
        artifact["model"],
        artifact["features"],
    )

def get_restock_predictions():
    model, feature_columns = load_demand_model()

    sales_rows = list(
        OrderItem.objects
        .exclude(order__delivery_status="cancelled")
        .values(
            "order__created_at",
            "product_id",
            "quantity",
        )
    )

    if not sales_rows:
        return []

    products = pd.DataFrame(
        list(
            Product.objects.values(
                "id",
                "name",
                "stock_level",
                "reorder_threshold",
            )
        )
    )

    products = products.rename(
        columns={
            "id": "product_id",
            "name": "product_name",
        }
    )

    sales = pd.DataFrame(sales_rows)

    sales = sales.rename(
        columns={
            "order__created_at": "sale_date",
            "quantity": "units_sold",
        }
    )

    sales["sale_date"] = pd.to_datetime(
        sales["sale_date"],
        utc=True
    ).dt.tz_localize(None)

    sales["week"] = (
        sales["sale_date"]
        .dt.to_period("W")
        .dt.start_time
    )

    weekly_sales = (
        sales
        .groupby(
            ["week", "product_id"],
            as_index=False
        )["units_sold"]
        .sum()
    )

    weekly_sales = weekly_sales.merge(
        products[["product_id", "product_name"]],
        on="product_id",
        how="left"
    )

    all_weeks = pd.date_range(
        weekly_sales["week"].min(),
        weekly_sales["week"].max(),
        freq="W-MON"
    )

    product_calendar = products.assign(key=1).merge(
        pd.DataFrame({
            "week": all_weeks,
            "key": 1,
        }),
        on="key"
    ).drop(columns="key")

    weekly_sales = product_calendar.merge(
        weekly_sales,
        on=["week", "product_id", "product_name"],
        how="left"
    )

    weekly_sales["units_sold"] = (
        weekly_sales["units_sold"]
        .fillna(0)
        .astype(int)
    )

    weekly_sales = weekly_sales.sort_values(
        ["product_id", "week"]
    )

    for lag in [1, 2, 4]:
        weekly_sales[f"sales_lag_{lag}"] = (
            weekly_sales
            .groupby("product_id")["units_sold"]
            .shift(lag)
        )

    weekly_sales["rolling_4_week_average"] = (
        weekly_sales
        .groupby("product_id")["units_sold"]
        .transform(
            lambda values: (
                values
                .shift(1)
                .rolling(4)
                .mean()
            )
        )
    )

    weekly_sales["month"] = weekly_sales["week"].dt.month

    weekly_sales["week_of_year"] = (
        weekly_sales["week"]
        .dt.isocalendar()
        .week
        .astype(int)
    )

    required_features = [
        "sales_lag_1",
        "sales_lag_2",
        "sales_lag_4",
        "rolling_4_week_average",
    ]

    latest = (
        weekly_sales
        .dropna(subset=required_features)
        .sort_values("week")
        .groupby("product_id")
        .tail(1)
        .copy()
    )

    if latest.empty:
        return []

    feature_data = pd.get_dummies(
        latest,
        columns=["product_id"],
        dtype=float
    )

    # Add any missing columns expected by the trained model.
    for column in feature_columns:
        if column not in feature_data.columns:
            feature_data[column] = 0

    model_input = feature_data[feature_columns]

    predicted_units = model.predict(model_input)

    predictions = []

    for row, prediction in zip(
        latest.itertuples(index=False),
        predicted_units
    ):
        predicted_demand = max(
            0,
            int(round(float(prediction)))
        )

        current_stock = int(row.stock_level)
        reorder_threshold = int(row.reorder_threshold)

        suggested_restock = max(
            0,
            predicted_demand - current_stock
        )

        if current_stock == 0:
            stock_status = "Out of Stock"
        elif current_stock <= reorder_threshold:
            stock_status = "Low in Stock"
        else:
            stock_status = "In Stock"

        predictions.append({
            "product_id": row.product_id,
            "product_name": row.product_name,
            "current_stock": current_stock,
            "predicted_demand": predicted_demand,
            "suggested_restock": suggested_restock,
            "stock_status": stock_status,
        })

    return predictions