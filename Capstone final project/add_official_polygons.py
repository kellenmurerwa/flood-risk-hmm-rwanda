"""
Integrate the OFFICIAL Rwanda flood-risk polygons (Rwanda GeoPortal /
geodata.rw, source: Ministry of Environment) into the dataset, replacing the
terrain-hydrology proxy for `flood_polygon_intersection`.

Service: https://geodata.rw/server/rest/services/basemap/Flood_Risk_Areas/FeatureServer/0
Polygons covering the Kigali region (objectid 1,2,3) are cached as
data_cache/official_flood_polygons.geojson. Cell centroids are tested with an
even-odd compound matplotlib Path so interior holes are respected.
"""
import json
from pathlib import Path as FPath

import numpy as np
import pandas as pd
import requests
from matplotlib.path import Path as MPath

ROOT = FPath(__file__).parent
CACHE = ROOT / "data_cache"
GEOJSON = CACHE / "official_flood_polygons.geojson"
SERVICE = ("https://geodata.rw/server/rest/services/basemap/"
           "Flood_Risk_Areas/FeatureServer/0/query")


def fetch_polygons():
    if GEOJSON.exists():
        return json.loads(GEOJSON.read_text())
    gj = requests.get(SERVICE, params={
        "where": "objectid IN (1,2,3)", "outFields": "objectid,gridcode,source",
        "outSR": "4326", "f": "geojson"}, timeout=120).json()
    GEOJSON.write_text(json.dumps(gj))
    return gj


def build_compound_path(gj):
    """One compound Path over every ring (exterior + holes) of every feature.
    even-odd fill => points inside holes are correctly excluded."""
    verts, codes = [], []
    for f in gj["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:                      # poly = [exterior, hole1, ...]
            for ring in poly:
                ring = np.asarray(ring)
                if len(ring) < 3:
                    continue
                verts.append(ring)
                c = np.full(len(ring), MPath.LINETO)
                c[0] = MPath.MOVETO
                codes.append(c)
    return MPath(np.vstack(verts), np.concatenate(codes))


def main():
    gj = fetch_polygons()
    nrings = sum(len(p) for f in gj["features"]
                 for p in ([f["geometry"]["coordinates"]]
                           if f["geometry"]["type"] == "Polygon"
                           else f["geometry"]["coordinates"]))
    print(f"[official] {len(gj['features'])} features, {nrings} rings")

    path = build_compound_path(gj)
    grid = pd.read_csv(ROOT / "real_grid_cells.csv")
    pts = grid[["centroid_lon", "centroid_lat"]].values
    inside = path.contains_points(pts)
    grid["flood_official"] = inside.astype(int)
    n = int(inside.sum())
    print(f"[official] cells inside official polygons: {n}/{len(grid)} "
          f"({100*n/len(grid):.0f}%)")
    if "flood_polygon_intersection" in grid:
        proxy = grid["flood_polygon_intersection"].astype(int)
        agree = (proxy.values == inside.astype(int)).mean()
        print(f"[official] proxy flood cells: {proxy.sum()} | "
              f"proxy-vs-official cell agreement: {agree:.2f}")

    if n == 0:
        print("[official] WARNING: official polygons do not cover the AOI grid "
              "-> keeping susceptibility proxy. (National layer is coarse.)")
        return

    # write back into grid + dataset
    grid.to_csv(ROOT / "real_grid_cells.csv", index=False)
    df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
    m = dict(zip(grid["grid_id"], grid["flood_official"]))
    df["flood_polygon_intersection"] = df["grid_id"].map(m).astype(int)
    df.to_parquet(ROOT / "real_flood_dataset.parquet", index=False)
    print("[official] dataset flood_polygon_intersection updated from official "
          "polygons; saved real_flood_dataset.parquet")


if __name__ == "__main__":
    main()
