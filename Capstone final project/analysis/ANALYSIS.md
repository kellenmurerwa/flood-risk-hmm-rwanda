# Analysis of Results — Achievement of Project Objectives

**Project:** Geospatial Flood-Risk Modelling using Climate Data and Hidden Markov Models in Rwanda
**Study area:** Nyabugogo–Nyabarongo / Mpazi corridor, Kigali · 729-cell, 250 m grid · 2018–2024
**Evaluation protocol:** temporal split (no shuffle) — **train 2018–2022**, **validation 2023**, test on the unseen **2024** year
**Author:** Kellen Murerwa · **Supervisor:** Emmanuel Adjei

All figures below are reproduced live by the test suite in `../tests/` (see
`../testing_results/`) from `model_outputs_real/results_summary.json`. This is an
analysis *against the proposal objectives*, not a bare list of findings.

---

## 1. Scorecard against the SMART objectives

| # | Objective (proposal §1.3.1) | Quantified target | Result (2024 hold-out) | Status |
|---|------------------------------|-------------------|------------------------|--------|
| 1 | Define corridor + build 250 m grid; acquire & preprocess rainfall, SRTM, OSM, official polygons (2018–24) | Reproducible grid, real data | 729 cells × 2 557 days = **1.86 M cell-days**, all real/keyless sources | ✅ Met |
| 2 | Engineer rainfall-accumulation (1/3/7/14-day) + static geospatial features into a reproducible cell-by-day table | 10-feature modelling table | `real_flood_dataset.parquet`, **0 NaNs** in model features (test-verified) | ✅ Met |
| 3 | Benchmark ≥3 supervised models vs rainfall-threshold & static-polygon baselines | **macro-F1 ≥ 0.75** and **high-recall ≥ 0.80** | XGBoost **0.813 / 0.843**; RF **0.813 / 0.849** | ✅ Met |
| 4 | Integrate HMM; evaluate next-step accuracy + spatial concordance with official polygons | **enrichment lift ≥ 1.4** and **inside/outside odds ≥ 1.5** | lift **1.60×**, odds **1.85×**; HMM next-step acc 0.445 | ✅ Met (spatial) / ⚠️ partial (HMM) |
| 5 | Produce risk maps + reproducible dashboard + report/defence | Working deliverables | risk map, **Streamlit dashboard**, report, defence deck all shipped | ✅ Met |

**Headline:** 4 of 5 objectives fully met; Objective 4 is met on its two stated
spatial targets but only *partially* on the HMM temporal component (analysed in §4).

---

## 2. Objective 3 — supervised classification (the core ML claim)

| Model | Macro-F1 | Accuracy | High-recall | Verdict |
|---|---|---|---|---|
| **XGBoost (+SHAP)** | **0.813** | 0.833 | 0.843 | Best & **deployed**; explainable |
| Random Forest | 0.813 | 0.834 | **0.849** | Ties on F1; best recall |
| Decision Tree | 0.750 | 0.780 | 0.798 | Just clears F1 bar |
| Logistic Regression | 0.750 | 0.781 | 0.819 | Linear baseline |
| Rainfall-threshold baseline | 0.626 | 0.657 | 0.902 | High recall, poor precision |
| Static-polygon baseline | 0.324 | 0.508 | 0.292 | Confirms static maps are inadequate |

**How the target was achieved.** Both ensemble models clear the macro-F1 ≥ 0.75
and high-recall ≥ 0.80 bars on the *temporal* test year — the honest test, because
2024 is never seen in training or validation. The best model improves macro-F1 by
**+0.19 absolute (+30%)** over the rainfall-threshold baseline and by **+0.49**
over the static-polygon map. This directly answers Research Question 3: a
geospatial ML classifier separates Low/Moderate/High pressure far better than
either rule-based baseline.

**Generalisation — the train/validation/test evidence.** The data is split
chronologically: parameters are fit on **2018–2022**, 2023 is held out as a
**validation** year to check for over-fitting, and 2024 is the final untouched
**test** year. Macro-F1 barely moves across the three splits (XGBoost 0.804 /
0.805 / 0.813; RF 0.813 / 0.806 / 0.813), so the models are **not over-fitting** —
performance on unseen future years matches the training fit. Every grid cell
appears in all three periods; only the time axis is partitioned, which is the
correct protocol for a forecasting task (a random shuffle would leak future
weather into training). The per-split table is reproduced live on the dashboard.

