from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings

from core.demand_features import (
    build_next_week_features,
    build_weekly_sales,
)
from core.models import CustomerSubscription


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


def get_scheduled_subscription_units(forecast_week):
    """Return known subscription units due in a forecast week by product.

    A product's expected subscription demand is calculated from:

        active subscription × BundleItem.quantity

    Only deliveries whose next_delivery_date falls inside the forecast week
    are counted. This avoids treating a monthly subscription as weekly demand.
    """
    week_start = forecast_week.date()
    week_end = week_start + timedelta(days=7)
    subscription_units = defaultdict(int)

    subscriptions = (
        CustomerSubscription.objects
        .filter(
            status="active",
            next_delivery_date__gte=week_start,
            next_delivery_date__lt=week_end,
        )
        .prefetch_related("bundle__bundle_items")
    )

    for subscription in subscriptions:
        delivery_date = subscription.next_delivery_date

        if (
            subscription.end_date is not None
            and delivery_date > subscription.end_date.date()
        ):
            continue

        for bundle_item in subscription.bundle.bundle_items.all():
            subscription_units[bundle_item.product_id] += bundle_item.quantity

    return subscription_units


def get_restock_predictions():
    model, feature_columns = load_demand_model()
    products, weekly_sales = build_weekly_sales()

    if weekly_sales.empty:
        return []

    forecast_rows = build_next_week_features(
        weekly_sales,
        products,
    )

    if forecast_rows.empty:
        return []

    feature_data = pd.get_dummies(
        forecast_rows,
        columns=["product_id"],
        dtype=float,
    )

    # Match the exact columns used when the model was trained.
    for column in feature_columns:
        if column not in feature_data.columns:
            feature_data[column] = 0

    model_input = feature_data[feature_columns]
    predicted_base_demand = model.predict(model_input)

    forecast_week = forecast_rows["week"].iloc[0]
    subscription_units = get_scheduled_subscription_units(forecast_week)
    predictions = []

    for row, prediction in zip(
        forecast_rows.itertuples(index=False),
        predicted_base_demand,
    ):
        predicted_base_units = max(
            0,
            int(round(float(prediction))),
        )
        committed_subscription_units = subscription_units.get(
            row.product_id,
            0,
        )
        predicted_demand = (
            predicted_base_units
            + committed_subscription_units
        )

        current_stock = int(products.loc[
            products["product_id"] == row.product_id,
            "stock_level",
        ].iloc[0])
        reorder_threshold = int(products.loc[
            products["product_id"] == row.product_id,
            "reorder_threshold",
        ].iloc[0])

        suggested_restock = max(
            0,
            predicted_demand - current_stock,
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
            "forecast_week": forecast_week.date(),
            "predicted_base_demand": predicted_base_units,
            "subscription_units": committed_subscription_units,
            "predicted_demand": predicted_demand,
            "current_stock": current_stock,
            "suggested_restock": suggested_restock,
            "stock_status": stock_status,
        })

    return predictions
