"""Build a step-by-step PRODUCT DEMO video (.mp4) of the Kigali Flood-Pressure
dashboard. Reference only (not a submission artifact).

Each 'step' is a 16:9 frame: a navy title bar (STEP N), a main panel (a
data-driven reproduction of the real dashboard panel, or a real model figure),
and a caption band with DO / SEE / SAY guidance. Frames are held for a readable
duration and encoded to ~8 minutes via the bundled ffmpeg.

Run:  python demo_reference/build_product_demo.py  ->  demo_reference/Product_Demo.mp4
"""
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import imageio_ffmpeg

HERE = Path(__file__).parent
ROOT = HERE.parent
FIG = ROOT / "model_outputs_real"
FRAMES = HERE / "product_frames"
FRAMES.mkdir(exist_ok=True)

NAVY = "#123A5E"; GREEN = "#2ca25f"; ORANGE = "#feb24c"; RED = "#de2d26"
GREY = "#444444"; STEPCOL = "#9ec5e8"
CLASSES = ["Low", "Moderate", "High"]
COLORS = {"Low": GREEN, "Moderate": ORANGE, "High": RED}

print("loading data + model ...")
df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
df["date"] = pd.to_datetime(df["date"])
b = joblib.load(FIG / "xgboost_model.joblib")
model, feat = b["model"], b["features"]

te = df[df["date"].dt.year == 2024].copy()
te["pred_i"] = model.predict(te[feat].values)
te["pred"] = [CLASSES[i] for i in te["pred_i"]]

# choose a DRY day (fewest High) and a WET day (most High) in 2024
by_day = te.groupby(te["date"].dt.date)
high_per_day = by_day["pred_i"].apply(lambda v: int((v == 2).sum()))
dry_date = high_per_day.idxmin(); wet_date = high_per_day.idxmax()
# a balanced day for the first, clean map view
balanced = by_day["pred_i"].apply(lambda v: np.bincount(v, minlength=3).min() / len(v)).idxmax()

# an inspected High cell on the wet day, with the richest history
wetday = te[te["date"].dt.date == wet_date]
gid = wetday.sort_values("rainfall_3d_mm", ascending=False)["grid_id"].iloc[0]
cellrow = wetday[wetday["grid_id"] == gid].iloc[0]
proba = model.predict_proba(cellrow[feat].values.reshape(1, -1))[0]

# per-cell transition matrix
sfull = (df[df["grid_id"] == gid].sort_values("date")["flood_pressure_state"]
         .map({"Low": 0, "Moderate": 1, "High": 2}).values)
tc = np.zeros((3, 3))
for a_, b_ in zip(sfull[:-1], sfull[1:]):
    tc[a_, b_] += 1
Pmat = np.where(tc.sum(1, keepdims=True) > 0, tc / tc.sum(1, keepdims=True), np.nan)

steps = []  # (png_path, duration_seconds)


def new_frame(step, title):
    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor("white")
    bar = fig.add_axes([0, 0.88, 1, 0.12]); bar.axis("off")
    bar.add_patch(plt.Rectangle((0, 0), 1, 1, color=NAVY))
    if step:
        bar.text(0.015, 0.68, step, fontsize=15, color=STEPCOL, fontweight="bold", va="center")
    bar.text(0.015, 0.30 if step else 0.5, title, fontsize=25, color="white",
             fontweight="bold", va="center")
    return fig


def caption(fig, do=None, see=None, say=None):
    ax = fig.add_axes([0, 0, 1, 0.17]); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, color="#eef2f6"))
    y = 0.80
    for tag, txt, col in [("DO", do, NAVY), ("SEE", see, "#7a5b00"), ("SAY", say, GREEN)]:
        if txt:
            ax.text(0.015, y, f"{tag}:", fontsize=13.5, color=col, fontweight="bold", va="top")
            ax.text(0.075, y, txt, fontsize=13.5, color="#222222", va="top", wrap=True)
            y -= 0.30
    return ax


def content_ax(fig, rect=(0.06, 0.20, 0.88, 0.64)):
    return fig.add_axes(rect)


def save(fig, name, dur):
    p = FRAMES / name
    fig.savefig(p, dpi=100, facecolor="white")
    plt.close(fig)
    steps.append((p, dur))


