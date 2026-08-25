"""
Trains a demand forecasting model on inventory_forecasting.csv and benchmarks
it against the CSV's own pre-existing `Demand Forecast` column.

Run from the project root:
    py model/train_forecast.py

Produces:
    model/demand_forecast_model.joblib   trained sklearn pipeline
    model/forecast_predictions.csv       test-set actual vs baseline vs model
    model/feature_importance.csv         RandomForest feature importances
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "inventory_forecasting.csv"
MODEL_DIR = Path(__file__).resolve().parent

TEST_START = "2023-10-01"  # last quarter of the dataset held out as test
TARGET = "Units Sold"

CATEGORICAL_FEATURES = [
    "Store ID",
    "Product ID",
    "Category",
    "Region",
    "Weather Condition",
    "Seasonality",
    "Holiday/Promotion",
]
NUMERIC_FEATURES = [
    "Price",
    "Discount",
    "Competitor Pricing",
    "Month",
    "Day_Of_Week",
    "Is_Weekend",
    "Rolling_Avg_Units_Sold_7d",
    "Rolling_Avg_Inventory_7d",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["Store ID", "Product ID", "Date"]).copy()

    df["Month"] = df["Date"].dt.month
    df["Day_Of_Week"] = df["Date"].dt.dayofweek
    df["Is_Weekend"] = (df["Day_Of_Week"] >= 5).astype(int)

    # Rolling means of *past* values only (shift 1 before rolling) so the
    # target day's own sales/inventory never leak into its own features -
    # mirrors the 5-day moving average used in sql/kpi_queries_sqlite.sql,
    # extended to 7 days per (Store, Product).
    grouped = df.groupby(["Store ID", "Product ID"])
    df["Rolling_Avg_Units_Sold_7d"] = grouped["Units Sold"].transform(
        lambda s: s.shift(1).rolling(window=7, min_periods=7).mean()
    )
    df["Rolling_Avg_Inventory_7d"] = grouped["Inventory Level"].transform(
        lambda s: s.shift(1).rolling(window=7, min_periods=7).mean()
    )

    return df.dropna(subset=["Rolling_Avg_Units_Sold_7d", "Rolling_Avg_Inventory_7d"])


def compute_metrics(actual: pd.Series, predicted: np.ndarray) -> dict:
    actual = np.asarray(actual)
    predicted = np.asarray(predicted)
    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    # MAPE is undefined for zero actuals (Units Sold == 0 on 88/109,500 rows);
    # exclude those from the percentage-error average, MAE/RMSE above already
    # account for them.
    nonzero = actual != 0
    mape = float(np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100)
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape}


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    df["Date"] = pd.to_datetime(df["Date"])
    df = engineer_features(df)

    train_df = df[df["Date"] < TEST_START]
    test_df = df[df["Date"] >= TEST_START]
    print(f"Train rows: {len(train_df)}  ({train_df['Date'].min().date()} to {train_df['Date'].max().date()})")
    print(f"Test rows:  {len(test_df)}  ({test_df['Date'].min().date()} to {test_df['Date'].max().date()})")

    corr = df[["Demand Forecast", "Price", "Discount", "Competitor Pricing"]].corrwith(df[TARGET])
    print("\nCorrelation with Units Sold (sanity check on signal available to a model):")
    print(corr.to_string())
    print(
        "Note: Demand Forecast correlates strongly with the target (r="
        f"{corr['Demand Forecast']:.2f}), consistent with it being generated as "
        "target-plus-noise rather than an independently derived forecast. Price/"
        "Discount/Competitor Pricing carry almost no linear signal in this "
        "synthetic dataset, which caps how far a legitimate feature-based model "
        "(no same-day leakage) can close the gap to that baseline.\n"
    )

    feature_cols = CATEGORICAL_FEATURES + NUMERIC_FEATURES
    X_train, y_train = train_df[feature_cols], train_df[TARGET]
    X_test, y_test = test_df[feature_cols], test_df[TARGET]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("num", "passthrough", NUMERIC_FEATURES),
        ]
    )

    models = {
        "LinearRegression": Pipeline(
            [("preprocess", preprocessor), ("model", LinearRegression())]
        ),
        "RandomForest": Pipeline(
            [
                ("preprocess", preprocessor),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
                    ),
                ),
            ]
        ),
    }

    results = {}
    predictions = {}
    for name, pipeline in models.items():
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
        predictions[name] = preds
        results[name] = compute_metrics(y_test, preds)

    # Benchmark: the dataset's own pre-existing Demand Forecast column,
    # evaluated on the identical test rows.
    results["Baseline (CSV Demand Forecast column)"] = compute_metrics(
        y_test, test_df["Demand Forecast"].to_numpy()
    )

    print("\nModel comparison on test set (2023 Q4 holdout):")
    print(f"{'Model':<38}{'MAE':>10}{'RMSE':>10}{'MAPE %':>10}")
    for name, m in results.items():
        print(f"{name:<38}{m['MAE']:>10.2f}{m['RMSE']:>10.2f}{m['MAPE']:>10.2f}")

    best_model_name = min(
        (n for n in models), key=lambda n: results[n]["MAPE"]
    )
    best_pipeline = models[best_model_name]
    print(f"\nBest trained model: {best_model_name} (MAPE {results[best_model_name]['MAPE']:.2f}%)")

    joblib.dump(best_pipeline, MODEL_DIR / "demand_forecast_model.joblib")

    out = test_df[["Date", "Store ID", "Product ID", "Category", "Region"]].copy()
    out["Actual"] = y_test.values
    out["Baseline_Demand_Forecast"] = test_df["Demand Forecast"].values
    out["Model_Prediction"] = np.round(predictions[best_model_name], 2)
    out.to_csv(MODEL_DIR / "forecast_predictions.csv", index=False)

    if best_model_name == "RandomForest":
        ohe = best_pipeline.named_steps["preprocess"].named_transformers_["cat"]
        feature_names = list(ohe.get_feature_names_out(CATEGORICAL_FEATURES)) + NUMERIC_FEATURES
        importances = best_pipeline.named_steps["model"].feature_importances_
        importance_df = (
            pd.DataFrame({"feature": feature_names, "importance": importances})
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
        importance_df.to_csv(MODEL_DIR / "feature_importance.csv", index=False)

    print(f"\nSaved: {MODEL_DIR / 'demand_forecast_model.joblib'}")
    print(f"Saved: {MODEL_DIR / 'forecast_predictions.csv'}")


if __name__ == "__main__":
    main()
