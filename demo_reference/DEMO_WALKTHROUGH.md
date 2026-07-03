# Demo & Defense Walkthrough — Reference Script
### Kigali Flood-Pressure Dashboard · Kellen Murerwa
*Private reference — NOT part of the graded submission. Use it to rehearse the demo, learn how to explain every panel, and prepare for panel questions.*

---

## 0. Before you start (setup)

Run the app from the **repository root** (where `dashboard.py` lives), not from inside `Capstone final project/`:

```bash
cd "C:\Users\HP\Downloads\flood-risk-hmm-rwanda-final"   # or your final repo
streamlit run dashboard.py          # OR: python main.py dashboard
```

A browser tab opens at `http://localhost:8501`. Have this open **before** the panel joins so you don't waste demo time waiting for it to boot.

**The one-sentence framing (say this first, every time):**
> "This is a decision-support tool that estimates daily *flood-pressure* — a Low / Moderate / High risk state — for every 250 m cell in the Nyabugogo–Nyabarongo corridor of Kigali. Flood-pressure is a **derived risk condition**, not a confirmed flood event; it complements, not replaces, official early warning."

Memorise that distinction — it pre-empts the single most common challenge ("are you predicting real floods?").

---

## 1. Suggested ≤5-minute demo flow (timed)

| Time | Panel | One-liner to land |
|---|---|---|
| 0:00–0:30 | Title + framing | What flood-pressure is, and what it isn't |
| 0:30–1:30 | Map + date slider | The product: a live risk map that *changes with rainfall* |
| 1:30–2:15 | Top metrics + polygon overlay | It agrees with the official map **and** extends it |
| 2:15–3:15 | Cell inspector | Drill into one cell: features → probabilities → rainfall |
| 3:15–4:00 | **Per-cell transition matrix** | The Markov contribution: not just *what state*, but *what next* |
| 4:00–4:45 | Model & splits panel | Honest metrics, train/val/test, confusion, SHAP, HMM |
| 4:45–5:00 | Close | Reproducible, interpretable, beats baselines |

If you only have 3 minutes, cut the model panel to a single sentence and keep the map + cell inspector + transition matrix (that's the story that's *yours*).

---

## 2. Panel-by-panel — DO this, SAY this

### 2.1 Title bar & caption
**DO:** Point at the title and the caption line.
**SAY:** "The data behind every pixel is real and keyless — rainfall from Open-Meteo ERA5, terrain from SRTM, roads/rivers/buildings from OpenStreetMap, and the official flood polygons from the Rwanda GeoPortal. Nothing here is synthetic or assumed."

### 2.2 The map (main panel)
**DO:** Let the default date load. Point to the coloured grid.
**SAY:** "Each square is a 250 m cell — 729 of them. Green is Low pressure, orange Moderate, red High. This is the model's prediction for the selected day."

**DO:** Drag the **Date slider** (sidebar) from a dry day to a wet day.
**SAY:** "Watch what happens as I move to a high-rainfall day — the red High-pressure zone grows along the low-lying river corridor. This is the whole point: a *static* hazard map can't do this. Our map is **dynamic** — it responds to actual rainfall."

**DO:** Hover a red cell so the tooltip appears.
**SAY:** "Hovering shows the cell ID, the predicted class with the model's confidence, the 3-day rainfall, and the elevation — so every prediction is inspectable."

**DO:** Change the **Map colour** radio through its three modes.
**SAY:**
- *Predicted state* — "what the model thinks."
- *Label state* — "the ground-truth label we trained against, for visual comparison."
- *Rainfall (3-day)* — "the dominant driver, so you can see rain and risk line up."

### 2.3 Official-polygon overlay
**DO:** Toggle **"Overlay official flood polygons"** on.
**SAY:** "The blue outline is the government's official flood-risk zone. Notice our red cells cluster inside and around it — but also extend beyond it. The model **re-discovers the official zone without ever training on the polygon as a target**, and then adds the broader rainfall-driven footprint the static map misses. That agreement-plus-extension is the core contribution."

