"""
Geospatial Flood-Risk Modelling using Climate Data and Hidden Markov Models
Kigali (Nyabugogo-Mpazi corridor), Rwanda  -- Capstone training pipeline.

Implements the methodology from the proposal (Table 3.4 / 3.5):
  1. Rainfall-threshold baseline
  2. Static flood-polygon baseline
  3. Logistic Regression / Decision Tree (interpretable baselines)
  4. Random Forest
  5. XGBoost (main model)  + SHAP explanations
  6. HMM temporal layer (hmmlearn): daily flood-pressure state transitions

External data: real daily rainfall is pulled from the free, keyless Open-Meteo
ERA5 archive ("meteo") for the Kigali cell centroids and merged as a
cross-check / extra feature set. MINEMA incident records and Google Maps are
not used: MINEMA has no public API and Google Maps needs a paid key -- the
terrain / hydrology / exposure features those would provide are already
engineered into the dataset (elevation, slope, distance_to_river, densities).
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    f1_score, accuracy_score, classification_report, confusion_matrix,
)
import xgboost as xgb

warnings.filterwarnings("ignore")

ROOT = Path(__file__).parent
DATA = ROOT / "Flood_Risk_Model_Expanded_Data_1000_Rows.xlsx"
OUT = ROOT / "model_outputs"
OUT.mkdir(exist_ok=True)

CLASSES = ["Low", "Moderate", "High"]
CLASS_TO_INT = {c: i for i, c in enumerate(CLASSES)}

GEO_FEATURES = [
    "rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_14d_mm",
    "elevation_m", "slope_deg", "distance_to_river_m",
    "road_density_km_per_km2", "building_density_count_per_km2",
    "flood_polygon_intersection",
]


# --------------------------------------------------------------------------- #
# 1. Load + Open-Meteo enrichment
# --------------------------------------------------------------------------- #
def load_data():
    df = pd.read_excel(DATA)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["grid_id", "date"]).reset_index(drop=True)
    return df


def fetch_open_meteo(df):
    """Fetch real ERA5 daily rainfall for each (rounded) cell centroid and
    compute matching rolling windows. Returns df with real_rain_* columns,
    or the original df (cols filled NaN) if offline."""
    print("\n[meteo] Fetching real daily rainfall from Open-Meteo (ERA5)...")
    start = (df["date"].min() - pd.Timedelta(days=14)).strftime("%Y-%m-%d")
    end = df["date"].max().strftime("%Y-%m-%d")

    # group nearby cells: ERA5 grid is coarse, so round to 2 dp (~1.1 km)
    df["_lat2"] = df["centroid_lat"].round(2)
    df["_lon2"] = df["centroid_lon"].round(2)
    points = df[["_lat2", "_lon2"]].drop_duplicates().values
    print(f"[meteo] {len(points)} unique grid points, {start} -> {end}")

    cache = {}
    for lat, lon in points:
        try:
            r = requests.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={
                    "latitude": lat, "longitude": lon,
                    "start_date": start, "end_date": end,
                    "daily": "precipitation_sum", "timezone": "Africa/Kigali",
                },
                timeout=30,
            )
            d = r.json()["daily"]
            s = pd.Series(d["precipitation_sum"],
                          index=pd.to_datetime(d["time"])).fillna(0.0)
            cache[(lat, lon)] = pd.DataFrame({
                "real_rain_1d_mm": s,
                "real_rain_3d_mm": s.rolling(3, min_periods=1).sum(),
                "real_rain_7d_mm": s.rolling(7, min_periods=1).sum(),
                "real_rain_14d_mm": s.rolling(14, min_periods=1).sum(),
            })
        except Exception as e:
            print(f"[meteo] FAILED for ({lat},{lon}): {e}")
            cache = {}
            break

    real_cols = ["real_rain_1d_mm", "real_rain_3d_mm",
                 "real_rain_7d_mm", "real_rain_14d_mm"]
    if not cache:
        print("[meteo] Enrichment unavailable -- proceeding with dataset only.")
        for c in real_cols:
            df[c] = np.nan
        return df, []

    def lookup(row):
        tab = cache.get((row["_lat2"], row["_lon2"]))
        if tab is None or row["date"] not in tab.index:
            return pd.Series({c: np.nan for c in real_cols})
        return tab.loc[row["date"], real_cols]

    df[real_cols] = df.apply(lookup, axis=1)
    df.drop(columns=["_lat2", "_lon2"], inplace=True)
    corr = df["rainfall_1d_mm"].corr(df["real_rain_1d_mm"])
    print(f"[meteo] OK. corr(dataset 1d rain, real ERA5 1d rain) = {corr:.3f}")
    print(f"[meteo] real 1d rain mean={df['real_rain_1d_mm'].mean():.2f}mm "
          f"max={df['real_rain_1d_mm'].max():.2f}mm")
    return df, real_cols


# --------------------------------------------------------------------------- #
# 2. Baselines
# --------------------------------------------------------------------------- #
def threshold_baseline(df):
    """Pure rainfall-threshold classifier (tests if geo features add value)."""
    r = df["rainfall_3d_mm"]
    lo, hi = r.quantile(1 / 3), r.quantile(2 / 3)
    pred = np.where(r <= lo, "Low", np.where(r <= hi, "Moderate", "High"))
    return pred


def polygon_baseline(df):
    """Static official-polygon flag (tests if temporal rainfall adds value)."""
    return np.where(df["flood_polygon_intersection"] == 1, "High", "Low")


# --------------------------------------------------------------------------- #
# 3. Supervised models (group-aware CV by grid_id)
# --------------------------------------------------------------------------- #
def evaluate_supervised(df, feature_cols):
    X = df[feature_cols].values
    y = df["flood_pressure_state"].map(CLASS_TO_INT).values
    groups = df["grid_id"].values

    models = {
        "LogisticRegression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)),
        "DecisionTree": DecisionTreeClassifier(max_depth=6, random_state=42),
        "RandomForest": RandomForestClassifier(
            n_estimators=400, max_depth=None, min_samples_leaf=2,
            random_state=42, n_jobs=-1),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=500, max_depth=4, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9, objective="multi:softprob",
            num_class=3, eval_metric="mlogloss", random_state=42, n_jobs=-1),
    }

    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    results = {}
    oof_pred = {m: np.zeros(len(y), dtype=int) for m in models}

    for name, model in models.items():
        f1s, accs = [], []
        for tr, te in cv.split(X, y, groups):
            model.fit(X[tr], y[tr])
            p = model.predict(X[te])
            oof_pred[name][te] = p
            f1s.append(f1_score(y[te], p, average="macro"))
            accs.append(accuracy_score(y[te], p))
        results[name] = {
            "macro_f1_mean": float(np.mean(f1s)),
            "macro_f1_std": float(np.std(f1s)),
            "accuracy_mean": float(np.mean(accs)),
        }
        print(f"  {name:18s} macroF1={np.mean(f1s):.3f}±{np.std(f1s):.3f} "
              f"acc={np.mean(accs):.3f}")

    # add baselines on same labels
    for bname, bpred in [("RainfallThreshold", threshold_baseline(df)),
                         ("StaticPolygon", polygon_baseline(df))]:
        bp = pd.Series(bpred).map(CLASS_TO_INT).values
        results[bname] = {
            "macro_f1_mean": float(f1_score(y, bp, average="macro")),
            "accuracy_mean": float(accuracy_score(y, bp)),
        }
        print(f"  {bname:18s} macroF1={results[bname]['macro_f1_mean']:.3f} "
              f"acc={results[bname]['accuracy_mean']:.3f}  (baseline)")

    return models, results, oof_pred, X, y, groups


def fit_final_xgb(df, feature_cols):
    """Fit XGBoost on all data for SHAP + feature importance + saving."""
    X = df[feature_cols].values
    y = df["flood_pressure_state"].map(CLASS_TO_INT).values
    model = xgb.XGBClassifier(
        n_estimators=500, max_depth=4, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, objective="multi:softprob",
        num_class=3, eval_metric="mlogloss", random_state=42, n_jobs=-1)
    model.fit(X, y)
    return model, X, y


# --------------------------------------------------------------------------- #
# 4. HMM temporal layer
# --------------------------------------------------------------------------- #
def train_hmm(df):
    """Fit a Gaussian HMM on per-grid daily rainfall sequences and report the
    learned state-transition matrix + next-step prediction accuracy.

    Hidden states = latent flood-pressure regimes; observations = the rainfall
    window features. States are aligned to Low/Moderate/High by mean rainfall.
    """
    from hmmlearn import hmm

    obs_cols = ["rainfall_1d_mm", "rainfall_3d_mm",
                "rainfall_7d_mm", "rainfall_14d_mm"]
    df = df.sort_values(["grid_id", "date"])

    seqs, lengths, true_states = [], [], []
    for _, g in df.groupby("grid_id"):
        seqs.append(g[obs_cols].values)
        lengths.append(len(g))
        true_states.append(g["flood_pressure_state"].map(CLASS_TO_INT).values)
    Xc = np.vstack(seqs)

    scaler = StandardScaler().fit(Xc)
    Xs = scaler.transform(Xc)

    model = hmm.GaussianHMM(
        n_components=3, covariance_type="diag",
        n_iter=300, random_state=42)
    model.fit(Xs, lengths)

    # decode states for every sequence
    decoded = []
    idx = 0
    for L in lengths:
        decoded.append(model.predict(Xs[idx:idx + L], [L]))
        idx += L
    decoded_all = np.concatenate(decoded)
    true_all = np.concatenate(true_states)

    # align HMM latent state ids -> Low/Mod/High by mean observed 3d rainfall
    rain3 = Xc[:, 1]
    order = (pd.DataFrame({"s": decoded_all, "r": rain3})
             .groupby("s")["r"].mean().sort_values().index.tolist())
    remap = {old: new for new, old in enumerate(order)}
    decoded_mapped = np.array([remap[s] for s in decoded_all])

    state_acc = accuracy_score(true_all, decoded_mapped)

    # transition matrix in the aligned ordering
    T = model.transmat_
    P = np.zeros_like(T)
    for i_old, i_new in remap.items():
        for j_old, j_new in remap.items():
            P[i_new, j_new] = T[i_old, j_old]

    # next-step accuracy: predict t+1 state as argmax of P[current decoded]
    correct = total = 0
    idx = 0
    for L, ts in zip(lengths, true_states):
        dseq = decoded_mapped[idx:idx + L]
        for t in range(L - 1):
            pred_next = int(np.argmax(P[dseq[t]]))
            if pred_next == ts[t + 1]:
                correct += 1
            total += 1
        idx += L
    next_step_acc = correct / total if total else float("nan")

    print(f"  HMM decoded-vs-label state acc = {state_acc:.3f}")
    print(f"  HMM next-step prediction acc   = {next_step_acc:.3f}")
    print("  Aligned transition matrix (rows=from Low/Mod/High):")
    print(np.array2string(P, precision=3, suppress_small=True))

    joblib.dump({"model": model, "scaler": scaler, "remap": remap},
                OUT / "hmm_model.joblib")
    return {
        "transition_matrix": P.tolist(),
        "state_labels": CLASSES,
        "decoded_state_accuracy": float(state_acc),
        "next_step_accuracy": float(next_step_acc),
        "stationary_note": "rows=from-state, cols=to-state, ordered Low<Mod<High",
    }, P


# --------------------------------------------------------------------------- #
# 5. Plots
# --------------------------------------------------------------------------- #
def plot_confusion(df, oof_pred, name):
    y = df["flood_pressure_state"].map(CLASS_TO_INT).values
    cm = confusion_matrix(y, oof_pred[name])
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(CLASSES); ax.set_yticklabels(CLASSES)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title(f"{name} (out-of-fold)")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, fraction=0.046)
    fig.tight_layout()
    fig.savefig(OUT / f"confusion_{name}.png", dpi=130)
    plt.close(fig)


def plot_importance(model, feature_cols):
    imp = model.feature_importances_
    order = np.argsort(imp)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh([feature_cols[i] for i in order], imp[order], color="#2b7a4b")
    ax.set_title("XGBoost feature importance")
    fig.tight_layout()
    fig.savefig(OUT / "xgb_feature_importance.png", dpi=130)
    plt.close(fig)


def plot_transition(P):
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(P, cmap="Oranges", vmin=0, vmax=1)
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(CLASSES); ax.set_yticklabels(CLASSES)
    ax.set_xlabel("To state"); ax.set_ylabel("From state")
    ax.set_title("HMM daily transition matrix")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{P[i, j]:.2f}", ha="center", va="center",
                    color="white" if P[i, j] > 0.5 else "black")
    fig.colorbar(im, fraction=0.046)
    fig.tight_layout()
    fig.savefig(OUT / "hmm_transition_matrix.png", dpi=130)
    plt.close(fig)


def shap_summary(model, X, feature_cols):
    try:
        import shap
        expl = shap.TreeExplainer(model)
        sv = expl.shap_values(X)
        shap.summary_plot(sv, X, feature_names=feature_cols,
                          show=False, plot_type="bar")
        plt.tight_layout()
        plt.savefig(OUT / "shap_summary.png", dpi=130, bbox_inches="tight")
        plt.close()
        print("  SHAP summary saved.")
    except Exception as e:
        print(f"  SHAP skipped: {e}")


# --------------------------------------------------------------------------- #
def main():
    print("=" * 70)
    print("FLOOD-RISK HMM CAPSTONE -- TRAINING PIPELINE")
    print("=" * 70)

    df = load_data()
    print(f"Loaded {len(df)} rows | {df['grid_id'].nunique()} grid cells | "
          f"{df['date'].nunique()} days | classes {df['flood_pressure_state'].value_counts().to_dict()}")

    df, real_cols = fetch_open_meteo(df)
    feature_cols = GEO_FEATURES + [c for c in real_cols
                                   if df[c].notna().any()]
    print(f"\nUsing {len(feature_cols)} features: {feature_cols}")

    print("\n[Supervised models -- 5-fold StratifiedGroupKFold by grid]")
    models, results, oof_pred, X, y, groups = evaluate_supervised(df, feature_cols)

    print("\n[Final XGBoost fit -> SHAP + importance]")
    xgb_final, Xf, yf = fit_final_xgb(df, feature_cols)
    joblib.dump({"model": xgb_final, "features": feature_cols},
                OUT / "xgboost_model.joblib")
    plot_importance(xgb_final, feature_cols)
    shap_summary(xgb_final, Xf, feature_cols)

    for m in ["RandomForest", "XGBoost"]:
        plot_confusion(df, oof_pred, m)
    print("\n  Best supervised classification report (XGBoost, out-of-fold):")
    print(classification_report(y, oof_pred["XGBoost"], target_names=CLASSES))

    print("\n[HMM temporal layer -- hmmlearn GaussianHMM]")
    hmm_res, P = train_hmm(df)
    plot_transition(P)

    summary = {
        "dataset": {
            "rows": len(df), "cells": int(df["grid_id"].nunique()),
            "days": int(df["date"].nunique()),
            "class_balance": df["flood_pressure_state"].value_counts().to_dict(),
        },
        "open_meteo_enrichment": bool(real_cols),
        "features": feature_cols,
        "supervised_results": results,
        "hmm": hmm_res,
    }
    with open(OUT / "results_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("DONE. Artifacts in:", OUT)
    print("  models: xgboost_model.joblib, hmm_model.joblib")
    print("  figures: confusion_*, xgb_feature_importance, shap_summary,")
    print("           hmm_transition_matrix")
    print("  metrics: results_summary.json")
    print("=" * 70)
    # ranked leaderboard
    board = sorted(results.items(),
                   key=lambda kv: kv[1]["macro_f1_mean"], reverse=True)
    print("\nLEADERBOARD (macro-F1):")
    for name, r in board:
        print(f"  {name:18s} {r['macro_f1_mean']:.3f}")


if __name__ == "__main__":
    main()
