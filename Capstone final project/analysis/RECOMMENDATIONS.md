# Recommendations and Future Work

**Project:** Geospatial Flood-Risk Modelling using Climate Data and Hidden Markov Models in Rwanda
**Author:** Kellen Murerwa · **Supervisor:** Emmanuel Adjei

Developed with the supervisor, grouped into (A) recommendations to the community
on how the product should and should not be applied, and (B) future technical work.

---

## A. Recommendations to the community on applying the product

1. **Use it for screening and prioritisation, not as a flood warning.**
   A flood-pressure state is a *derived risk condition* (rainfall + terrain +
   exposure), **not** a confirmed flood event. The tool should complement — never
   replace — MIDIMAR / Meteo Rwanda official early-warning channels. It is best
   used to **prioritise drainage inspection, sandbag pre-positioning and community
   sensitisation** in the 1–3 days after heavy rain.

2. **Trust the spatial pattern more than the exact class.** The model reliably
   concentrates High pressure inside and immediately around the official flood
   zones (1.85× odds) and highlights a wider rainfall-driven footprint. Treat the
   *map of where pressure is rising* as the primary output; treat the exact
   Low/Moderate/High label of a single borderline cell with caution, given the
   sharp decision boundary.

3. **Pair it with local knowledge.** Community-based disaster-risk-reduction
   groups and cell/sector leaders should validate flagged areas on the ground.
   The dashboard is designed for exactly this — a non-modeller can inspect any
   date and cell and see the rainfall and feature values behind a prediction.

4. **Expect over-warning in borderline conditions, and set a review threshold.**
   Because high-pressure recall was deliberately prioritised, the system errs
   toward flagging risk. Authorities should decide an action threshold (e.g. act
   when ≥ N contiguous cells are High) rather than reacting to every single
   High cell.

5. **Respect the data licences and privacy note.** Outputs derive from Open-Meteo
   (ERA5/Copernicus, SRTM/NASA), OpenStreetMap (ODbL) and Rwanda GeoPortal/MOE
   polygons; attribution must be preserved in any redistribution.

---

## B. Future work (technical)

1. **Ground-truth with real incident records.** The highest-value next step is to
   obtain confirmed flood-incident reports (MIDIMAR, district offices, news/social
   archives) and re-validate against *events*, not derived labels. This directly
   addresses the project's main threat to validity.

2. **Probability calibration + a true Moderate band.** Apply isotonic/Platt
   calibration and tune class thresholds so the Moderate state is meaningful and
   the model stops saturating to P(High)≈1 under modest sustained rain. Report
   calibration curves alongside F1.

3. **Promote the temporal layer.** Replace the coarse 3-state HMM forecaster with
   a sequence model that ingests the rainfall features directly (e.g. an
   input–output HMM, a CRF, or a small GRU/LSTM) so next-step accuracy can rival
   the supervised layer, while keeping the HMM transition matrix for explanation.

4. **Forecast-driven, forward-looking risk.** Feed **forecast** rainfall
   (Open-Meteo forecast API) instead of only historical accumulations, turning the
   tool from *nowcasting* into a genuine *1–7 day ahead* flood-pressure outlook.

5. **Generalise beyond one corridor and one year.** Re-train and spatially
   cross-validate across additional Kigali catchments and multiple hold-out years
   to demonstrate transferability; add leave-one-catchment-out validation.

6. **Operationalise the deployment.** Add scheduled daily data refresh, model-drift
   monitoring, and an SMS/USSD or simple alert push so the sub-10-ms inference can
   reach non-dashboard users; containerise (see `../deployment/`) and run on a
   small always-on instance.

7. **Enrich features.** Add land-cover/imperviousness, soil type, drainage-network
   topology and antecedent soil-moisture proxies to sharpen the physical realism
   of the susceptibility signal.

---

## C. Priority ordering (supervisor-agreed)

| Priority | Item | Why first |
|---|---|---|
| 1 | Incident-record ground-truth (B1) | Removes the biggest validity gap |
| 2 | Calibration + Moderate band (B2) | Makes day-to-day output trustworthy |
| 3 | Forecast-driven outlook (B4) | Turns screening into early action |
| 4 | Operational deployment + alerts (B6) | Reaches users beyond the dashboard |
| 5 | Multi-catchment generalisation (B5) | Establishes external validity |
