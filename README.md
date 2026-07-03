# Geospatial Flood-Risk Modelling using Climate Data and Hidden Markov Models in Rwanda

**Capstone project — BSc Software Engineering, African Leadership University**
Author: Kellen Murerwa · Supervisor: Emmanuel Adjei

A reproducible machine-learning + Hidden Markov Model framework that estimates
**daily Low / Moderate / High flood-pressure states** for the **Nyabugogo–Nyabarongo
corridor in Kigali, Rwanda**, by fusing real rainfall, terrain, hydrology and
urban-exposure data, and validates the result against the official flood-risk
polygons.

---

## What it does

1. Builds a **250 m grid** over the study corridor (729 cells).
2. Pulls **real, free, keyless data** per cell-day, 2018–2024:
   - **Rainfall** (1/3/7/14-day totals) — Open-Meteo **ERA5** archive
   - **Elevation + slope** — Open-Meteo **SRTM** elevation
   - **Distance-to-river, road & building density** — **OpenStreetMap** (Overpass)
   - **Official flood-risk polygons** — Rwanda GeoPortal / **geodata.rw** (Ministry of Environment)
3. Derives **flood-pressure labels** (rainfall trigger × terrain susceptibility, with
   an unobserved drainage latent + noise so the task is not trivially circular).
4. Trains and benchmarks: rainfall-threshold & static-polygon baselines, Logistic
   Regression, Decision Tree, **Random Forest**, **XGBoost** (+ SHAP), and an
   **HMM** temporal layer — evaluated on a **temporal train/validation/test split**
   (train 2018–2022, validation 2023, test 2024).
5. Validates spatially against the official polygons and ships a **Streamlit dashboard**.

## Headline results (2024 test hold-out)

| Model | Macro-F1 | High-recall |
|---|---|---|
| XGBoost (deployed) | **0.813** | 0.843 |
| Random Forest | 0.813 | 0.849 |
| Rainfall-threshold baseline | 0.626 | — |
| Static-polygon baseline | 0.324 | — |

Train/validation/test macro-F1 are near-identical for both ensembles (XGBoost
0.804 / 0.805 / 0.813; RF 0.813 / 0.806 / 0.813) — no over-fitting. Spatial
validation vs official polygons: containment 0.30, **enrichment 1.60×**,
inside/outside High odds **1.85×** (model concentrates High-pressure in official
flood zones while capturing a broader rainfall-driven footprint).

---

## Quick start

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows (PowerShell: .venv\Scripts\Activate.ps1)

pip install -r requirements.txt            # runtime deps for the dashboard (slim, pinned)
python main.py dashboard                   # launch the Streamlit inspection app

pip install -r requirements-training.txt   # + build/train/analysis pipeline (adds shap, hmmlearn, ...)
python main.py all                         # build -> train -> evaluate  (fetches real data, ~minutes)
```

Individual stages: `python main.py build | polygons | train | evaluate | dashboard`.
API responses are cached in `data_cache/`, so re-runs are fast and offline-friendly.

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Pipeline orchestrator (CLI entry point) |
| `build_real_dataset.py` | Fetch real data, engineer features, build labels → `real_flood_dataset.parquet` |
| `add_official_polygons.py` | Stand-alone official-polygon integration / refresh |
| `train_real.py` | Train baselines + RF + XGBoost + HMM; temporal hold-out; SHAP |
| `evaluate_spatial.py` | Spatial validation (enrichment, odds ratio) + flood-pressure risk map |
| `dashboard.py` | Streamlit inspection dashboard (maps, per-cell inspector, metrics) |
| `model_outputs_real/` | Trained models, figures, `results_summary.json` |
| `Flood_Risk_HMM_Capstone_Proposal.docx/.pdf` | The written proposal |

## Data sources

All inputs are real and free; only OpenStreetMap requires a `User-Agent` header.
Endpoints below are the ones actually called in `build_real_dataset.py` and
`add_official_polygons.py` (verified live).

| # | Feature(s) it provides | Source | API / endpoint | Access · licence |
|---|---|---|---|---|
| 1 | `rainfall_1d/3d/7d/14d_mm` (daily totals → accumulation features) | Open-Meteo — ERA5 reanalysis | `https://archive-api.open-meteo.com/v1/archive` | Free, keyless · ERA5/Copernicus |
| 2 | `elevation_m`, derived `slope_deg` (terrain) | Open-Meteo — SRTM elevation | `https://api.open-meteo.com/v1/elevation` | Free, keyless · SRTM/NASA |
| 3 | `distance_to_river_m`, `road_density_km_per_km2`, `building_density_count_per_km2` (rivers, roads, buildings) | OpenStreetMap — Overpass API | `https://overpass.kumi.systems/api/interpreter` (any Overpass mirror works; mirrors rate-limit and need a `User-Agent`) | Free · ODbL |
| 4 | `flood_polygon_intersection` (+ spatial-validation reference) | Rwanda GeoPortal — Ministry of Environment | `https://geodata.rw/server/rest/services/basemap/Flood_Risk_Areas/FeatureServer/0` (query params must be URL-encoded) | Free · MOE |

> **Note on rainfall:** the proposal named Meteo Rwanda / CHIRPS; the implementation
> uses **Open-Meteo ERA5 reanalysis** because Meteo Rwanda offered no open, keyless
> access within the project window. ERA5 is real but reanalysis-grade (~9–31 km),
> so validation against Meteo Rwanda gauge records is future work.

## Data & ethics note

A *flood-pressure state* is a **derived risk condition** (rainfall + terrain + exposure),
**not a confirmed flood event**. The framework is a decision-support / risk-screening
tool that complements — and does not replace — official early-warning systems.
Official polygons: Rwanda GeoPortal (geodata.rw), source Ministry of Environment.

## License / attribution

Rainfall & elevation © Open-Meteo (ERA5, Copernicus; SRTM/NASA). Map data ©
OpenStreetMap contributors (ODbL). Flood polygons © Rwanda GeoPortal / MOE.
