from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from core.demand_features import REQUIRED_FEATURES, build_weekly_sales


class Command(BaseCommand):
    help = (
        "Train the restock demand model on one-time sales and save it "
        "for subscription-adjusted forecasting."
    )

    def handle(self, *args, **options):
        products, weekly_sales = build_weekly_sales()

        if products.empty or weekly_sales.empty:
            raise CommandError("There is not enough sales data to train the model.")

        model_data = weekly_sales.dropna(
            subset=list(REQUIRED_FEATURES),
        ).copy()

        if model_data["week"].nunique() < 5:
            raise CommandError(
                "At least five weeks with lag features are required to train the model."
            )

        model_data = pd.get_dummies(
            model_data,
            columns=["product_id"],
            dtype=float,
        )

        feature_columns = [
            column
            for column in model_data.columns
            if column.startswith("product_id_")
        ]
        feature_columns += list(REQUIRED_FEATURES)

        cutoff_date = model_data["week"].quantile(0.8)
        train_data = model_data[model_data["week"] < cutoff_date]
        test_data = model_data[model_data["week"] >= cutoff_date]

        if train_data.empty or test_data.empty:
            raise CommandError(
                "The time-based train/test split did not produce both data sets."
            )

        model = HistGradientBoostingRegressor(
            loss="poisson",
            max_iter=200,
            random_state=42,
        )
        model.fit(
            train_data[feature_columns],
            train_data["units_sold"],
        )

        test_predictions = model.predict(test_data[feature_columns])
        model_mae = mean_absolute_error(
            test_data["units_sold"],
            test_predictions,
        )
        baseline_mae = mean_absolute_error(
            test_data["units_sold"],
            test_data["rolling_4_week_average"],
        )

        final_model = HistGradientBoostingRegressor(
            loss="poisson",
            max_iter=200,
            random_state=42,
        )
        final_model.fit(
            model_data[feature_columns],
            model_data["units_sold"],
        )

        model_path = (
            Path(settings.BASE_DIR)
            / "core"
            / "ml_models"
            / "demand_model.joblib"
        )
        model_path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(
            {
                "model": final_model,
                "features": feature_columns,
                "model_name": "HistGradientBoostingRegressor",
                "target": "one_time_units_sold",
                "subscription_adjustment": True,
                "model_mae": round(float(model_mae), 4),
                "baseline_mae": round(float(baseline_mae), 4),
            },
            model_path,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Saved demand model to {model_path}"
            )
        )
        self.stdout.write(f"Model MAE: {model_mae:.2f}")
        self.stdout.write(f"Baseline MAE: {baseline_mae:.2f}")
        self.stdout.write(
            "Subscription deliveries are added at prediction time using "
            "active subscriptions and BundleItem quantities."
        )
