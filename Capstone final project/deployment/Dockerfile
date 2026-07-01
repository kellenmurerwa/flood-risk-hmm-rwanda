# Kigali Flood-Pressure dashboard — container image.
# BUILD CONTEXT MUST BE THE REPO ROOT (so the data/model artifacts are visible),
# because real_flood_dataset.parquet and model_outputs_real/ are .gitignored.
#
#   docker build -f "Capstone final project/deployment/Dockerfile" -t kigali-flood .
#   docker run -p 8501:8501 kigali-flood
#   open http://localhost:8501
#
FROM python:3.11-slim

WORKDIR /app

# system deps for matplotlib/xgboost wheels are already in the slim image;
# curl is added only for the container health-check.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# application code
COPY dashboard.py main.py evaluate_spatial.py ./

# runtime artifacts (regenerate locally with `python main.py all` if absent)
COPY real_flood_dataset.parquet ./
COPY model_outputs_real/ ./model_outputs_real/
COPY data_cache/official_flood_polygons.geojson ./data_cache/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "dashboard.py", \
            "--server.port=8501", "--server.address=0.0.0.0", \
            "--server.headless=true"]
