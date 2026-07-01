# Capstone — Final Version of the Product/Solution

### Geospatial Flood-Risk Modelling using Climate Data and Hidden Markov Models in Rwanda
**Nyabugogo–Nyabarongo / Mpazi corridor, Kigali** · BSc Software Engineering, African Leadership University
**Author:** Kellen Murerwa  ·  **Supervisor:** Emmanuel Adjei

A reproducible machine-learning + Hidden Markov Model system that estimates daily
**Low / Moderate / High flood-pressure states** over a 729-cell, 250 m grid by
fusing real rainfall, terrain, hydrology and urban-exposure data, validates the
result against the official Ministry-of-Environment flood polygons, and serves it
through an interactive Streamlit dashboard.

> A *flood-pressure state* is a **derived risk condition** (rainfall + terrain +
> exposure), **not** a confirmed flood event. This is a decision-support /
> screening tool that complements — not replaces — official early-warning systems.

---

## 📦 What this submission folder contains

| Path | Purpose | Rubric criterion |
|---|---|---|
| [`testing_results/TESTING_RESULTS.md`](testing_results/TESTING_RESULTS.md) | All test runs + demo screenshots | **Testing Results (5 pts)** |
| [`testing_results/screenshots/`](testing_results/screenshots/) | Demo & model figures (PNG) | Testing Results |
| [`testing_results/*.txt`](testing_results/) | Raw captured test output | Testing Results |
| [`analysis/ANALYSIS.md`](analysis/ANALYSIS.md) | Results vs. proposal objectives | **Analysis (2 pts)** |
| [`analysis/DISCUSSION.md`](analysis/DISCUSSION.md) | Milestone importance + impact | Discussion |
| [`analysis/RECOMMENDATIONS.md`](analysis/RECOMMENDATIONS.md) | Community guidance + future work | Recommendations |
| [`deployment/`](deployment/) | Dockerfile, Streamlit/Render config, deploy guide | **Deployment (3 pts)** |
| [`tests/`](tests/) | The test scripts (re-runnable) | Testing Results |

The application source (`dashboard.py`, `main.py`, the pipeline modules) lives in
the **repository root**, one level up; this folder is the graded submission
package built on top of it.

---

## ▶️ How to install and run the app (step by step)

**Prerequisites:** Python 3.11+ and Git, on Windows/macOS/Linux.

```bash
# 1. Clone and enter the repo
git clone <your-repo-url>
cd "Draft-Captone Proposal Kellen"

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Build the dataset + train the models (fetches real, free, keyless data;
#    cached in data_cache/ so re-runs are fast and offline). ~ a few minutes.
python main.py all                # build -> train -> evaluate
#    (skip step 4 if real_flood_dataset.parquet and model_outputs_real/ already exist)

# 5. Launch the dashboard
python main.py dashboard          # or: streamlit run dashboard.py
#    open the printed URL, e.g. http://localhost:8501
```

**Run the tests / regenerate the screenshots** (from the repo root):

```bash
python -m pytest "Capstone final project/tests/test_pipeline.py" -v
python "Capstone final project/tests/demo_data_values.py"
python "Capstone final project/tests/benchmark_performance.py"
python "Capstone final project/tests/make_dashboard_preview.py"
```

---

## 🗂️ Related files (in the repository root)

| File | Purpose |
|---|---|
| `main.py` | Pipeline orchestrator / CLI entry point |
| `build_real_dataset.py` | Fetch real data, engineer features, build labels → `real_flood_dataset.parquet` |
| `add_official_polygons.py` | Official MOE flood-polygon integration |
| `train_real.py` | Train baselines + RF + XGBoost + HMM; train/val/test temporal split; SHAP |
| `evaluate_spatial.py` | Spatial validation (enrichment, odds ratio) + risk map |
| `dashboard.py` | **The deployed Streamlit app** |
| `model_outputs_real/` | Trained models, figures, `results_summary.json` |
| `requirements.txt` | Python dependencies (also copied into this folder) |
| `Flood_Risk_HMM_Capstone_Proposal.docx/.pdf` | The written proposal |

---

## 🎥 5-minute demo video

> **TODO (you record this):** a ≤5-minute screen recording that focuses on the
> **core functionality** — launching the dashboard, picking dates, reading the
> flood-pressure map, inspecting a cell's features/probabilities, and the
> performance/model panel. (No sign-up/sign-in to show — the app has none.)
> Suggested beats: (1) `python main.py dashboard`, (2) move the date slider on a
> wet vs. dry day, (3) toggle the official-polygon overlay, (4) inspect a High
> cell, (5) open the "Model performance & HMM" expander.

**Video link:** _paste your unlisted YouTube / Google Drive link here_

---

## 🌐 Live deployment

> **TODO (you deploy this):** follow [`deployment/DEPLOYMENT.md`](deployment/DEPLOYMENT.md)
> — recommended path is **Streamlit Community Cloud** (free, no card). The app has
> been verified to boot headless and serve HTTP 200 locally
> ([`testing_results/deploy_local_boot.log`](testing_results/deploy_local_boot.log));
> deployment artifacts (Dockerfile, `render.yaml`, `Procfile`, `.streamlit/config.toml`)
> are ready in [`deployment/`](deployment/).

**Deployed URL:** _paste your `https://<app>.streamlit.app` (or Render) link here_

---

## ✅ Results at a glance (2024 test hold-out)

Temporal split: **train 2018–2022 · validation 2023 · test 2024**.

| Model | Macro-F1 | High-recall | Note |
|---|---|---|---|
| **XGBoost (+SHAP)** | **0.813** | 0.843 | best & deployed — meets F1≥0.75 & recall≥0.80 |
| Random Forest | 0.813 | **0.849** | ties on F1, best High-recall |
| Rainfall-threshold baseline | 0.626 | — | beaten by +0.19 F1 |
| Static-polygon baseline | 0.324 | — | beaten by +0.49 F1 |

Train/validation/test macro-F1 track closely (XGBoost 0.804 / 0.805 / 0.813;
RF 0.813 / 0.806 / 0.813) — no over-fitting; the model generalises across years.
Spatial validation vs official polygons: **enrichment 1.60×** (target ≥1.4 ✅),
inside/outside High odds **1.85×** (target ≥1.5 ✅). Live query latency **p95 ≈
9.6 ms** vs the 2 s budget ✅. Full breakdown in
[`analysis/ANALYSIS.md`](analysis/ANALYSIS.md).

---

## 📜 Data & attribution

Rainfall & elevation © Open-Meteo (ERA5/Copernicus; SRTM/NASA). Map data ©
OpenStreetMap contributors (ODbL). Flood polygons © Rwanda GeoPortal / Ministry
of Environment. All sources are free and keyless.
