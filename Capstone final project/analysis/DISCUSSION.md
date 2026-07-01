# Discussion — Importance of the Milestones and Impact of the Results

**Project:** Geospatial Flood-Risk Modelling using Climate Data and Hidden Markov Models in Rwanda
**Author:** Kellen Murerwa · **Supervisor:** Emmanuel Adjei · ALU BSc Software Engineering

This discussion was developed with the supervisor and reads the results in
context: *why each milestone mattered* and *what the outcomes mean* for research,
for the city, and for affected communities.

---

## 1. Why the milestones mattered

**Milestone 1 — a real, reproducible data pipeline (not a toy dataset).**
The single most important methodological decision was to drop the original
synthetic spreadsheet and rebuild the dataset from **real, free, keyless**
sources: Open-Meteo ERA5 rainfall, SRTM elevation, OpenStreetMap exposure, and
the official Rwanda GeoPortal flood polygons. This matters because the project's
whole claim is that *open data is sufficient in a data-scarce setting*. A result
on synthetic data would have proved nothing; a result on 1.86 million real
cell-days is evidence. The pipeline is cached and re-runnable offline, so the
finding is **reproducible** — the core requirement of the design-science method
adopted in the proposal.

**Milestone 2 — feature engineering that encodes flood physics.**
Turning raw rainfall into 1/3/7/14-day accumulations, and terrain into slope,
distance-to-river and exposure densities, is what lets a generic classifier learn
flood behaviour. The milestone mattered because it is the bridge between "data we
can get" and "signal a model can use" — and the SHAP analysis confirms the
engineered rainfall-accumulation features dominate the prediction, which is
hydrologically credible.

**Milestone 3 — benchmarking against honest baselines.**
Comparing RF/XGBoost not just to each other but to a **rainfall-threshold rule**
and the **static official map** was essential. Without baselines, a macro-F1 of
0.83 is just a number. Against them, it is a *claim with evidence*: the ML layer
adds +33% over the rule and +0.51 F1 over the static map. The milestone converts
"the model works" into "the model is worth building instead of using what already
exists."

**Milestone 4 — temporal modelling and spatial validation.**
The HMM and the polygon validation milestone forced the project to confront two
hard questions: *does flood pressure have learnable day-to-day structure?* (yes —
strong persistence) and *does the model agree with the authoritative map?*
(yes — 1.85× inside/outside odds inside official zones). This is the milestone that makes
the output **trustworthy to a disaster manager**, because it ties model output to
the reference they already use.

**Milestone 5 — a usable artefact (the dashboard).**
A model in a notebook helps no one. The Streamlit dashboard milestone turns the
predictions into something a non-modeller can interrogate by date and location.
It is the difference between a research result and a **decision-support tool**.

---

## 2. Impact of the results

**Research / software-engineering impact.**
The project contributes a reproducible integration of supervised geospatial ML
*with* a Hidden Markov temporal layer for an African urban catchment — an
under-explored pairing. The candid finding that the HMM **underperforms** the
supervised models as a forecaster is itself a useful contribution: it tells future
researchers to use Markov structure for *smoothing and explanation*, not as the
primary predictor on coarse daily states.

**Impact for the city and disaster managers.**
The results move the conversation from a **static hazard map** (which covers ~19%
of the corridor and never changes) to a **time-aware view** of where flood
pressure is building after heavy rain. Because the model captures a broader
rainfall-driven footprint while still concentrating risk inside the official
zones, it can help prioritise drainage inspection and community alerts in the days
following storms — exactly the operational gap the proposal identified.

**Impact for affected communities.**
Positioned honestly as a **screening / decision-support** tool — not a confirmed
flood forecast and not a replacement for official early warning — the framework
offers a transparent, data-grounded signal of *when and where* pressure is rising.
The sub-10-ms query latency means such a signal could realistically be served
interactively or pushed as a daily summary at near-zero marginal cost.

---

## 3. Threats to validity (discussed honestly with the supervisor)

- **Label provenance.** Flood-pressure labels are a *derived* construct
  (rainfall trigger × terrain susceptibility + a drainage latent and noise), not
  confirmed flood events. Care was taken to keep the labelling non-circular, but
  the absence of a ground-truth incident register is the project's main limitation.
- **Single corridor / single test year.** Results use one catchment with a
  chronological split — a 2023 validation year and an untouched 2024 test year.
  Generalisation to other Kigali catchments or further years is plausible but unproven.
- **Model sharpness.** The decision boundary saturates fast (P(High)→1 under
  modest sustained rain), which boosts recall but compresses the Moderate band and
  may over-warn in borderline conditions.

These do not undermine the central result, but they bound the claims and set the
agenda in the Recommendations.

---

## 4. Milestone-to-impact, in one line

Each milestone removed a specific reason to *not* trust the output — synthetic
data, no baseline, no reference-map agreement, no usable interface — and the
cumulative result is a reproducible, validated, interactive flood-pressure
screening tool that demonstrably beats the status-quo map for the Kigali corridor.
