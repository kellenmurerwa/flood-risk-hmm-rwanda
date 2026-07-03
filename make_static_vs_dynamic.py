"""
Static official flood zones (fixed) vs. the model's dynamic, rainfall-driven
flood-pressure footprint — the core 'ML gap' visual for slide 2.

Saves: model_outputs_real/static_vs_dynamic.png
"""
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).parent
OUT = ROOT / "model_outputs_real"
CLASSES = ["Low", "Moderate", "High"]
COL = {"Low": "#2ca25f", "Moderate": "#feb24c", "High": "#de2d26"}

df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
df["date"] = pd.to_datetime(df["date"])
b = joblib.load(OUT / "xgboost_model.joblib")
model, feat = b["model"], b["features"]

# one representative wet day in the hold-out
te = df[df["date"].dt.year == 2024].copy()
wet = te.groupby(te["date"].dt.date)["rainfall_3d_mm"].mean().idxmax()
day = te[te["date"].dt.date == wet].copy()
day["pred"] = [CLASSES[i] for i in model.predict(day[feat].values)]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 5.2))

# LEFT — static official zones (same every day)
inzone = day["flood_polygon_intersection"] == 1
axL.scatter(day.loc[~inzone, "centroid_lon"], day.loc[~inzone, "centroid_lat"],
            c="#d9d9d9", s=34, marker="s", label="outside official zone")
axL.scatter(day.loc[inzone, "centroid_lon"], day.loc[inzone, "centroid_lat"],
            c="#1f6fb2", s=34, marker="s", label="official flood zone")
axL.set_title("STATIC official hazard map\n(~19% of corridor · never changes)",
              fontsize=12, fontweight="bold")
axL.legend(loc="lower left", fontsize=8, framealpha=0.9)

# RIGHT — dynamic predicted flood-pressure for the wet day
for st in CLASSES:
    s = day[day["pred"] == st]
    axR.scatter(s["centroid_lon"], s["centroid_lat"], c=COL[st], s=34, marker="s",
                label=f"{st} ({len(s)})")
# outline the official zone for reference
axR.scatter(day.loc[inzone, "centroid_lon"], day.loc[inzone, "centroid_lat"],
            facecolors="none", edgecolors="#1f6fb2", s=46, marker="s",
            linewidths=0.7, label="official zone outline")
axR.set_title(f"DYNAMIC predicted flood-pressure\n(wet day {wet} · rainfall-driven)",
              fontsize=12, fontweight="bold")
axR.legend(loc="lower left", fontsize=7, framealpha=0.9, ncol=1)

for ax in (axL, axR):
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_xlim(day["centroid_lon"].min() - 0.005, day["centroid_lon"].max() + 0.005)
    ax.set_ylim(day["centroid_lat"].min() - 0.005, day["centroid_lat"].max() + 0.005)

fig.suptitle("The gap: a fixed map vs. a time-aware, data-driven risk view",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(OUT / "static_vs_dynamic.png", dpi=140)
print(f"Saved {OUT / 'static_vs_dynamic.png'} (day={wet})")
