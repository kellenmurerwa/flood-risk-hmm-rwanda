"""
Flood-Pressure Inspection Dashboard -- Nyabugogo-Nyabarongo corridor, Kigali.

A lightweight Streamlit app (proposal deliverable: "a reproducible
notebook/dashboard for inspecting results by date and location"). It lets a user
pick a date, view the predicted Low/Moderate/High flood-pressure map over the
grid, overlay the official flood-risk polygons, inspect any cell's features and
the XGBoost prediction, and view the rainfall time series and HMM transitions.

Run:  streamlit run dashboard.py
Needs: streamlit, pydeck (bundled with streamlit), pandas, joblib + the trained
       model_outputs_real/ artifacts and real_flood_dataset.parquet.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import streamlit as st

ROOT = Path(__file__).parent
OUT = ROOT / "model_outputs_real"
CLASSES = ["Low", "Moderate", "High"]
COLORS = {"Low": [44, 162, 95], "Moderate": [254, 178, 76], "High": [222, 45, 38]}
FEATURES = ["rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_14d_mm",
            "elevation_m", "slope_deg", "distance_to_river_m",
            "road_density_km_per_km2", "building_density_count_per_km2",
            "flood_polygon_intersection"]

st.set_page_config(page_title="Kigali Flood-Pressure", layout="wide")


@st.cache_data
def load_data():
    df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_resource
def load_model():
    b = joblib.load(OUT / "xgboost_model.joblib")
    return b["model"], b["features"]


@st.cache_data
def load_polygons():
    p = ROOT / "data_cache" / "official_flood_polygons.geojson"
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data
def load_summary():
    p = OUT / "results_summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


df = load_data()
model, feat = load_model()
summary = load_summary()

st.title("🌊 Kigali Flood-Pressure Inspection Dashboard")
st.caption("Nyabugogo–Nyabarongo corridor · daily Low/Moderate/High flood-pressure "
           "states from real rainfall (Open-Meteo/ERA5), terrain (SRTM), OSM "
           "exposure and official MOE flood polygons.")

# ---- sidebar controls ----
st.sidebar.header("Controls")
dates = df["date"].dt.date.unique()
dsel = st.sidebar.select_slider("Date", options=sorted(dates),
                                value=sorted(dates)[len(dates) // 2])
show_poly = st.sidebar.checkbox("Overlay official flood polygons", True)
layer_mode = st.sidebar.radio("Map colour", ["Predicted state", "Label state",
                                             "Rainfall (3-day)"])

day = df[df["date"].dt.date == dsel].copy()
X = day[feat].values
day["pred_i"] = model.predict(X)
proba = model.predict_proba(X)
day["pred"] = [CLASSES[i] for i in day["pred_i"]]
day["pred_conf"] = proba.max(axis=1)

# ---- top metrics ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Cells", len(day))
c2.metric("Predicted High", int((day["pred"] == "High").sum()))
c3.metric("Mean 3-day rain", f"{day['rainfall_3d_mm'].mean():.1f} mm")
agree = summary.get("supervised_results", {}).get("XGBoost", {})
c4.metric("Model macro-F1 (2024)", f"{agree.get('macro_f1', float('nan')):.3f}")

# ---- map ----
import pydeck as pdk

if layer_mode == "Rainfall (3-day)":
    r = day["rainfall_3d_mm"]
    norm = (r - r.min()) / (r.max() - r.min() + 1e-9)
    day["color"] = [[int(255 * v), int(120 * (1 - v)), int(60 + 150 * (1 - v))]
                    for v in norm]
else:
    col = "pred" if layer_mode == "Predicted state" else "flood_pressure_state"
    day["color"] = day[col].map(COLORS)

cell_deg = 0.00225
poly_layers = []
if show_poly:
    gj = load_polygons()
    if gj:
        poly_layers.append(pdk.Layer(
            "GeoJsonLayer", gj, stroked=True, filled=True,
            get_fill_color=[30, 60, 200, 35], get_line_color=[30, 60, 200, 160],
            line_width_min_pixels=1))

grid_layer = pdk.Layer(
    "ScatterplotLayer", day, get_position=["centroid_lon", "centroid_lat"],
    get_fill_color="color", get_radius=110, opacity=0.75, pickable=True)

st.pydeck_chart(pdk.Deck(
    map_style=None,
    initial_view_state=pdk.ViewState(
        latitude=float(day["centroid_lat"].mean()),
        longitude=float(day["centroid_lon"].mean()), zoom=12.5),
    layers=poly_layers + [grid_layer],
    tooltip={"text": "{grid_id}\nPred: {pred} ({pred_conf})\n"
                     "Rain3d: {rainfall_3d_mm} mm\nElev: {elevation_m} m"}))

st.markdown("**Legend** — 🟢 Low · 🟠 Moderate · 🔴 High · 🟦 official flood polygon")

# ---- cell inspector ----
st.subheader("🔎 Inspect a grid cell")
gid = st.selectbox("Grid cell", sorted(day["grid_id"].unique()))
cell_day = day[day["grid_id"] == gid].iloc[0]
ic1, ic2 = st.columns([1, 1])
with ic1:
    st.write("**Prediction**")
    st.write({c: round(float(p), 3) for c, p in zip(CLASSES, proba[
        day["grid_id"].tolist().index(gid)])})
    st.write("**Features**")
    st.dataframe(cell_day[feat].to_frame("value"))
with ic2:
    st.write("**Rainfall & flood-pressure time series (this cell)**")
    series = df[df["grid_id"] == gid].set_index("date")
    st.line_chart(series[["rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm"]])
    state_num = series["flood_pressure_state"].map(
        {"Low": 0, "Moderate": 1, "High": 2})
    st.area_chart(state_num.rename("flood_pressure (0=Low,2=High)"))

# ---- model / HMM panel ----
with st.expander("📈 Model performance & HMM transitions"):
    if summary:
        st.write("**Supervised results (2024 hold-out)**")
        st.dataframe(pd.DataFrame(summary["supervised_results"]).T.round(3))
        hmm = summary.get("hmm", {})
        if hmm.get("transition_matrix"):
            st.write("**HMM daily transition matrix**")
            T = pd.DataFrame(hmm["transition_matrix"], index=CLASSES, columns=CLASSES)
            st.dataframe(T.round(3))
            st.write(f"Next-step accuracy: {hmm.get('next_step_accuracy', 0):.3f} · "
                     f"Spatial agreement (pred-High in official zone): "
                     f"{summary['supervised_results'].get('XGBoost', {}).get('spatial_agreement_high_in_zone', float('nan')):.3f}")
    for img, cap in [("confusion_XGBoost.png", "XGBoost confusion (2024)"),
                     ("xgb_feature_importance.png", "Feature importance"),
                     ("shap_summary.png", "SHAP summary"),
                     ("hmm_transition_matrix.png", "HMM transitions")]:
        f = OUT / img
        if f.exists():
            st.image(str(f), caption=cap, width=460)

st.caption("Flood-pressure = derived risk state (rainfall + terrain + exposure), "
           "not a confirmed flood event. Official polygons: Rwanda GeoPortal / MOE.")
