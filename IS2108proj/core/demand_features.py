"""Shared demand-data preparation for training and runtime forecasting."""

import pandas as pd

from core.models import OrderItem, Product


LAG_WEEKS = (1, 2, 4)
REQUIRED_FEATURES = (
    "sales_lag_1",
    "sales_lag_2",
    "sales_lag_4",
    "rolling_4_week_average",
)


def get_products_frame():
    """Return the product fields needed by the forecasting pipeline."""
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

    if products.empty:
        return products

    return products.rename(
        columns={
            "id": "product_id",
            "name": "product_name",
        }
    )


def get_one_time_sales_frame():
    """Return non-cancelled one-time order items as a DataFrame.

    Subscription deliveries are intentionally excluded from the ML target.
    They are added later as known demand using upcoming subscription dates.
    """
    sales_rows = list(
        OrderItem.objects
        .filter(order__subscription__isnull=True)
        .exclude(order__delivery_status="cancelled")
        .values(
            "order__created_at",
            "product_id",
            "quantity",
        )
    )

    if not sales_rows:
        return pd.DataFrame()

    sales = pd.DataFrame(sales_rows).rename(
        columns={
            "order__created_at": "sale_date",
            "quantity": "units_sold",
        }
    )

    sales["sale_date"] = pd.to_datetime(
        sales["sale_date"],
        utc=True,
    ).dt.tz_localize(None)

    sales["week"] = (
        sales["sale_date"]
        .dt.to_period("W")
        .dt.start_time
    )

    return sales


def add_lag_features(weekly_sales):
    """Add the lag and rolling-average features used by the ML model."""
    weekly_sales = weekly_sales.sort_values(
        ["product_id", "week"]
    ).copy()

    for lag in LAG_WEEKS:
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

    return weekly_sales


def build_weekly_sales():
    """Build a complete product-by-week one-time-sales data set."""
    products = get_products_frame()
    sales = get_one_time_sales_frame()

    if products.empty or sales.empty:
        return products, pd.DataFrame()

    weekly_sales = (
        sales
        .groupby(
            ["week", "product_id"],
            as_index=False,
        )["units_sold"]
        .sum()
        .merge(
            products[["product_id", "product_name"]],
            on="product_id",
            how="left",
        )
    )

    all_weeks = pd.date_range(
        weekly_sales["week"].min(),
        weekly_sales["week"].max(),
        freq="W-MON",
    )

    product_calendar = products.assign(key=1).merge(
        pd.DataFrame({"week": all_weeks, "key": 1}),
        on="key",
    ).drop(columns="key")

    weekly_sales = product_calendar.merge(
        weekly_sales,
        on=["week", "product_id", "product_name"],
        how="left",
    )

    weekly_sales["units_sold"] = (
        weekly_sales["units_sold"]
        .fillna(0)
        .astype(int)
    )

    return products, add_lag_features(weekly_sales)


def build_next_week_features(weekly_sales, products):
    """Create feature rows for the week after the latest observed week."""
    observed = weekly_sales[
        ["week", "product_id", "product_name", "units_sold"]
    ]
    next_week = weekly_sales["week"].max() + pd.Timedelta(weeks=1)
    future_rows = products[["product_id", "product_name"]].copy()
    future_rows["week"] = next_week
    future_rows["units_sold"] = float("nan")

    combined = pd.concat(
        [observed, future_rows],
        ignore_index=True,
    )
    combined = add_lag_features(combined)

    return combined[combined["week"] == next_week].copy()
