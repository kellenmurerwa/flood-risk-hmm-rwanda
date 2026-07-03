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
    # Read only the columns the pipeline uses (features + label + keys). On a
    # 1.86M-row table this trims hundreds of MB from peak RAM, which matters for
    # the RandomForest fit on memory-constrained machines. No effect on results.
    cols = FEATURES + ["flood_pressure_state", "date", "grid_id"]
    df = pd.read_parquet(ROOT / "real_flood_dataset.parquet", columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    df["y"] = df["flood_pressure_state"].map(C2I)
    return df


# Three-way TEMPORAL split (no shuffling -- respects time ordering so we never
# train on the future). Train fits parameters, validation is the held-out year
# used to sanity-check generalisation / catch over-fitting, and 2024 is the final
# untouched test year reported as the headline result.
SPLIT_PROTOCOL = {
    "type": "temporal (chronological, no shuffle)",
    "train": "2018-2022 (fit model parameters)",
    "validation": "2023 (held-out year: generalisation / over-fit check)",
    "test": "2024 (final untouched hold-out: headline metrics)",
    "note": ("Cells are NOT split across sets -- every grid cell appears in all "
             "three periods; only the time axis is partitioned, which is the "
             "correct protocol for a temporal forecasting task."),
}


def temporal_split(df):
    tr = df[df["date"].dt.year <= 2022].copy()
    va = df[df["date"].dt.year == 2023].copy()
    te = df[df["date"].dt.year == 2024].copy()
    print(f"[split] train {len(tr)} rows (2018-2022) | "
          f"val {len(va)} rows (2023) | test {len(te)} rows (2024)")
    return tr, va, te


def thr_baseline(df, lo, hi):
    r = df["rainfall_3d_mm"]
    return np.where(r <= lo, 0, np.where(r <= hi, 1, 2))


def _metrics(y, p):
    return {
        "macro_f1": float(f1_score(y, p, average="macro")),
        "accuracy": float(accuracy_score(y, p)),
        "high_recall": float(recall_score(y, p, labels=[2], average="macro")),
    }


def supervised(tr, va, te):
    Xtr, ytr = tr[FEATURES].values, tr["y"].values
    Xva, yva = va[FEATURES].values, va["y"].values
    Xte, yte = te[FEATURES].values, te["y"].values
    models = {
        "LogisticRegression": make_pipeline(StandardScaler(),
            LogisticRegression(max_iter=2000)),
        "DecisionTree": DecisionTreeClassifier(max_depth=8, random_state=42),
        # max_leaf_nodes hard-bounds the forest size (~0.2 GB for 300 trees) so
        # the whole pipeline trains in RAM on an 8 GB laptop without leaning on
        # the pagefile -- unbounded trees on 1.3M rows grow a multi-GB forest that
        # OOMs on modest machines. This trades a small amount of accuracy for
        # robust, laptop-reproducible training (a deliberate engineering choice).
        # n_jobs is capped (not -1) for the same peak-RAM reason.
        "RandomForest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
            max_leaf_nodes=4096, random_state=42, n_jobs=2),
        "XGBoost": xgb.XGBClassifier(n_estimators=400, max_depth=5,
            learning_rate=0.07, subsample=0.9, colsample_bytree=0.9,
            tree_method="hist", objective="multi:softprob", num_class=3,
            eval_metric="mlogloss", random_state=42, n_jobs=2),
    }
    res, preds = {}, {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        ptr, pva, pte = m.predict(Xtr), m.predict(Xva), m.predict(Xte)
        preds[name] = pte                      # test preds used downstream
        # Top-level keys stay the TEST metrics (headline / backward compatible);
        # `splits` adds the per-split (train/validation/test) breakdown the
        # supervisor asked for -- so over-fitting is visible as a train>>test gap.
        res[name] = dict(_metrics(yte, pte))
        res[name]["splits"] = {"train": _metrics(ytr, ptr),
                               "validation": _metrics(yva, pva),
                               "test": _metrics(yte, pte)}
        s = res[name]["splits"]
        print(f"  {name:18s} macroF1 train={s['train']['macro_f1']:.3f} "
              f"val={s['validation']['macro_f1']:.3f} test={s['test']['macro_f1']:.3f} "
              f"| HighRecall(test)={res[name]['high_recall']:.3f}")

    # baselines (thresholds learned on TRAIN rainfall terciles, then applied
    # unchanged to every split so the comparison is honest)
    lo, hi = tr["rainfall_3d_mm"].quantile([1/3, 2/3])
    baseline_preds = {
        "RainfallThreshold": {"train": thr_baseline(tr, lo, hi),
                              "validation": thr_baseline(va, lo, hi),
                              "test": thr_baseline(te, lo, hi)},
        "StaticPolygon": {
            "train": np.where(tr["flood_polygon_intersection"] == 1, 2, 0),
            "validation": np.where(va["flood_polygon_intersection"] == 1, 2, 0),
            "test": np.where(te["flood_polygon_intersection"] == 1, 2, 0)},
    }
    ys = {"train": ytr, "validation": yva, "test": yte}
    for b, sp in baseline_preds.items():
        res[b] = dict(_metrics(yte, sp["test"]))
        res[b]["splits"] = {k: _metrics(ys[k], sp[k]) for k in ys}
        print(f"  {b:18s} macroF1(test)={res[b]['macro_f1']:.3f} "
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
    tr, va, te = temporal_split(df)

    print("\n[Supervised -- temporal split (train 2018-2022, val 2023, test 2024)]")
    models, res, preds, yte = supervised(tr, va, te)

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
    # The flood_polygon feature is upgraded from the terrain-hydrology proxy to
    # the official MOE polygons once add_official_polygons.py has run (its cached
    # GeoJSON is then present). Label the source accordingly so the metadata
    # matches the data actually in the parquet.
    poly_src = ("Rwanda GeoPortal / MOE official flood-risk polygons (real)"
                if (ROOT / "data_cache" / "official_flood_polygons.geojson").exists()
                else "terrain-hydrology susceptibility proxy")
    summary = {"dataset": {"rows": len(df), "cells": int(df["grid_id"].nunique()),
                           "days": int(df["date"].nunique()),
                           "period": "2018-2024", "test_period": "2024",
                           "train_rows": len(tr), "validation_rows": len(va),
                           "test_rows": len(te)},
               "split_protocol": SPLIT_PROTOCOL,
               "data_sources": {"rainfall": "Open-Meteo ERA5 (real)",
                                "elevation": "Open-Meteo/SRTM (real)",
                                "rivers_roads_buildings": "OpenStreetMap Overpass (real)",
                                "flood_polygon": poly_src},
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
