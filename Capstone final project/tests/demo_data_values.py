"""
Testing strategy 2 of 3 -- FUNCTIONALITY WITH DIFFERENT DATA VALUES.

This script feeds the deployed XGBoost flood-pressure model a battery of
hand-crafted scenarios that sweep the key drivers (rainfall, elevation,
distance-to-river, urban density). It prints the predicted Low/Moderate/High
state and the class probabilities for each, demonstrating that the product
responds sensibly to changing inputs (e.g. heavy multi-day rain on a low-lying
riverside cell -> High; a dry spell on high ground -> Low).

A bar-chart screenshot of the scenario probabilities is saved to
testing_results/screenshots/demo_data_values.png.

Run:  python "tests/demo_data_values.py"
"""
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model_outputs_real"
SHOTS = ROOT / "testing_results" / "screenshots"
CLASSES = ["Low", "Moderate", "High"]
FEATURES = ["rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_14d_mm",
            "elevation_m", "slope_deg", "distance_to_river_m",
            "road_density_km_per_km2", "building_density_count_per_km2",
            "flood_polygon_intersection"]

bundle = joblib.load(OUT / "xgboost_model.joblib")
model, feat = bundle["model"], bundle["features"]

# Scenario name -> feature dict (values within the real corridor's observed range)
SCENARIOS = {
    "Dry spell, high ground, far from river": dict(
        rainfall_1d_mm=0, rainfall_3d_mm=1, rainfall_7d_mm=3, rainfall_14d_mm=8,
        elevation_m=1560, slope_deg=9, distance_to_river_m=1400,
        road_density_km_per_km2=2, building_density_count_per_km2=20,
        flood_polygon_intersection=0),
    "Moderate rain, mid slope, suburban": dict(
        rainfall_1d_mm=18, rainfall_3d_mm=34, rainfall_7d_mm=55, rainfall_14d_mm=80,
        elevation_m=1465, slope_deg=4, distance_to_river_m=600,
        road_density_km_per_km2=8, building_density_count_per_km2=120,
        flood_polygon_intersection=0),
    "Heavy 3-day rain, low-lying riverside, dense urban": dict(
        rainfall_1d_mm=42, rainfall_3d_mm=88, rainfall_7d_mm=120, rainfall_14d_mm=160,
        elevation_m=1380, slope_deg=1, distance_to_river_m=60,
        road_density_km_per_km2=14, building_density_count_per_km2=320,
        flood_polygon_intersection=1),
    "Extreme rain, valley floor, in official flood zone": dict(
        rainfall_1d_mm=70, rainfall_3d_mm=140, rainfall_7d_mm=190, rainfall_14d_mm=240,
        elevation_m=1372, slope_deg=0.5, distance_to_river_m=20,
        road_density_km_per_km2=16, building_density_count_per_km2=400,
        flood_polygon_intersection=1),
}


def predict_row(d):
    X = np.array([[d[f] for f in feat]])
    i = int(model.predict(X)[0])
    p = model.predict_proba(X)[0]
    return CLASSES[i], p


def main():
    rows, probs = [], []
    print("=" * 78)
    print("FUNCTIONAL TEST -- prediction under different data values")
    print("=" * 78)
    for name, d in SCENARIOS.items():
        state, p = predict_row(d)
        probs.append(p)
        rows.append(name)
        print(f"\nScenario: {name}")
        print(f"  rain(1/3/7/14d)={d['rainfall_1d_mm']}/{d['rainfall_3d_mm']}/"
              f"{d['rainfall_7d_mm']}/{d['rainfall_14d_mm']} mm  "
              f"elev={d['elevation_m']} m  dist_river={d['distance_to_river_m']} m  "
              f"official_zone={d['flood_polygon_intersection']}")
        print(f"  --> PREDICTED: {state}   "
              f"P(Low/Mod/High)={p[0]:.2f}/{p[1]:.2f}/{p[2]:.2f}")

    # monotonicity sanity check: rising rainfall should not lower P(High)
    # (allow tiny float noise once probabilities saturate near 1.0)
    p_high = [float(p[2]) for p in probs]
    print("\nMonotonicity check P(High) across rising-rainfall scenarios:",
          [round(x, 3) for x in p_high])
    drops = [p_high[i + 1] - p_high[i] for i in range(len(p_high) - 1)]
    assert min(drops) >= -1e-3, "P(High) should be non-decreasing with rainfall"
    print("PASS: P(High) is non-decreasing as rainfall/exposure increase "
          "(tolerance 1e-3 at saturation).")

    # ---- screenshot ----
    probs = np.array(probs)
    x = np.arange(len(rows))
    w = 0.25
    colors = {"Low": "#2ca25f", "Moderate": "#feb24c", "High": "#de2d26"}
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for k, c in enumerate(CLASSES):
        ax.bar(x + (k - 1) * w, probs[:, k], w, label=c, color=colors[c])
    ax.set_xticks(x)
    ax.set_xticklabels([r.replace(", ", ",\n") for r in rows], fontsize=8)
    ax.set_ylabel("Predicted probability")
    ax.set_ylim(0, 1)
    ax.set_title("Functional test: flood-pressure prediction vs different data values")
    ax.legend(title="State")
    fig.tight_layout()
    SHOTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(SHOTS / "demo_data_values.png", dpi=140)
    print(f"\nSaved screenshot -> {SHOTS / 'demo_data_values.png'}")


if __name__ == "__main__":
    main()
