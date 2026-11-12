"""Synthetic prototype model that predicts roast from flavour and brew method."""

import csv
from functools import lru_cache
from itertools import product
from pathlib import Path

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier


FEATURES = (
    "preferred_flavour",
    "preferred_brewing_method",
)
TRAINING_DATA_PATH = (
    Path(__file__).resolve().parent / "data" / "coffee_roast_training_data.csv"
)
MODEL_PATH = Path(__file__).resolve().parent / "ml" / "coffee_roast_model.joblib"

ROAST_LEVELS = ("light", "medium", "dark")
FLAVOURS = ("fruity", "nutty", "chocolatey", "floral", "spicy")
BREWING_METHODS = ("espresso", "french_press", "pour_over", "filter")


def _synthetic_roast(preferences):
    brew_method = preferences["preferred_brewing_method"]
    flavour = preferences["preferred_flavour"]

    if flavour in ("fruity", "floral"):
        roast_index = 0
    elif flavour in ("nutty", "chocolatey"):
        roast_index = 1
    else:
        roast_index = 2

    if brew_method in ("espresso", "french_press"):
        roast_index = min(roast_index + 1, len(ROAST_LEVELS) - 1)
    elif brew_method == "pour_over":
        roast_index = max(roast_index - 1, 0)

    return ROAST_LEVELS[roast_index]


def generate_synthetic_training_rows():
    for flavour, brew_method in product(
        FLAVOURS,
        BREWING_METHODS,
    ):
        preferences = {
            "preferred_flavour": flavour,
            "preferred_brewing_method": brew_method,
        }
        yield {
            **preferences,
            "recommended_roast": _synthetic_roast(preferences),
        }


def train_and_save_model():
    rows = list(generate_synthetic_training_rows())
    TRAINING_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRAINING_DATA_PATH.open("w", newline="", encoding="utf-8") as training_file:
        writer = csv.DictWriter(
            training_file,
            fieldnames=(*FEATURES, "recommended_roast"),
        )
        writer.writeheader()
        writer.writerows(rows)

    features = [[row[name] for name in FEATURES] for row in rows]
    labels = [row["recommended_roast"] for row in rows]
    encoder = ColumnTransformer(
        [
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                list(range(len(FEATURES))),
            )
        ]
    )
    model = Pipeline(
        [
            ("encode", encoder),
            ("classifier", DecisionTreeClassifier(max_depth=6, random_state=42)),
        ]
    )
    model.fit(features, labels)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    _load_model.cache_clear()
    return len(rows)


@lru_cache(maxsize=1)
def _load_model():
    return joblib.load(MODEL_PATH)


def predict_recommended_roast(response):
    features = [[getattr(response, feature) for feature in FEATURES]]
    return _load_model().predict(features)[0]
