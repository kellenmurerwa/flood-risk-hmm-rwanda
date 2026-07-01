# Deployment Plan — Kigali Flood-Pressure Dashboard

**Artefact deployed:** the Streamlit inspection dashboard (`dashboard.py`) that
serves the trained XGBoost flood-pressure model over the 729-cell Kigali corridor.

This document gives the deployment plan (steps, tools, environments), the
artifact caveat, and the verification evidence required by the rubric.

---

## 0. Local boot verification (already done) ✅

The app was launched headless and verified to serve before writing this guide:

```
$ streamlit run dashboard.py --server.port 8599 --server.headless true
  You can now view your Streamlit app in your browser.
  URL: http://127.0.0.1:8599

[deploy verification]
GET /_stcore/health -> HTTP 200
GET /               -> HTTP 200
```

Evidence: [`../testing_results/deploy_local_boot.log`](../testing_results/deploy_local_boot.log).
Inference latency under load is p95 ≈ 9.6 ms (see `../testing_results/test_output_performance.txt`),
so the app is responsive at pilot scale on free-tier hardware.

---

## 1. Environments & tools

| Concern | Choice | Why |
|---|---|---|
| Runtime | Python 3.11 | Matches `requirements.txt` pins |
| App server | Streamlit (built-in) | The dashboard *is* a Streamlit app |
| Container | Docker (`Dockerfile`) | Portable to any host |
| Free host (recommended) | **Streamlit Community Cloud** | Free, no card, GitHub-linked |
| Alt host | Render / Railway (`render.yaml`, `Procfile`) | Free web service from same repo |

---

## 2. The artifact caveat (read first) ⚠️

`real_flood_dataset.parquet` (5.8 MB) and `model_outputs_real/` (3.5 MB) are
**`.gitignore`d** because they are reproducible (`python main.py all`). A host that
clones the GitHub repo will therefore **not** have them and the app will fail to
load. You must do **one** of:

**Option A — commit the runtime artifacts (simplest, ~9 MB, well under GitHub limits):**
```bash
git add -f real_flood_dataset.parquet \
           model_outputs_real/xgboost_model.joblib \
           model_outputs_real/results_summary.json \
           model_outputs_real/*.png \
           data_cache/official_flood_polygons.geojson
git commit -m "Add runtime artifacts for deployment"
```

**Option B — regenerate on the host at build time** (slower, needs network):
add `python main.py all` to the build command. Not recommended on free tiers
(can exceed build timeouts while fetching Open-Meteo/OSM data).

This repo's `Dockerfile` uses **Option A semantics** — it `COPY`s the artifacts
from the build context, so they must exist locally (they do) when you build.

---

## 3. Deploy — Streamlit Community Cloud (recommended, free)

1. Copy `deployment/.streamlit/config.toml` to the **repo root** as `.streamlit/config.toml`.
2. Do **Option A** above so the artifacts are in the repo, then `git push`.
3. Go to <https://share.streamlit.io> → **New app** → pick the repo/branch.
4. Set **Main file path** = `dashboard.py`. Click **Deploy**.
5. You receive a public URL like `https://<app-name>.streamlit.app`.
   **Paste that URL into [`../README.md`](../README.md) "Live deployment".**

## 4. Deploy — Docker (any host)

```bash
# build context = repo root so artifacts are visible
docker build -f "Capstone final project/deployment/Dockerfile" -t kigali-flood .
docker run -p 8501:8501 kigali-flood
# verify
curl -f http://localhost:8501/_stcore/health      # -> 200
```
Push `kigali-flood` to any registry and run on Render/Fly/Railway/a VM.

## 5. Deploy — Render Blueprint

1. Copy `render.yaml` and `.streamlit/config.toml` to the repo root; do Option A; push.
2. Render → **New +** → **Blueprint** → select the repo.
3. Render reads `render.yaml`, builds, and serves on a public `*.onrender.com` URL.

---

## 6. Post-deploy verification checklist

- [ ] `GET /_stcore/health` returns **200**
- [ ] Date slider renders the predicted-state map (green/orange/red cells)
- [ ] Cell inspector shows feature values + class probabilities
- [ ] "Model performance & HMM transitions" expander shows the figures
- [ ] p95 query latency < 2 s (NFR budget) — already 9.6 ms locally

---

## 7. Operational notes (future)

For a production deployment: add a scheduled daily data refresh, pin the model
version, add drift monitoring, and front the inference with a small alert push
(SMS/USSD) — see [`../analysis/RECOMMENDATIONS.md`](../analysis/RECOMMENDATIONS.md) §B6.
