"""
Animated GIF of the PRODUCT WORKING: the trained model's predicted daily
flood-pressure map evolving over a real wet spell in the 2024 hold-out.
This is genuine model output (not a screen recording), suitable to embed in a
slide or play in the talk.

Output: flood_pressure_animation.gif
Run:    python make_product_animation.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Patch

ROOT = Path(__file__).parent
OUT = ROOT / "model_outputs_real"
CLASSES = ["Low", "Moderate", "High"]
COL = {"Low": "#2ca25f", "Moderate": "#feb24c", "High": "#de2d26"}

df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
df["date"] = pd.to_datetime(df["date"])
b = joblib.load(OUT / "xgboost_model.joblib")
model, feat = b["model"], b["features"]

# choose the wettest ~24-day window in 2024 so the animation shows risk build-up
te = df[df["date"].dt.year == 2024].copy()
daily_rain = te.groupby(te["date"].dt.normalize())["rainfall_3d_mm"].mean()
peak = daily_rain.rolling(24).mean().idxmax()
start = peak - pd.Timedelta(days=23)
window = pd.date_range(start, peak, freq="D")
te = te[te["date"].isin(window)].copy()
te["pred_i"] = model.predict(te[feat].values)

days = sorted(te["date"].unique())
lon = te.groupby("grid_id")["centroid_lon"].first()
lat = te.groupby("grid_id")["centroid_lat"].first()
gids = lon.index.tolist()

fig, (ax, axb) = plt.subplots(1, 2, figsize=(11, 5.6),
                              gridspec_kw={"width_ratios": [3, 1]})
fig.suptitle("Predicted daily flood-pressure — Kigali corridor (2024 wet spell)",
             fontsize=13, fontweight="bold")
sc = ax.scatter(lon.values, lat.values, s=30, marker="s",
                c=["#cccccc"] * len(gids))
ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
ax.legend(handles=[Patch(color=COL[c], label=c) for c in CLASSES],
          loc="lower left", fontsize=8, framealpha=0.9)
title = ax.set_title("")
bars = axb.bar(CLASSES, [0, 0, 0], color=[COL[c] for c in CLASSES])
axb.set_ylim(0, len(gids)); axb.set_ylabel("cells"); axb.set_title("State counts")


def frame(k):
    d = days[k]
    day = te[te["date"] == d].set_index("grid_id").loc[gids]
    colors = [COL[CLASSES[i]] for i in day["pred_i"].values]
    sc.set_color(colors)
    counts = [int((day["pred_i"] == i).sum()) for i in range(3)]
    for bar, h in zip(bars, counts):
        bar.set_height(h)
    rain = day["rainfall_3d_mm"].mean()
    title.set_text(f"{pd.Timestamp(d).date()}   ·   mean 3-day rain {rain:.0f} mm   ·   "
                   f"High cells {counts[2]}")
    return [sc, title, *bars]


anim = FuncAnimation(fig, frame, frames=len(days), interval=600, blit=False)
fig.tight_layout(rect=[0, 0, 1, 0.95])
path = ROOT / "flood_pressure_animation.gif"
anim.save(str(path), writer=PillowWriter(fps=2))
plt.close(fig)
print(f"Saved {path}  ({len(days)} frames, {window[0].date()}..{window[-1].date()})")