def draw_map(ax, day_df, title):
    for st in CLASSES:
        s = day_df[day_df["pred"] == st]
        ax.scatter(s["centroid_lon"], s["centroid_lat"], c=COLORS[st], s=34,
                   marker="s", label=f"{st} ({len(s)})")
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.legend(title="Predicted state", fontsize=9, loc="upper right")


def show_img(ax, name):
    f = FIG / name
    if f.exists():
        ax.imshow(plt.imread(f)); ax.axis("off")
    else:
        ax.text(0.5, 0.5, f"[{name} not found]", ha="center"); ax.axis("off")


# ------------------------------------------------------------------ FRAMES ---
# 1 Title
fig = new_frame("", "Kigali Flood-Pressure Dashboard — Product Demo")
ax = content_ax(fig); ax.axis("off")
ax.text(0.5, 0.72, "A step-by-step tour of the deployed Streamlit app",
        ha="center", fontsize=20, color=GREY)
ax.text(0.5, 0.54, "Nyabugogo–Nyabarongo corridor · 729 cells · 250 m grid · 2018–2024",
        ha="center", fontsize=15, color=GREY)
ax.text(0.5, 0.34, "Kellen Murerwa  ·  Supervisor: Emmanuel Adjei  ·  ALU",
        ha="center", fontsize=14, color=NAVY, fontweight="bold")
caption(fig, say="This is decision-support: it estimates daily flood-PRESSURE — a Low/Moderate/High "
                 "risk state per cell. It is NOT a confirmed flood event.")
save(fig, "f01.png", 7)

# 2 Launch
fig = new_frame("STEP 1", "Launch the app")
ax = content_ax(fig); ax.axis("off")
ax.add_patch(plt.Rectangle((0.05, 0.35), 0.9, 0.45, color="#0f1620"))
ax.text(0.08, 0.70, "> cd  <final repo folder>", fontsize=17, color="#7CFC7C", family="monospace")
ax.text(0.08, 0.58, "> streamlit run dashboard.py", fontsize=17, color="#7CFC7C", family="monospace")
ax.text(0.08, 0.46, "  Local URL:  http://localhost:8501", fontsize=15, color="#cccccc", family="monospace")
ax.text(0.5, 0.22, "A browser tab opens automatically at localhost:8501.",
        ha="center", fontsize=14, color=GREY)
caption(fig, do="Run from the REPO ROOT (where dashboard.py lives), not from inside 'Capstone final project/'.",
        say="Have this open BEFORE the panel joins so you don't wait for it to boot.")
save(fig, "f02.png", 16)

# 3 Layout overview
fig = new_frame("STEP 2", "The layout — three areas")
ax = content_ax(fig); ax.axis("off")
rows = [("① Sidebar (left)", "date slider · polygon overlay toggle · map-colour mode"),
        ("② Map + metrics (centre)", "the 729-cell risk map and the top-line numbers"),
        ("③ Cell inspector & model panel (below)", "drill into one cell · transition matrix · performance")]
for i, (h, d) in enumerate(rows):
    y = 0.78 - i * 0.24
    ax.text(0.06, y, h, fontsize=19, color=NAVY, fontweight="bold")
    ax.text(0.09, y - 0.09, d, fontsize=15, color=GREY)
caption(fig, do="Scroll top-to-bottom: controls → map → inspector → model panel.",
        say="I'll walk through each area in the order you'd present it.")
save(fig, "f03.png", 18)

# 4 Map — read it
fig = new_frame("STEP 3", "The risk map — how to read it")
draw_map(content_ax(fig), te[te["date"].dt.date == balanced], f"Predicted flood-pressure — {balanced}")
caption(fig, see="Each square is one 250 m cell. Green = Low, orange = Moderate, red = High pressure.",
        say="This is the model's prediction for the selected day, across all 729 cells.")
save(fig, "f04.png", 22)

# 5 Dry day
fig = new_frame("STEP 4", "Move the date slider — a DRY day")
draw_map(content_ax(fig), te[te["date"].dt.date == dry_date], f"Dry day — {dry_date}")
caption(fig, do="Drag the sidebar date slider to a low-rainfall day.",
        see="Almost all cells are green/orange — little High pressure.",
        say="On a dry day the corridor sits at Low-to-Moderate pressure.")