### 2.4 Top metric strip
**DO:** Read the four metrics left to right.
**SAY:**
- **Cells** — "729, the full grid."
- **Predicted High** — "how many cells are in High pressure *today* — this number moves with the date."
- **Mean 3-day rain** — "the rainfall context for this date."
- **Macro-F1 (2024 test)** — "0.813 — the model's headline accuracy on the held-out 2024 year, above our 0.75 target."

### 2.5 Cell inspector
**DO:** Open the **Grid cell** dropdown, pick a cell (ideally a red/High one).
**SAY (left side):** "For this cell the model outputs a full probability across the three states — not just a label. That calibrated probability is what makes it decision-support: an officer can act on '80% High' differently than '51% High'."
**DO:** Point at the **Features** table.
**SAY:** "These are the ten inputs for this cell — the four rainfall windows, elevation, slope, distance to river, road and building density, and the official-zone flag."
**DO:** Point at the **time series** (right).
**SAY:** "And here's the cell's rainfall history across 1-, 3-, 7- and 14-day windows, with its flood-pressure state below. You can see pressure rise *after* sustained rain, not instantly — that lag is real hydrology."

### 2.6 ⭐ Per-cell Markov transition matrix (the feature to emphasise)
> This is the panel that answers your supervisor's main request. Spend time here.

**DO:** Scroll to **"Markov state-transition matrix — for the selected cell."** Point at the 3×3 heatmap.
**SAY:** "Classification alone only tells you the state *today*. The core contribution is **temporal** — for this exact cell, given today's state, what's the probability of each state *tomorrow*? Read a row as 'from this state'; the columns are 'to that state tomorrow'."

**DO:** Point at the diagonal, then an off-diagonal cell.
**SAY:** "The strong diagonal means states **persist** — once a cell is High after heavy rain, it tends to stay High. The off-diagonal Low→Moderate→High entries are how a cell *escalates*. The plain-language read-out on the right says it in words: 'from Low, X% stay Low, Y% move to Moderate.' A dash means that cell never entered that state in 2018–2024, which we show honestly rather than faking a number."

**SAY (why it matters):** "For a disaster manager this is the difference between a snapshot and a forecast: not just 'this cell is High now' but 'this cell has an 80%+ chance of *staying* High tomorrow' — that's what drives a pre-positioning decision."

### 2.7 Model performance, data splits & HMM panel
**DO:** Expand **"Model performance, data splits & HMM transitions."**

**Split table — SAY:** "First, how the data is split — chronologically, no shuffling: train on 2018–2022, **validate on 2023**, and test on the untouched 2024. Every cell appears in all three periods; only time is partitioned. A random split would leak future weather into training — this is the honest protocol for forecasting."

**Per-split macro-F1 table — SAY:** "Here's each model's macro-F1 on train, validation and test. The key thing: they're almost identical — XGBoost is 0.804, 0.805, 0.813. Train ≈ validation ≈ test means **no over-fitting** — the model generalises to years it never saw."

**Confusion matrix image — SAY:** "The confusion matrix on the 2024 test year: strong Low and High detection down the diagonal; most of the error is Moderate cells predicted as neighbouring states — expected, because Moderate is the transitional class between two continuous extremes, not a wild miss."

**Feature importance — SAY:** "Rainfall accumulation — especially the 3- and 7-day windows — dominates, then elevation and distance-to-river. That's exactly the physics of urban flooding."

**SHAP summary — SAY:** "SHAP confirms it per-prediction and makes the model auditable rather than a black box — that satisfies our interpretability requirement."

**HMM transition matrix + next-step — SAY:** "This is the *global* HMM view: self-transition probabilities of about 0.83, 0.80 and 0.91 — strong persistence — and next-step accuracy of 0.45 over three states, well above the 0.33 you'd get by chance. Note we're honest that the HMM is the *explanatory* temporal layer; the supervised model is the predictor."

---

## 3. How to explain each graph/figure in depth

### 3.1 The predicted-state map
- **What it is:** 729 coloured points, one per cell, coloured by predicted Low/Moderate/High for the chosen day.
- **What to stress:** it's *dynamic* (changes with the date), *spatially structured* (red follows the low river corridor), and *inspectable* (hover + click).
- **Trap to avoid:** don't call red cells "floods." Call them "High flood-pressure."

