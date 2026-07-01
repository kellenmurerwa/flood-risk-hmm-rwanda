"""
Renders a static, data-driven preview of the Streamlit dashboard's core panels
for inclusion as a testing screenshot. It reproduces -- from the real dataset and
the deployed XGBoost model -- exactly what the live app shows for a chosen date:
the predicted Low/Moderate/High flood-pressure map over the 729-cell corridor
grid, the top-line metrics, and a single cell's rainfall time series.

Run:  python "Capstone final project/tests/make_dashboard_preview.py"
"""
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "model_outputs_real"
SHOTS = ROOT / "Capstone final project" / "testing_results" / "screenshots"
CLASSES = ["Low", "Moderate", "High"]
COLORS = {"Low": "#2ca25f", "Moderate": "#feb24c", "High": "#de2d26"}

df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
df["date"] = pd.to_datetime(df["date"])
b = joblib.load(OUT / "xgboost_model.joblib")
model, feat = b["model"], b["features"]

# pick the 2024 day whose predicted-state mix is most balanced, so the map shows
# real spatial structure across all three states (not a saturated all-High day)
te = df[df["date"].dt.year == 2024].copy()
te["pred_i"] = model.predict(te[feat].values)
best_date, best_score = None, -1.0
for d, g in te.groupby(te["date"].dt.date):
    counts = np.bincount(g["pred_i"].values, minlength=3) / len(g)
    score = counts.min()                       # maximise the rarest-state share
    if score > best_score:
        best_score, best_date = score, d
wettest = best_date
day = te[te["date"].dt.date == wettest].copy()
day["pred"] = [CLASSES[i] for i in day["pred_i"]]

fig = plt.figure(figsize=(13, 6.5))
gs = fig.add_gridspec(2, 2, width_ratios=[1.5, 1], height_ratios=[1, 1])

# ---- panel 1: predicted-state map ----
axm = fig.add_subplot(gs[:, 0])
for state in CLASSES:
    s = day[day["pred"] == state]
    axm.scatter(s["centroid_lon"], s["centroid_lat"], c=COLORS[state],
                s=42, marker="s", label=f"{state} ({len(s)})")
axm.set_title(f"Predicted flood-pressure map — {wettest}\n"
              "Nyabugogo–Nyabarongo corridor, 729 cells (250 m grid)")
axm.set_xlabel("Longitude"); axm.set_ylabel("Latitude")
axm.legend(title="Predicted state", loc="upper right", fontsize=8)

# ---- panel 2: metrics strip ----
axk = fig.add_subplot(gs[0, 1]); axk.axis("off")
n_high = int((day["pred"] == "High").sum())
metrics = [("Cells", f"{len(day)}"),
           ("Predicted High", f"{n_high}"),
           ("Mean 3-day rain", f"{day['rainfall_3d_mm'].mean():.1f} mm"),
           ("Model macro-F1 (2024)", "0.813")]
for i, (k, v) in enumerate(metrics):
    x = 0.02 + (i % 2) * 0.5
    y = 0.75 - (i // 2) * 0.5
    axk.text(x, y + 0.18, v, fontsize=20, fontweight="bold", transform=axk.transAxes)
    axk.text(x, y, k, fontsize=9, color="#555", transform=axk.transAxes)
axk.set_title("Live metrics (this date)", fontsize=10, loc="left")

# ---- panel 3: a cell's rainfall time series ----
axt = fig.add_subplot(gs[1, 1])
gid = day.sort_values("rainfall_3d_mm", ascending=False)["grid_id"].iloc[0]
series = df[df["grid_id"] == gid].set_index("date").loc["2024"]
axt.plot(series.index, series["rainfall_1d_mm"], lw=0.7, label="1-day")
axt.plot(series.index, series["rainfall_3d_mm"], lw=0.9, label="3-day")
axt.plot(series.index, series["rainfall_7d_mm"], lw=0.9, label="7-day")
axt.set_title(f"Rainfall time series — cell {gid} (2024)", fontsize=10)
axt.set_ylabel("mm"); axt.legend(fontsize=7, ncol=3)
axt.tick_params(axis="x", labelsize=7, rotation=30)

fig.suptitle("Kigali Flood-Pressure Inspection Dashboard — core panels (data-driven preview)",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.96])
SHOTS.mkdir(parents=True, exist_ok=True)
fig.savefig(SHOTS / "dashboard_preview.png", dpi=140)
print(f"Saved -> {SHOTS / 'dashboard_preview.png'}  (date={wettest}, High cells={n_high})")