save(fig, "f05.png", 22)

# 6 Wet day
fig = new_frame("STEP 5", "Move the slider — a WET day (the key moment)")
draw_map(content_ax(fig), wetday, f"Wet day — {wet_date}")
caption(fig, do="Now drag to a high-rainfall day.",
        see="The red High-pressure zone GROWS along the low-lying river corridor.",
        say="This is the whole point — a static map can't do this. Our map is DYNAMIC; it responds to rainfall.")
save(fig, "f06.png", 26)

# 7 Colour modes
fig = new_frame("STEP 6", "Map-colour modes (sidebar radio)")
gs = fig.add_gridspec(1, 3, left=0.04, right=0.97, top=0.82, bottom=0.22, wspace=0.25)
axa = fig.add_subplot(gs[0]); draw_map(axa, wetday, "Predicted state"); axa.legend().remove()
axb = fig.add_subplot(gs[1])
lab = wetday.copy(); lab["pred"] = lab["flood_pressure_state"]
for st in CLASSES:
    s = lab[lab["pred"] == st]; axb.scatter(s["centroid_lon"], s["centroid_lat"], c=COLORS[st], s=22, marker="s")
axb.set_title("Label state", fontsize=12); axb.set_xlabel("Lon")
axc = fig.add_subplot(gs[2])
r = wetday["rainfall_3d_mm"]; nrm = (r - r.min()) / (r.max() - r.min() + 1e-9)
axc.scatter(wetday["centroid_lon"], wetday["centroid_lat"], c=nrm, cmap="YlGnBu", s=22, marker="s")
axc.set_title("Rainfall (3-day)", fontsize=12); axc.set_xlabel("Lon")
caption(fig, do="Switch the 'Map colour' radio between the three modes.",
        say="Predicted vs the ground-truth label vs the rainfall driver — so you can see rain and risk line up.")
save(fig, "f07.png", 22)

# 8 Polygon overlay
fig = new_frame("STEP 7", "Overlay the official flood polygons")
ax = content_ax(fig)
draw_map(ax, wetday, f"Predicted High vs official zone — {wet_date}")
ax.text(0.02, 0.02, "(In the app the official MOE polygon is drawn as a blue outline.)",
        transform=ax.transAxes, fontsize=10, color="#2b5fb0")
caption(fig, do="Tick 'Overlay official flood polygons'.",
        say="Our red cells cluster inside AND around the official zone — the model re-discovers it "
            "WITHOUT training on it, then extends the footprint. That's the core contribution.")
save(fig, "f08.png", 24)

# 9 Metrics
fig = new_frame("STEP 8", "Top metric strip")
ax = content_ax(fig); ax.axis("off")
n_high = int((wetday["pred"] == "High").sum())
mets = [("Cells", "729"), ("Predicted High", str(n_high)),
        ("Mean 3-day rain", f"{wetday['rainfall_3d_mm'].mean():.1f} mm"),
        ("Macro-F1 (2024 test)", "0.813")]