### 3.2 Confusion matrix (2024 test)
- **How to read:** rows = true class, columns = predicted class; the diagonal is correct predictions.
- **Say:** "Low and High are recovered strongly; the confusions concentrate on Moderate, the in-between class. Because the cost of a missed High day is high, we deliberately optimised for **High recall** (0.84) — we'd rather over-warn than miss."
- **If pushed:** "This is a temporal test — 2024 was never seen — so these are generalisation numbers, not training accuracy."

### 3.3 Feature-importance bar chart
- **Say:** "Ranks the ten features by how much the model relies on them. Rainfall windows top the list, which is the sanity check that the model learned hydrology, not noise."

### 3.4 SHAP summary
- **Say:** "SHAP decomposes individual predictions into per-feature contributions. High rainfall pushes toward High pressure; high elevation pushes toward Low. It's the interpretability/accountability evidence — we can explain *why* any single cell was flagged."

### 3.5 HMM transition matrix (global)
- **Say:** "A Hidden Markov Model over the daily sequences. The matrix is P(state tomorrow | state today) averaged across the corridor. Strong diagonal = persistence; transitions only move between neighbouring states, never Low→High in one jump. It's the population-level version of the per-cell matrix in the inspector."

### 3.6 Per-cell transition matrix (inspector) — *your headline*
- Covered in 2.6. If asked how it differs from the global HMM: "The global HMM is one matrix for the whole corridor; this is estimated from **one cell's own history**, so it's location-specific — a low-lying cell escalates differently from a hilltop cell."

### 3.7 Risk map figure (flood_pressure_risk_map.png)
- **Say:** "This is the 2024 High-pressure *frequency* per cell with the official polygons overlaid — the static evidence behind the spatial-validation numbers."

### 3.8 The results / leaderboard table
- **Say, reading top to bottom:** "XGBoost — the deployed model — and Random Forest both hit 0.813 macro-F1; XGBoost is best by a hair and is the one we ship. Both clear the 0.75 and 0.80 targets. The two baselines — a rainfall-only rule at 0.626 and the static-polygon map at 0.324 — are clearly beaten, which is the proof that the geospatial ML *adds value* over what you could do without it."
- **The recall nuance (be ready):** "The rainfall baseline has high recall, 0.90 — but low precision; it flags High too often. Macro-F1 balances both, and that's where it collapses to 0.63."

### 3.9 Spatial-validation numbers
- **Say:** "Enrichment 1.60× and inside/outside odds 1.85×. The official layer covers only ~19% of the corridor, so a naive '70% of predictions inside the zone' target is geometrically impossible without making the labels circular. So we reframed to enrichment and odds ratio — both cleared."

---

## 4. Possible panel questions & how to answer them

**Q1. "Are you predicting actual floods?"**
> No — I predict *flood-pressure*, a derived risk state from rainfall, terrain and exposure. There's no open incident register for the corridor, so I'm honest that this is screening/decision-support that complements official early warning, not a confirmed-event predictor. Validating against real incidents (e.g. MINEMA records) is stated future work.

**Q2. "Isn't your label circular — you built it from rainfall and terrain, then predict it from rainfall and terrain?"**
> That's the risk, and I addressed it directly. The label includes an **unobserved drainage latent plus daily noise** that the model can't see. Without it, models hit 0.99 F1 — a warning sign, not a success. With it, performance drops to a realistic ~0.81, which is exactly what you'd expect from a genuine, non-trivial signal.

