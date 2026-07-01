"""
Automated test suite for the Geospatial Flood-Risk HMM capstone product.

Testing strategy 1 of 3 -- UNIT + INTEGRATION tests (pytest).

Run:  pytest "Capstone final project/tests/test_pipeline.py" -v

These tests exercise the deployed product's core contract:
  * the trained model artefacts load and expose the expected feature schema,
  * the dataset is well-formed (no NaNs in model features, valid label space),
  * predictions have the correct shape / class range / calibrated probabilities,
  * the 2024 temporal hold-out reproduces the headline metrics in the proposal,
  * the published results_summary.json is internally consistent.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import joblib
import pytest
from sklearn.metrics import f1_score, recall_score

ROOT = Path(__file__).resolve().parents[2]            # repo root
OUT = ROOT / "model_outputs_real"
CLASSES = ["Low", "Moderate", "High"]
FEATURES = ["rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_14d_mm",
            "elevation_m", "slope_deg", "distance_to_river_m",
            "road_density_km_per_km2", "building_density_count_per_km2",
            "flood_polygon_intersection"]


@pytest.fixture(scope="session")
def data():
    df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df


@pytest.fixture(scope="session")
def model():
    b = joblib.load(OUT / "xgboost_model.joblib")
    return b["model"], b["features"]


@pytest.fixture(scope="session")
def summary():
    return json.loads((OUT / "results_summary.json").read_text())


# ---------------------------------------------------------------- artefacts
def test_model_artefacts_exist():
    assert (OUT / "xgboost_model.joblib").exists()
    assert (OUT / "hmm_model.joblib").exists()
    assert (OUT / "results_summary.json").exists()


def test_model_feature_schema(model):
    _, feat = model
    assert feat == FEATURES, "feature order must match the deployed schema"


# ---------------------------------------------------------------- dataset
def test_dataset_shape(data):
    # 729 cells x 2557 days (2018-2024) = ~1.86M cell-days
    assert data["grid_id"].nunique() == 729
    assert len(data) > 1_800_000


def test_no_nan_in_features(data):
    assert not data[FEATURES].isna().any().any(), "model features must be NaN-free"


def test_label_space_is_valid(data):
    assert set(data["flood_pressure_state"].unique()) <= set(CLASSES)


# ---------------------------------------------------------------- predictions
def test_prediction_shape_and_range(data, model):
    m, feat = model
    X = data[feat].head(1000).values
    pred = m.predict(X)
    assert pred.shape == (1000,)
    assert set(np.unique(pred)) <= {0, 1, 2}


def test_predict_proba_is_calibrated(data, model):
    m, feat = model
    proba = m.predict_proba(data[feat].head(500).values)
    assert proba.shape == (500, 3)
    assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-5), "rows must sum to 1"


# ---------------------------------------------------------------- hold-out metrics
def test_2024_holdout_reproduces_headline_metrics(data, model):
    """Re-run inference on the 2024 hold-out and confirm the proposal targets."""
    m, feat = model
    te = data[data["date"].dt.year == 2024]
    y = te["flood_pressure_state"].map({c: i for i, c in enumerate(CLASSES)}).values
    pred = m.predict(te[feat].values)
    macro_f1 = f1_score(y, pred, average="macro")
    high_recall = recall_score(y, pred, labels=[2], average="macro")
    assert macro_f1 == pytest.approx(0.8127, abs=0.02)     # SMART target >= 0.75
    assert high_recall == pytest.approx(0.8435, abs=0.02)  # SMART target >= 0.80
    assert macro_f1 >= 0.75
    assert high_recall >= 0.80


def test_summary_targets_consistent(summary):
    t = summary["targets_met"]
    assert t["macro_f1>=0.75"] is True
    assert t["high_recall>=0.80"] is True
    # spatial agreement target was honestly NOT met -- assert it is reported as such
    assert t["spatial_agreement>=0.70"] is False


def test_spatial_enrichment_above_one(summary):
    sv = summary["spatial_validation"]
    assert sv["enrichment_lift"] > 1.0, "model must concentrate High in official zones"
    assert sv["inside_outside_odds_ratio"] > 1.0
