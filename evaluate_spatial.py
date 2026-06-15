"""
Post-hoc spatial validation against the OFFICIAL Rwanda flood polygons, and a
flood-pressure risk map. Loads the trained XGBoost model (no retraining) and
evaluates the 2024 hold-out.

Reports, beyond the raw "share of predicted-High cells inside official polygons"
(which is capped by the polygons covering only ~19% of the corridor):
  * enrichment / lift  = P(official zone | predicted High) / P(official zone)
  * official-zone High-rate vs outside-zone High-rate
  * a per-cell predicted-High-frequency map with official polygons overlaid.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
OUT = ROOT / "model_outputs_real"
CLASSES = ["Low", "Moderate", "High"]

df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
df["date"] = pd.to_datetime(df["date"])
bundle = joblib.load(OUT / "xgboost_model.joblib")
model, feat = bundle["model"], bundle["features"]

te = df[df["date"].dt.year == 2024].copy()
te["pred"] = model.predict(te[feat].values)
te["is_high"] = (te["pred"] == 2).astype(int)
zone = te["flood_polygon_intersection"].values

base_zone = float(zone.mean())                       # P(official zone)
agree = float(zone[te["is_high"] == 1].mean())       # P(zone | High)
lift = agree / base_zone if base_zone else float("nan")
high_rate_in = float(te.loc[zone == 1, "is_high"].mean())
high_rate_out = float(te.loc[zone == 0, "is_high"].mean())

print(f"official-zone base rate         : {base_zone:.3f}")
print(f"P(zone | predicted High)        : {agree:.3f}")
print(f"enrichment / lift               : {lift:.2f}x")
print(f"High-rate inside official zone  : {high_rate_in:.3f}")
print(f"High-rate outside official zone : {high_rate_out:.3f}")
print(f"inside/outside High odds ratio  : {high_rate_in/high_rate_out:.2f}x")

# ---- per-cell predicted-High frequency map ----
cell = (te.groupby("grid_id")
        .agg(lat=("centroid_lat", "first"), lon=("centroid_lon", "first"),
             high_freq=("is_high", "mean"),
             official=("flood_polygon_intersection", "first")).reset_index())

fig, ax = plt.subplots(figsize=(7, 6))
sc = ax.scatter(cell["lon"], cell["lat"], c=cell["high_freq"], cmap="Reds",
                s=60, marker="s", edgecolors="none")
# outline official-zone cells
off = cell[cell["official"] == 1]
ax.scatter(off["lon"], off["lat"], facecolors="none", edgecolors="blue",
           s=70, marker="s", linewidths=0.8, label="official flood polygon cell")
plt.colorbar(sc, label="Predicted-High frequency (2024)")
ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
ax.set_title("Flood-pressure risk map (2024)\nred = High-pressure frequency · "
             "blue outline = official flood zone")
ax.legend(loc="upper right", fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "flood_pressure_risk_map.png", dpi=140)
plt.close(fig)
print("Saved flood_pressure_risk_map.png")

# ---- fold richer spatial metrics into the summary ----
sp = OUT / "results_summary.json"
summary = json.loads(sp.read_text()) if sp.exists() else {}
summary["spatial_validation"] = {
    "official_zone_base_rate": base_zone,
    "share_predicted_high_in_official_zone": agree,
    "enrichment_lift": lift,
    "high_rate_inside_zone": high_rate_in,
    "high_rate_outside_zone": high_rate_out,
    "inside_outside_odds_ratio": high_rate_in / high_rate_out,
    "interpretation": ("Official national polygons cover only ~19% of the "
                       "corridor; predicted-High pressure is enriched in the "
                       "official zone but extends beyond it, reflecting the "
                       "dynamic rainfall-driven footprint the static map omits."),
}
sp.write_text(json.dumps(summary, indent=2, default=str))
print("Updated results_summary.json with spatial_validation block.")