**Q3. "How did you split the data, and how do you know it isn't over-fitting?"** *(your supervisor's exact question)*
> A three-way **temporal** split with no shuffling: train 2018–2022, validate 2023, test 2024. I report macro-F1 on all three, and they track almost identically — XGBoost 0.804 / 0.805 / 0.813. If it were over-fitting, train would be far above test. It isn't, so it generalises across years. A random split would leak future weather backward and inflate the score.

**Q4. "Why XGBoost over Random Forest if they tie?"**
> They tie on macro-F1 at 0.813; XGBoost edges it and gives calibrated probabilities plus clean SHAP explanations, so it's the deployed model. Random Forest actually has slightly higher High-recall (0.849 vs 0.843), which I disclose — if a deployment weighted recall above all else, RF is a defensible swap.

**Q5. "Why ERA5 and not CHIRPS or Meteo Rwanda gauges?"**
> ERA5 is keyless, reproducible, and I verified it live. CHIRPS is scientifically ideal for Africa but I *tested* two access routes — the IRI Data Library and ClimateSERV — and both failed or timed out without heavy tooling, so I document it as a validation extension. Meteo Rwanda gauges are the gold standard but have no open API and need a formal data request.

**Q6. "Your spatial containment is only 0.30 — isn't that weak?"**
> Raw containment is capped by geometry: the official layer covers only 19% of the corridor, so a model can't put most of its High cells inside 19% of the area without ignoring the rest of the rainfall footprint. That's why I reframed to **enrichment (1.60×)** and **odds ratio (1.85×)** — both meaningfully above 1, meaning High pressure is far denser inside the official zone than outside. It agrees with the map *and* extends it.

**Q7. "What does the Markov / HMM layer actually add?"**
> Two things. Descriptively, it quantifies **persistence** — High pressure has a ~0.91 self-transition, so risk lingers after rain rather than resetting daily. Operationally, the per-cell transition matrix on the dashboard turns a snapshot into a short-horizon forecast: 'given today's state, here's the probability of each state tomorrow, for this specific cell.'

**Q8. "Why is the Moderate class the weakest?"**
> Moderate is the transitional band between Low and High on a continuous risk surface, so its boundaries are inherently fuzzier. The confusion matrix shows its errors fall onto the *neighbouring* classes, not onto the opposite extreme — the model is directionally right even when it's off by one band.

**Q9. "Does this generalise beyond this one corridor?"**
> I validate on one catchment with a proper temporal hold-out, so I can defend generalisation *across years*. Generalisation to other Kigali catchments is plausible but unproven — I list leave-one-catchment-out validation as future work rather than overclaiming.

**Q10. "How fast is it — could this run operationally?"**
> Inference is p95 ≈ 9.6 ms per query against a 2-second budget, and the whole app boots headless and serves in a container, so at pilot scale it's operationally realistic on free-tier hardware.

**Q11. "What's the single biggest limitation?"**
> The absence of a ground-truth incident register — my labels are derived pressure, not confirmed events. Everything else (coarser ERA5, low-resolution official polygons) is secondary. I'd rather state that plainly than oversell.

**Q12. "Why 250 m cells and this specific box?"**
> 250 m balances spatial detail against the resolution of the open data. I deliberately shifted the study box south so the grid genuinely overlaps the real Ministry-of-Environment flood zone — otherwise the spatial validation would be meaningless.

---

## 5. Closing lines (pick one)

- "In one sentence: a reproducible, interpretable, time-aware flood-pressure tool that beats both naive baselines on real open data, agrees with and extends the official map, and runs as a live dashboard."
- "Everything you've seen reruns end-to-end from a single `main.py`, with a passing test suite that re-derives these exact numbers — so it's not a one-off result, it's reproducible."

---

## 6. Rubric self-check (rehearse against this)

| Rubric item | Where you show it in the demo | Say the number |
|---|---|---|
| **Testing Results (5)** | Model panel: confusion, splits, 10/10 tests; testing_results/ folder | "macro-F1 0.813, high-recall 0.843, 10/10 tests pass" |
| **Analysis (2)** | Map + metrics + leaderboard | "beats rainfall baseline by +0.19 F1, static map by +0.49" |
| **Discussion** | Persistence + spatial agreement | "agrees with official map (1.85× odds) and extends it" |
| **Recommendations** | Limitations + future work slide | "incident validation, CHIRPS blend, per-catchment testing" |
| **Deployment (3)** | The running app + Dockerfile/render.yaml | "boots headless, HTTP 200, p95 9.6 ms" |
| **Demo video / live app** | This walkthrough + the live URL | (record ≤5 min following §1) |

Practice the §1 flow out loud twice with the deck in `Practice_Deck.pptx`, timing yourself to 5 minutes. You've got this.
