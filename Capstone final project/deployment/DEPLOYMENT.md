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

## 2. Runtime artifacts — already included ✅

`real_flood_dataset.parquet`, `model_outputs_real/` and
`data_cache/official_flood_polygons.geojson` are **committed in this folder**, so a
host that clones the repo has everything and the app loads with **no data
re-fetch**. Verified: an export of the git-tracked files only (i.e. exactly what a
clone/deploy receives) boots the dashboard to HTTP 200 with no errors.

(These are normally reproducible via `python main.py all`; they are shipped here so
the graded submission runs and deploys out of the box.)

`.streamlit/config.toml` is already at this folder's root, and `requirements.txt`
is the slim, pinned runtime set validated for deployment.

---

## 3. Deploy — Streamlit Community Cloud (recommended, free)

Everything needed (artifacts, `.streamlit/config.toml`, pinned `requirements.txt`)
is already in place, so:

1. Push this project to a GitHub repo.
2. Go to <https://share.streamlit.io> → **New app** → pick the repo/branch.
3. Set **Main file path** = `dashboard.py`. Click **Deploy**.
4. You receive a public URL like `https://<app-name>.streamlit.app`.
   **Paste that URL into [`../README.md`](../README.md) "Live deployment".**

> If you deploy this folder as a **subdirectory** of a larger repo, set the Main
> file path to the full path, e.g. `Capstone final project/dashboard.py`.

## 4. Deploy — Docker (any host)

```bash
# run from this folder (the repo root); the artifacts are already here
docker build -f deployment/Dockerfile -t kigali-flood .
docker run -p 8501:8501 kigali-flood
# verify
curl -f http://localhost:8501/_stcore/health      # -> 200
```
Push `kigali-flood` to any registry and run on Render/Fly/Railway/a VM.

## 5. Deploy — Render Blueprint

1. Copy `render.yaml` to the repo root (artifacts and `.streamlit/config.toml` are
   already in place); push.
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