**Why this matters for the use-case.** High-pressure **recall** (0.84–0.85) was
weighted above precision in the proposal because a missed high-pressure day is
costlier than a false alarm. The model recovers ~84% of true high-pressure
cell-days, while the static map recovers only ~29%.

**Honest caveat.** The `demo_data_values` functional test shows the model
saturates quickly — moderate multi-day rain on low ground already yields
P(High) ≈ 0.99. The decision boundary is sharp, which favours recall but means
the "Moderate" band is comparatively narrow; this is a known sensitivity, noted
for future calibration (see Recommendations).

---

## 3. Objective 4a — spatial concordance with official polygons (**met**)

| Spatial metric | Target | Result |
|---|---|---|
| Enrichment / lift = P(official zone \| predicted-High) / P(official zone) | ≥ 1.4 | **1.60×** ✅ |
| Inside-vs-outside High odds ratio | ≥ 1.5 | **1.85×** ✅ |
| Raw containment (share of predicted-High inside official zone) | — | 0.30 |

The official Ministry-of-Environment polygons cover only **~19%** of the corridor.
Raw containment is therefore *capped low by construction* — a model that flagged
risk **only** inside the static polygons could not exceed that footprint and would
simply reproduce the map it is meant to improve on. The proposal anticipated this
and set **enrichment** and **odds-ratio** as the real targets. Both are met: the
model concentrates High-pressure predictions **1.85× more densely inside** the
official zones than outside, while still capturing the broader, **rainfall-driven
footprint** the static map omits. This answers Research Question 5: predicted
high-pressure cells align with official zones *and* extend beyond them in a
hydrologically sensible way.

> The earlier ad-hoc check `spatial_agreement>=0.70` (raw containment) is reported
> as **not met** in `results_summary.json`. That is expected and not a project
> failure: it measures containment, which the 19% polygon coverage makes
> unreachable, and it is *not* the proposal's stated target. The stated targets
> (lift, odds ratio) are the correct yardstick, and both pass.

---

## 4. Objective 4b — HMM temporal layer (**partially met**)

| HMM metric | Result |
|---|---|
| Decoded-state accuracy | 0.450 |
| Next-step (1-day-ahead) accuracy | 0.445 |
| Daily self-persistence (diagonal of transition matrix) | Low **0.83**, Moderate **0.80**, High **0.91** |

The HMM was successfully integrated and **does** characterise the temporal
structure: the transition matrix shows flood-pressure states are highly
persistent day-to-day (High→High = 0.91), and transitions are near-tridiagonal —
states move to neighbours (Low↔Moderate↔High), rarely jumping Low→High. This
answers Research Question 4 qualitatively.

However, next-step accuracy (0.445) is **well below** the supervised classifiers.
Interpretation: with only three coarse daily states and strong persistence, the
unsupervised HMM cannot match a feature-rich supervised model that sees the actual
rainfall accumulation. **The supervised RF/XGBoost layer is the operational
predictor; the HMM is best read as a descriptive temporal-smoothing/explanatory
layer, not the primary forecaster.** This is the one place the result is more
modest than the proposal's framing implied, and it is reported transparently.

---

## 5. Non-functional objective — latency (**met, with large margin**)

The proposal set a 2-second response budget. Benchmarked on a 12-core host
(`../testing_results/test_output_performance.txt`):

- A **single live query** (one date = 729 cells): **p95 ≈ 9.6 ms** — ~200× inside budget.
- Even on **1 thread** (constrained hardware): p95 ≈ 49 ms — still ~40× inside budget.
- Bulk back-testing throughput: ~120k–135k cell-predictions/sec.

Latency is comfortably met across every hardware/software configuration tested,
so the dashboard's interactivity is not a risk at pilot scale.

---

## 6. Where results met vs. missed the objectives — summary

- **Met and exceeded:** data pipeline, feature engineering, supervised
  classification accuracy and recall, spatial enrichment/odds-ratio, latency,
  and all delivered artefacts (maps, dashboard, report, defence).
- **Partially met:** the HMM temporal layer — integrated and informative, but its
  predictive accuracy trails the supervised models and it should be positioned as
  explanatory rather than as the forecaster.
- **Deliberately not chased:** raw polygon containment, which the 19% official
  coverage makes structurally unreachable and which is not the stated target.

The project therefore achieves its central thesis — **open climate + geospatial
data plus ensemble ML can produce a time-aware, decision-support view of urban
flood pressure that beats both rule-based and static-map baselines** — while being
candid about the limits of the HMM component.
