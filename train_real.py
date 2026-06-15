"""
Train & evaluate the flood-pressure pipeline on the REAL Nyabugogo-Mpazi
dataset, following the proposal's evaluation protocol:

  * Temporal hold-out: train on 2018-2023, test on 2024 (held-out PERIOD).
  * Supervised models: LogisticRegression/DecisionTree baselines, RandomForest,
    XGBoost; plus rainfall-threshold and static-polygon baselines.
  * Targets: macro-F1 >= 0.75 and High-pressure recall >= 0.80 (Obj. 3).
  * HMM temporal layer: daily state transitions, next-step accuracy, and
    spatial agreement -- >= 70% of predicted-High cells inside flood polygons
    (Obj. 4).
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (f1_score, accuracy_score, recall_score,
                             classification_report, confusion_matrix)
import xgboost as xgb

warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent
OUT = ROOT / "model_outputs_real"
OUT.mkdir(exist_ok=True)

CLASSES = ["Low", "Moderate", "High"]
C2I = {c: i for i, c in enumerate(CLASSES)}
FEATURES = ["rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_14d_mm",
            "elevation_m", "slope_deg", "distance_to_river_m",
            "road_density_km_per_km2", "building_density_count_per_km2",
            "flood_polygon_intersection"]


def load():
    df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
    df["date"] = pd.to_datetime(df["date"])
    df["y"] = df["flood_pressure_state"].map(C2I)
    return df


def temporal_split(df):
    tr = df[df["date"].dt.year <= 2023].copy()
    te = df[df["date"].dt.year == 2024].copy()
    print(f"[split] train {len(tr)} rows (2018-2023) | test {len(te)} rows (2024)")
    return tr, te


def thr_baseline(df, lo, hi):
    r = df["rainfall_3d_mm"]
    return np.where(r <= lo, 0, np.where(r <= hi, 1, 2))


def supervised(tr, te):
    Xtr, ytr = tr[FEATURES].values, tr["y"].values
    Xte, yte = te[FEATURES].values, te["y"].values
    models = {
        "LogisticRegression": make_pipeline(StandardScaler(),
            LogisticRegression(max_iter=2000)),
        "DecisionTree": DecisionTreeClassifier(max_depth=8, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
            random_state=42, n_jobs=-1),
        "XGBoost": xgb.XGBClassifier(n_estimators=400, max_depth=5,
            learning_rate=0.07, subsample=0.9, colsample_bytree=0.9,
            tree_method="hist", objective="multi:softprob", num_class=3,
            eval_metric="mlogloss", random_state=42, n_jobs=-1),
    }
    res, preds = {}, {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        p = m.predict(Xte)
        preds[name] = p
        res[name] = {
            "macro_f1": float(f1_score(yte, p, average="macro")),
            "accuracy": float(accuracy_score(yte, p)),
            "high_recall": float(recall_score(yte, p, labels=[2], average="macro")),
        }
        print(f"  {name:18s} macroF1={res[name]['macro_f1']:.3f} "
              f"acc={res[name]['accuracy']:.3f} HighRecall={res[name]['high_recall']:.3f}")

    # baselines (thresholds learned on train rainfall terciles)
    lo, hi = tr["rainfall_3d_mm"].quantile([1/3, 2/3])
    bp = thr_baseline(te, lo, hi)
    res["RainfallThreshold"] = {
        "macro_f1": float(f1_score(yte, bp, average="macro")),
        "accuracy": float(accuracy_score(yte, bp)),
        "high_recall": float(recall_score(yte, bp, labels=[2], average="macro"))}
    pp = np.where(te["flood_polygon_intersection"] == 1, 2, 0)
    res["StaticPolygon"] = {
        "macro_f1": float(f1_score(yte, pp, average="macro")),
        "accuracy": float(accuracy_score(yte, pp)),
        "high_recall": float(recall_score(yte, pp, labels=[2], average="macro"))}
    for b in ["RainfallThreshold", "StaticPolygon"]:
        print(f"  {b:18s} macroF1={res[b]['macro_f1']:.3f} "
              f"acc={res[b]['accuracy']:.3f} HighRecall={res[b]['high_recall']:.3f}  (baseline)")
    return models, res, preds, yte


def plot_confusion(yte, p, name):
    cm = confusion_matrix(yte, p)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(CLASSES); ax.set_yticklabels(CLASSES)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title(f"{name} (2024 hold-out)")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max()/2 else "black")
    fig.tight_layout(); fig.savefig(OUT / f"confusion_{name}.png", dpi=130)
    plt.close(fig)


def plot_importance(model):
    imp = model.feature_importances_; order = np.argsort(imp)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh([FEATURES[i] for i in order], imp[order], color="#2b7a4b")
    ax.set_title("XGBoost feature importance (real data)")
    fig.tight_layout(); fig.savefig(OUT / "xgb_feature_importance.png", dpi=130)
    plt.close(fig)


def shap_summary(model, Xsample):
    try:
        import shap
        sv = shap.TreeExplainer(model).shap_values(Xsample)
        shap.summary_plot(sv, Xsample, feature_names=FEATURES, show=False,
                          plot_type="bar")
        plt.tight_layout()
        plt.savefig(OUT / "shap_summary.png", dpi=130, bbox_inches="tight")
        plt.close()
        print("  SHAP summary saved.")
    except Exception as e:
        print(f"  SHAP skipped: {e}")


def hmm_layer(df):
    from hmmlearn import hmm
    obs = ["rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_14d_mm"]
    df = df.sort_values(["grid_id", "date"])
    seqs, lengths, truth, zone = [], [], [], []
    for gid, g in df.groupby("grid_id"):
        seqs.append(g[obs].values); lengths.append(len(g))
        truth.append(g["y"].values)
        zone.append(g["flood_polygon_intersection"].values)
    Xc = np.vstack(seqs)
    scaler = StandardScaler().fit(Xc); Xs = scaler.transform(Xc)
    model = hmm.GaussianHMM(n_components=3, covariance_type="diag",
                            n_iter=200, random_state=42)
    model.fit(Xs, lengths)

    decoded, idx = [], 0
    for L in lengths:
        decoded.append(model.predict(Xs[idx:idx+L], [L])); idx += L
    dall = np.concatenate(decoded); tall = np.concatenate(truth)
    zall = np.concatenate(zone)

    rain3 = Xc[:, 1]
    order = (pd.DataFrame({"s": dall, "r": rain3}).groupby("s")["r"].mean()
             .sort_values().index.tolist())
    remap = {o: n for n, o in enumerate(order)}
    dmap = np.array([remap[s] for s in dall])

    state_acc = accuracy_score(tall, dmap)
    T = model.transmat_; P = np.zeros_like(T)
    for io, inn in remap.items():
        for jo, jn in remap.items():
            P[inn, jn] = T[io, jo]

    correct = total = 0; idx = 0
    for L, ts in zip(lengths, truth):
        d = dmap[idx:idx+L]
        for t in range(L-1):
            if int(np.argmax(P[d[t]])) == ts[t+1]:
                correct += 1
            total += 1
        idx += L
    next_acc = correct/total

    # spatial agreement: of cells whose decoded state is High, fraction in flood zone
    high_mask = dmap == 2
    spatial_agree = float(zall[high_mask].mean()) if high_mask.any() else float("nan")

    print(f"  HMM decoded-vs-label acc = {state_acc:.3f}")
    print(f"  HMM next-step acc        = {next_acc:.3f}")
    print(f"  Spatial agreement (High in flood zone) = {spatial_agree:.3f}")
    print("  Transition matrix (Low/Mod/High):")
    print(np.array2string(P, precision=3, suppress_small=True))

    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(P, cmap="Oranges", vmin=0, vmax=1)
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(CLASSES); ax.set_yticklabels(CLASSES)
    ax.set_xlabel("To"); ax.set_ylabel("From"); ax.set_title("HMM daily transitions (real)")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{P[i,j]:.2f}", ha="center", va="center",
                    color="white" if P[i, j] > 0.5 else "black")
    fig.tight_layout(); fig.savefig(OUT / "hmm_transition_matrix.png", dpi=130)
    plt.close(fig)
    joblib.dump({"model": model, "scaler": scaler, "remap": remap},
                OUT / "hmm_model.joblib")
    return {"decoded_state_accuracy": float(state_acc),
            "next_step_accuracy": float(next_acc),
            "spatial_agreement_high_in_zone": spatial_agree,
            "transition_matrix": P.tolist()}


def main():
    print("="*70); print("TRAINING ON REAL DATA -- Nyabugogo-Mpazi, Kigali"); print("="*70)
    df = load()
    print(f"Rows {len(df)} | cells {df['grid_id'].nunique()} | "
          f"days {df['date'].nunique()} | classes {df['flood_pressure_state'].value_counts().to_dict()}")
    tr, te = temporal_split(df)

    print("\n[Supervised -- temporal hold-out (train<=2023, test=2024)]")
    models, res, preds, yte = supervised(tr, te)

    best = max(["RandomForest", "XGBoost"], key=lambda m: res[m]["macro_f1"])
    # spatial agreement (Obj. 4): share of predicted-High cell-days that fall
    # inside flood-risk polygons, for the best supervised model
    zone = te["flood_polygon_intersection"].values
    for m in ["RandomForest", "XGBoost"]:
        hi = preds[m] == 2
        res[m]["spatial_agreement_high_in_zone"] = (
            float(zone[hi].mean()) if hi.any() else float("nan"))
    print(f"  Spatial agreement (predicted-High in flood zone): "
          f"RF={res['RandomForest']['spatial_agreement_high_in_zone']:.3f} "
          f"XGB={res['XGBoost']['spatial_agreement_high_in_zone']:.3f}")
    for m in ["RandomForest", "XGBoost"]:
        plot_confusion(yte, preds[m], m)
    plot_importance(models["XGBoost"])
    rng = np.random.default_rng(42)
    samp = te[FEATURES].values
    samp = samp[rng.choice(len(samp), size=min(4000, len(samp)), replace=False)]
    shap_summary(models["XGBoost"], samp)
    joblib.dump({"model": models["XGBoost"], "features": FEATURES},
                OUT / "xgboost_model.joblib")
    print(f"\n  Best model: {best} -- classification report (2024):")
    print(classification_report(yte, preds[best], target_names=CLASSES))

    print("\n[HMM temporal layer -- all cells, full period]")
    hmm_res = hmm_layer(df)

    # targets check
    tgt = {
        "macro_f1>=0.75": any(res[m]["macro_f1"] >= 0.75 for m in ["RandomForest", "XGBoost"]),
        "high_recall>=0.80": any(res[m]["high_recall"] >= 0.80 for m in ["RandomForest", "XGBoost"]),
        "spatial_agreement>=0.70": any(res[m]["spatial_agreement_high_in_zone"] >= 0.70
                                       for m in ["RandomForest", "XGBoost"]),
    }
    summary = {"dataset": {"rows": len(df), "cells": int(df["grid_id"].nunique()),
                           "days": int(df["date"].nunique()),
                           "period": "2018-2024", "test_period": "2024"},
               "data_sources": {"rainfall": "Open-Meteo ERA5 (real)",
                                "elevation": "Open-Meteo/SRTM (real)",
                                "rivers_roads_buildings": "OpenStreetMap Overpass (real)",
                                "flood_polygon": "terrain-hydrology susceptibility proxy"},
               "supervised_results": res, "hmm": hmm_res, "targets_met": tgt}
    (OUT / "results_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    print("\n" + "="*70)
    print("TARGETS:", json.dumps(tgt))
    board = sorted(res.items(), key=lambda kv: kv[1]["macro_f1"], reverse=True)
    print("\nLEADERBOARD (macro-F1, 2024 hold-out):")
    for n, r in board:
        print(f"  {n:18s} {r['macro_f1']:.3f}   HighRecall={r['high_recall']:.3f}")
    print("\nArtifacts ->", OUT)


if __name__ == "__main__":
    main()
