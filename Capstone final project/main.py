"""
Geospatial Flood-Risk Modelling using Climate Data and Hidden Markov Models
in Rwanda -- Nyabugogo-Nyabarongo corridor, Kigali.

Capstone project entry point. Orchestrates the full reproducible pipeline:

    python main.py build       # fetch real data + build the modelling table
    python main.py train       # train baselines + RF + XGBoost + HMM (2024 holdout)
    python main.py polygons     # refresh official MOE flood-polygon membership
    python main.py evaluate    # spatial validation + flood-pressure risk map
    python main.py dashboard   # launch the Streamlit inspection dashboard
    python main.py all         # build -> train -> evaluate (no dashboard)

Each stage is implemented in its own module so it can also be run directly.
Data sources are real and free/keyless: Open-Meteo (ERA5 rainfall, SRTM
elevation), OpenStreetMap Overpass (rivers/roads/buildings), and the official
Rwanda GeoPortal flood-risk polygons (geodata.rw, Ministry of Environment).

Author: Kellen Murerwa  |  Supervisor: Emmanuel Adjei  |  ALU BSc Software Engineering
"""
import argparse
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run_module(name):
    """Execute a sibling script as __main__ (shares this interpreter/env)."""
    path = ROOT / name
    if not path.exists():
        sys.exit(f"[main] missing pipeline module: {name}")
    print(f"\n{'='*70}\n[main] running {name}\n{'='*70}")
    runpy.run_path(str(path), run_name="__main__")


STAGES = {
    "build": "build_real_dataset.py",      # real data -> real_flood_dataset.parquet
    "polygons": "add_official_polygons.py",  # official MOE flood polygons -> feature
    "train": "train_real.py",              # models + HMM, 2024 temporal holdout
    "evaluate": "evaluate_spatial.py",     # spatial validation + risk map
}


def main():
    ap = argparse.ArgumentParser(
        description="Flood-pressure modelling pipeline (Kigali capstone).")
    ap.add_argument("stage",
                    choices=list(STAGES) + ["all", "dashboard"],
                    help="pipeline stage to run")
    args = ap.parse_args()

    if args.stage == "dashboard":
        # Streamlit must own the process, so launch it as a subprocess.
        subprocess.run([sys.executable, "-m", "streamlit", "run",
                        str(ROOT / "dashboard.py")], check=False)
        return

    if args.stage == "all":
        for s in ["build", "train", "evaluate"]:
            run_module(STAGES[s])
        print("\n[main] pipeline complete. Launch the dashboard with: "
              "python main.py dashboard")
        return

    run_module(STAGES[args.stage])


if __name__ == "__main__":
    main()