for i, (k, v) in enumerate(mets):
    x = 0.06 + (i % 2) * 0.47; y = 0.60 - (i // 2) * 0.38
    ax.text(x, y + 0.12, v, fontsize=34, fontweight="bold", color=NAVY)
    ax.text(x, y, k, fontsize=15, color=GREY)
caption(fig, see="Cells (729) · Predicted High (moves with the date) · Mean 3-day rain · headline accuracy.",
        say="Macro-F1 0.813 on the held-out 2024 year — above our 0.75 target.")
save(fig, "f09.png", 18)

# 10 Cell inspector — probabilities + features
fig = new_frame("STEP 9", f"Cell inspector — pick a cell (here {gid})")
gs = fig.add_gridspec(1, 2, left=0.06, right=0.96, top=0.82, bottom=0.22, wspace=0.3)
axp = fig.add_subplot(gs[0])
axp.barh(CLASSES, proba, color=[COLORS[c] for c in CLASSES])
axp.set_xlim(0, 1); axp.set_title("Class probabilities", fontsize=13)
for i, p in enumerate(proba):
    axp.text(p + 0.02, i, f"{p:.2f}", va="center", fontsize=12)
axt = fig.add_subplot(gs[1]); axt.axis("off")
show = ["rainfall_3d_mm", "rainfall_7d_mm", "elevation_m", "slope_deg",
        "distance_to_river_m", "building_density_count_per_km2"]
axt.text(0.0, 0.95, "Feature values (this cell):", fontsize=13, fontweight="bold")
for i, fn in enumerate(show):
    axt.text(0.02, 0.80 - i * 0.13, f"{fn}", fontsize=12, color=GREY)
    axt.text(0.75, 0.80 - i * 0.13, f"{cellrow[fn]:.1f}", fontsize=12, fontweight="bold")
caption(fig, do="Open the 'Grid cell' dropdown and pick a red (High) cell.",
        see="A full probability across the 3 states — not just a label — plus the 10 input features.",
        say="Calibrated probability is what makes it decision-support: act on '80% High' differently than '51%'.")
save(fig, "f10.png", 25)

# 11 Cell time series
fig = new_frame("STEP 10", f"Cell rainfall dynamics — {gid} (2024)")
ax = content_ax(fig)
series = df[df["grid_id"] == gid].set_index("date").loc["2024"]
for w, lw in [("rainfall_1d_mm", 0.7), ("rainfall_3d_mm", 1.0), ("rainfall_7d_mm", 1.0), ("rainfall_14d_mm", 1.0)]:
    ax.plot(series.index, series[w], lw=lw, label=w.replace("rainfall_", "").replace("_mm", ""))
ax.set_ylabel("mm"); ax.legend(ncol=4, fontsize=10); ax.set_title("Multi-window rainfall accumulation", fontsize=12)
caption(fig, see="1-, 3-, 7- and 14-day rainfall for this cell, with its flood-pressure state below (in the app).",
        say="Pressure rises AFTER sustained rain, not instantly — longer windows drive sustained High states.")
save(fig, "f11.png", 22)

# 12 Per-cell transition matrix (HEADLINE)
fig = new_frame("STEP 11  ★", f"Per-cell Markov transition matrix — {gid}")
gs = fig.add_gridspec(1, 2, left=0.06, right=0.96, top=0.82, bottom=0.22, wspace=0.25, width_ratios=[1, 1])
axh = fig.add_subplot(gs[0])
axh.imshow(np.nan_to_num(Pmat), cmap="Purples", vmin=0, vmax=1)
axh.set_xticks(range(3)); axh.set_yticks(range(3))
axh.set_xticklabels(CLASSES); axh.set_yticklabels(CLASSES)
axh.set_xlabel("state tomorrow"); axh.set_ylabel("state today")
axh.set_title("P(state tomorrow | state today)", fontsize=12)
for i in range(3):
    for j in range(3):
        v = Pmat[i, j]
        axh.text(j, i, "—" if np.isnan(v) else f"{v:.2f}", ha="center", va="center",
                 color="white" if (not np.isnan(v) and v > 0.5) else "black", fontsize=13)
axr = fig.add_subplot(gs[1]); axr.axis("off")
axr.text(0.0, 0.9, "Read it in words:", fontsize=14, fontweight="bold")
lines = []
for i, c in enumerate(CLASSES):
    if np.isnan(Pmat[i]).all():
        lines.append(f"• From {c}: not observed for this cell.")
    else:
        stay = Pmat[i, i]
        lines.append(f"• From {c}: {stay*100:.0f}% stay {c}")
for k, ln in enumerate(lines):
    axr.text(0.0, 0.72 - k * 0.16, ln, fontsize=13, color="#222")
axr.text(0.0, 0.12, "Strong diagonal = pressure PERSISTS.\nOff-diagonal = how a cell escalates.",
         fontsize=12, color=GREY)
caption(fig, do="Scroll to 'Markov state-transition matrix'.",
        say="THE contribution: not just what state today, but what state TOMORROW — for THIS cell, from its own history. "
            "A snapshot becomes a short-horizon forecast a manager can act on.")
save(fig, "f12.png", 30)

# 13 Splits
fig = new_frame("STEP 12", "Model panel — how the data is split")
ax = content_ax(fig); ax.axis("off")
tbl = [["Split", "Period", "Rows", "Purpose"],
       ["Train", "2018–2022", "1,331,154", "fit parameters"],
       ["Validation", "2023", "266,085", "over-fit check"],
       ["Test", "2024", "266,814", "final hold-out"]]
t = ax.table(cellText=tbl, loc="center", cellLoc="left", bbox=[0.02, 0.25, 0.96, 0.6])
t.auto_set_font_size(False); t.set_fontsize(15)
for j in range(4):
    t[0, j].set_facecolor(NAVY); t[0, j].get_text().set_color("white"); t[0, j].get_text().set_fontweight("bold")
caption(fig, say="Temporal split, NO shuffle: train on the past, validate on 2023, test on the untouched 2024. "
                 "A random split would leak future weather into training.")
save(fig, "f13.png", 22)

# 14 Per-split F1 (no over-fit)
fig = new_frame("STEP 13", "No over-fitting — macro-F1 by split")
ax = content_ax(fig); ax.axis("off")
tbl = [["Model", "Train", "Validation", "Test"],
       ["XGBoost (deployed)", "0.804", "0.805", "0.813"],
       ["Random Forest", "0.813", "0.806", "0.813"],
       ["Logistic Regression", "0.732", "0.740", "0.750"]]
t = ax.table(cellText=tbl, loc="center", cellLoc="center", bbox=[0.05, 0.3, 0.9, 0.5])
t.auto_set_font_size(False); t.set_fontsize(15)
for j in range(4):
    t[0, j].set_facecolor(NAVY); t[0, j].get_text().set_color("white"); t[0, j].get_text().set_fontweight("bold")
caption(fig, say="Train ≈ validation ≈ test for every model — the model GENERALISES to years it never saw. "
                 "This is the exact question a supervisor asks.")
save(fig, "f14.png", 24)

# 15 Confusion
fig = new_frame("STEP 14", "Confusion matrix (2024 test)")
show_img(content_ax(fig, (0.30, 0.20, 0.40, 0.64)), "confusion_XGBoost.png")
caption(fig, see="Rows = true class, columns = predicted; the diagonal is correct.",
        say="Strong Low and High detection; error concentrates on the transitional Moderate class — "
            "off by one band, not a wild miss. We optimised High-recall: a missed High day costs more than a false alarm.")
save(fig, "f15.png", 24)

# 16 Feature importance
fig = new_frame("STEP 15", "Feature importance")
show_img(content_ax(fig, (0.22, 0.20, 0.56, 0.64)), "xgb_feature_importance.png")
caption(fig, say="Rainfall accumulation (3- and 7-day) dominates, then elevation and distance-to-river — "
                 "exactly the physics of urban flooding. The sanity check that it learned hydrology, not noise.")
save(fig, "f16.png", 18)

# 17 SHAP
fig = new_frame("STEP 16", "SHAP explainability")
show_img(content_ax(fig, (0.24, 0.20, 0.52, 0.64)), "shap_summary.png")
caption(fig, say="SHAP explains individual predictions per-feature — it makes the model auditable, not a black box. "
                 "That's our interpretability/accountability evidence.")
save(fig, "f17.png", 18)

# 18 Global HMM
fig = new_frame("STEP 17", "Global HMM transition matrix")
show_img(content_ax(fig, (0.31, 0.20, 0.38, 0.64)), "hmm_transition_matrix.png")
caption(fig, see="Self-transitions ≈ 0.83 / 0.80 / 0.91 (Low/Mod/High); next-step accuracy 0.45 (chance 0.33).",
        say="The corridor-wide view of persistence — the population version of the per-cell matrix. "
            "Honest framing: the HMM is explanatory; the supervised model is the predictor.")
save(fig, "f18.png", 22)

# 19 Spatial validation
fig = new_frame("STEP 18", "Spatial validation vs the official map")
ax = content_ax(fig); ax.axis("off")
for i, (k, v, c) in enumerate([("Enrichment / lift", "1.60×", GREEN),
                               ("Inside/outside High odds", "1.85×", GREEN),
                               ("Official-zone coverage", "~19%", GREY),
                               ("Raw containment", "0.30", GREY)]):
    x = 0.06 + (i % 2) * 0.47; y = 0.62 - (i // 2) * 0.34
    ax.text(x, y + 0.12, v, fontsize=32, fontweight="bold", color=c)
    ax.text(x, y, k, fontsize=15, color=GREY)
caption(fig, say="The official layer covers only 19%, so a '70% inside' target is geometrically impossible without "
                 "circular labels. Reframed to enrichment (1.60×) and odds (1.85×) — High pressure is far denser inside the zone.")
save(fig, "f19.png", 24)

# 20 Leaderboard
fig = new_frame("STEP 19", "Results leaderboard")
ax = content_ax(fig); ax.axis("off")
tbl = [["Model", "Macro-F1", "High-recall"],
       ["XGBoost (deployed, best)", "0.813", "0.843"],
       ["Random Forest", "0.813", "0.849"],
       ["Logistic Regression", "0.750", "0.819"],
       ["Decision Tree", "0.750", "0.798"],
       ["Rainfall-threshold (baseline)", "0.626", "0.902"],
       ["Static-polygon (baseline)", "0.324", "0.292"]]
t = ax.table(cellText=tbl, loc="center", cellLoc="center", bbox=[0.08, 0.15, 0.84, 0.78])
t.auto_set_font_size(False); t.set_fontsize(14)
for j in range(3):
    t[0, j].set_facecolor(NAVY); t[0, j].get_text().set_color("white"); t[0, j].get_text().set_fontweight("bold")
for i in (1, 2):
    for j in range(3):
        t[i, j].set_facecolor("#E5F0E9")
caption(fig, say="XGBoost and RF both hit 0.813; XGBoost ships. Both baselines are clearly beaten — "
                 "rainfall rule 0.626, static map 0.324 — which proves the geospatial ML adds real value.")
save(fig, "f20.png", 25)

# 21 Recap
fig = new_frame("", "Recap — what you just showed")
ax = content_ax(fig); ax.axis("off")
pts = ["Dynamic risk map that changes with rainfall (not a static hazard map)",
       "Per-cell probabilities + inputs → decision-support, not a black box",
       "Per-cell Markov transitions → snapshot becomes a forecast",
       "Train ≈ val ≈ test → generalises, no over-fitting (0.813)",
       "Agrees with the official map (1.85× odds) AND extends it",
       "Reproducible end-to-end; 10/10 tests pass; p95 latency 9.6 ms"]
for i, p in enumerate(pts):
    ax.text(0.06, 0.80 - i * 0.13, "✓ " + p, fontsize=16, color="#222")
caption(fig, say="A reproducible, interpretable, time-aware flood-pressure tool for Kigali — "
                 "beats the baselines, agrees with and extends the official map, runs as a live dashboard.")
save(fig, "f21.png", 20)

# 22 Close
fig = new_frame("", "Thank you — questions welcome")
ax = content_ax(fig); ax.axis("off")
ax.text(0.5, 0.55, "Everything reruns from a single  main.py.", ha="center", fontsize=20, color=NAVY)
ax.text(0.5, 0.38, "Pair this video with DEMO_WALKTHROUGH.md for the full narration + Q&A.",
        ha="center", fontsize=14, color=GREY)
caption(fig, say="Close on reproducibility — it's your strongest, most defensible claim.")
save(fig, "f22.png", 8)

# ------------------------------------------------------------- encode mp4 ---
total = sum(d for _, d in steps)
print(f"{len(steps)} frames, {total}s (~{total/60:.1f} min). encoding ...")
listfile = FRAMES / "concat.txt"
with open(listfile, "w") as fh:
    for p, d in steps:
        fh.write(f"file '{p.as_posix()}'\nduration {d}\n")
    fh.write(f"file '{steps[-1][0].as_posix()}'\n")   # concat quirk: repeat last

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
out = HERE / "Product_Demo.mp4"
cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
       "-vf", "format=yuv420p", "-c:v", "libx264", "-r", "30",
       "-movflags", "+faststart", str(out)]
subprocess.run(cmd, check=True, capture_output=True)
print(f"Saved {out}  ({total//60}m {total%60}s)")
