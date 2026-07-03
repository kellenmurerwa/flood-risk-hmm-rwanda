"""
Testing strategy 3 of 3 -- PERFORMANCE ON DIFFERENT SOFTWARE SPECIFICATIONS.

The deployed product must answer a single farmer/official query (one date =
729 grid cells) well inside the proposal's 2-second latency budget, and must
also scale to bulk back-testing. This script benchmarks the trained XGBoost
model across:

  * different BATCH SIZES (1, 729 = one map-day, 10k, 100k, full 2024 hold-out),
  * different XGBoost THREAD counts (1, 2, 4, all) -- emulating deployment on
    constrained vs. multi-core hardware/software configurations.

It reports throughput (rows/sec) and p50/p95 latency, and saves a screenshot
to testing_results/screenshots/benchmark_performance.png.

Run:  python "tests/benchmark_performance.py"
"""
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model_outputs_real"
SHOTS = ROOT / "testing_results" / "screenshots"
FEATURES = ["rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_14d_mm",
            "elevation_m", "slope_deg", "distance_to_river_m",
            "road_density_km_per_km2", "building_density_count_per_km2",
            "flood_polygon_intersection"]


def timed(fn, repeats=20):
    ts = []
    for _ in range(repeats):
        t = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t) * 1000.0)  # ms
    ts = np.array(ts)
    return ts.mean(), np.percentile(ts, 50), np.percentile(ts, 95)


def main():
    df = pd.read_parquet(ROOT / "real_flood_dataset.parquet")
    df["date"] = pd.to_datetime(df["date"])
    bundle = joblib.load(OUT / "xgboost_model.joblib")
    model, feat = bundle["model"], bundle["features"]
    cpu = os.cpu_count()

    print("=" * 78)
    print("PERFORMANCE TEST -- inference latency / throughput")
    print(f"Host: {cpu} logical CPUs | XGBoost {__import__('xgboost').__version__} | "
          f"numpy {np.__version__}")
    print("=" * 78)

    full = df[df["date"].dt.year == 2024][feat].values
    sizes = {"1 cell": 1, "1 map-day (729)": 729, "10k": 10_000,
             "100k": 100_000, f"full 2024 ({len(full):,})": len(full)}

    # ---- batch-size sweep (all threads) ----
    print(f"\n[A] Batch-size sweep (all {cpu} threads)")
    print(f"{'batch':>22} | {'mean ms':>9} | {'p95 ms':>8} | {'rows/sec':>12}")
    batch_rows = []
    for name, n in sizes.items():
        X = full[:n] if n <= len(full) else np.repeat(full, n // len(full) + 1, 0)[:n]
        reps = 50 if n <= 729 else (20 if n <= 10_000 else 8)
        mean, p50, p95 = timed(lambda: model.predict(X), repeats=reps)
        rps = n / (mean / 1000.0)
        batch_rows.append((name, n, mean, p95, rps))
        print(f"{name:>22} | {mean:9.3f} | {p95:8.3f} | {rps:12,.0f}")

    # ---- thread sweep on one map-day (the live-query workload) ----
    print("\n[B] Thread sweep on the live workload (1 map-day = 729 cells)")
    print(f"{'threads':>10} | {'mean ms':>9} | {'p95 ms':>8}")
    Xday = full[:729]
    thread_rows = []
    for th in sorted({1, 2, 4, cpu}):
        try:
            model.set_params(n_jobs=th)
        except Exception:
            os.environ["OMP_NUM_THREADS"] = str(th)
        mean, p50, p95 = timed(lambda: model.predict(Xday), repeats=50)
        thread_rows.append((th, mean, p95))
        budget = "OK < 2000 ms" if p95 < 2000 else "OVER BUDGET"
        print(f"{th:>10} | {mean:9.3f} | {p95:8.3f}   [{budget}]")

    live_p95 = min(r[2] for r in thread_rows)
    print(f"\nLive single-query p95 latency: {live_p95:.2f} ms "
          f"(proposal NFR budget = 2000 ms) -> "
          f"{'MET' if live_p95 < 2000 else 'MISSED'}")

    # ---- screenshot ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    names = [r[0] for r in batch_rows]
    rps = [r[4] for r in batch_rows]
    ax1.barh(range(len(names)), rps, color="#3182bd")
    ax1.set_yticks(range(len(names)))
    ax1.set_yticklabels(names, fontsize=8)
    ax1.set_xlabel("Throughput (rows/sec)")
    ax1.set_title("Throughput vs batch size")
    for i, v in enumerate(rps):
        ax1.text(v, i, f" {v:,.0f}", va="center", fontsize=7)

    th = [str(r[0]) for r in thread_rows]
    p95s = [r[2] for r in thread_rows]
    ax2.bar(th, p95s, color="#31a354")
    ax2.axhline(2000, color="red", ls="--", lw=1, label="2 s NFR budget")
    ax2.set_xlabel("XGBoost threads")
    ax2.set_ylabel("p95 latency (ms) · 729-cell query")
    ax2.set_title("Live-query latency vs thread count")
    for i, v in enumerate(p95s):
        ax2.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=7)
    ax2.legend()
    fig.suptitle(f"Performance test — host: {cpu} logical CPUs", fontsize=11)
    fig.tight_layout()
    SHOTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(SHOTS / "benchmark_performance.png", dpi=140)
    print(f"\nSaved screenshot -> {SHOTS / 'benchmark_performance.png'}")


if __name__ == "__main__":
    main()
