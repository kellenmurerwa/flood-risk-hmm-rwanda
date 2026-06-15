"""Generate all diagrams for the Flood-Risk HMM capstone proposal."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
import matplotlib.dates as mdates
from datetime import datetime

OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)

NAVY = "#0b3d91"
RED = "#c8102e"
GREEN = "#2e7d32"
GREY = "#555555"
LIGHT = "#eef3fb"
AMBER = "#f5a623"
BLUE = "#1565c0"


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------------------
# Figure 1: System Architecture (layered geospatial ML + HMM pipeline)
# ---------------------------------------------------------------------------
def fig_architecture():
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.set_xlim(0, 100)
    ax.axis("off")
    ax.set_title("Figure 1. System Architecture of the Geospatial Flood-Pressure Modelling System",
                 fontsize=12, fontweight="bold", pad=12)

    def box(x, y, w, h, label, color, text_color="white", fontsize=8.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3",
                                     facecolor=color, edgecolor="black", linewidth=1.2))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=fontsize, color=text_color, fontweight="bold", wrap=True)

    def arrow(x1, y1, x2, y2, label="", color="black", offset=(0, 0)):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                      arrowstyle="-|>", mutation_scale=13,
                                      color=color, linewidth=1.3))
        if label:
            ax.text((x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1],
                    label, fontsize=7, color=color, ha="center",
                    bbox=dict(facecolor="white", edgecolor="none", pad=1))

    for y, lbl in [(62, "OUTPUT & EVALUATION TIER"), (44, "MODELLING TIER"),
                   (24, "PROCESSING & FEATURE ENGINEERING TIER"),
                   (4, "EXTERNAL DATA SOURCES")]:
        ax.text(1, y + 4.5, lbl, fontsize=8, color=GREY, fontweight="bold")
        ax.plot([0, 100], [y + 4, y + 4], color="#cccccc", linestyle="--", linewidth=0.6)

    # Output tier
    box(8, 52, 26, 8, "Flood-Pressure Risk Maps\n& Notebook / Dashboard", NAVY)
    box(40, 52, 26, 8, "Spatial Validation vs\nOfficial Flood-Risk Polygons", GREEN)
    box(72, 52, 22, 8, "Evaluation Metrics\n& Transition Matrix", GREY)

    # Modelling tier
    box(8, 34, 26, 8, "Flood-Pressure Classifier\n(RF / XGBoost)", GREEN)
    box(40, 34, 26, 8, "HMM Temporal Layer\n(Low / Moderate / High)", AMBER, text_color="black")
    box(72, 34, 22, 8, "Model Registry\n(joblib artefacts)", GREY)

    # Processing tier
    box(4, 14, 21, 8, "Grid Builder\n(100-250 m cells)", NAVY)
    box(28, 14, 21, 8, "Rainfall Feature Engine\n(1/3/7/14-day totals)", BLUE)
    box(52, 14, 21, 8, "Terrain & Hydrology\n(slope, dist-to-river)", BLUE)
    box(76, 14, 20, 8, "Exposure Features\n(road/building density)", BLUE)

    # External sources
    box(3, -6, 22, 7, "CHIRPS / Meteo Rwanda\nDaily Rainfall", "#37474f")
    box(28, -6, 22, 7, "SRTM DEM\n(Elevation)", "#37474f")
    box(53, -6, 20, 7, "OpenStreetMap\n(roads, rivers, buildings)", "#37474f")
    box(76, -6, 20, 7, "Rwanda GeoPortal\nFlood-Risk Polygons", "#37474f")
    ax.set_ylim(-10, 66)

    # Arrows external -> processing
    arrow(14, 1, 14, 14, "rainfall", color=GREY)
    arrow(39, 1, 39, 14, "DEM", color=GREY)
    arrow(63, 1, 63, 14, "vectors", color=GREY)
    arrow(86, 1, 86, 14, "polygons", color=GREY)

    # processing -> modelling
    arrow(20, 22, 20, 34, "feature table")
    arrow(45, 22, 50, 34, "labels")
    arrow(63, 22, 55, 34, "")

    # modelling internal
    arrow(34, 38, 40, 38, "states")
    arrow(66, 38, 72, 38, "persist")

    # modelling -> output
    arrow(21, 42, 21, 52, "predicted state")
    arrow(53, 42, 53, 52, "transitions")
    arrow(83, 42, 83, 52, "metrics")

    save(fig, "fig01_architecture.png")


# ---------------------------------------------------------------------------
# Figure 2: HMM Flood-Pressure State Transition Diagram
# ---------------------------------------------------------------------------
def fig_hmm_states():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 80)
    ax.axis("off")
    ax.set_title("Figure 2. Hidden Markov Model of Daily Flood-Pressure State Transitions",
                 fontsize=12, fontweight="bold", pad=10)

    states = {
        "LOW": (20, 48, GREEN),
        "MODERATE": (50, 58, AMBER),
        "HIGH": (80, 48, RED),
    }
    for name, (x, y, color) in states.items():
        ax.add_patch(Circle((x, y), 9, facecolor=color, edgecolor="black", linewidth=1.6,
                            alpha=0.92))
        ax.text(x, y, name, ha="center", va="center", fontsize=11, color="white",
                fontweight="bold")

    def trans(x1, y1, x2, y2, label, rad=0.25, color=NAVY):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                      mutation_scale=14, color=color, linewidth=1.5,
                                      connectionstyle=f"arc3,rad={rad}"))
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + (4 if rad > 0 else -4), label,
                fontsize=8.5, color=color, ha="center", fontweight="bold",
                bbox=dict(facecolor="white", edgecolor="none", pad=1))

    # Forward transitions (rising pressure)
    trans(28, 51, 42, 56, "0.25", rad=0.25)
    trans(58, 56, 72, 51, "0.30", rad=0.25)
    # Backward transitions (receding pressure)
    trans(72, 45, 58, 51, "0.45", rad=0.25, color=GREY)
    trans(42, 51, 28, 45, "0.35", rad=0.25, color=GREY)
    # Skip transition Low<->High
    trans(26, 43, 74, 43, "0.05", rad=-0.18, color="#9e9e9e")

    # Self-loops
    def selfloop(x, y, label):
        ax.add_patch(FancyArrowPatch((x - 4, y + 7), (x + 4, y + 7), arrowstyle="-|>",
                                      mutation_scale=12, color="black", linewidth=1.2,
                                      connectionstyle="arc3,rad=-1.6"))
        ax.text(x, y + 15, label, ha="center", fontsize=8.5, fontweight="bold")
    selfloop(20, 48, "0.60")
    selfloop(50, 58, "0.40")
    selfloop(80, 48, "0.50")

    # Observation (emission) note
    ax.add_patch(FancyBboxPatch((14, 8), 72, 18, boxstyle="round,pad=0.5",
                                 facecolor=LIGHT, edgecolor=NAVY, linewidth=1.4))
    ax.text(50, 22, "Observed (emission) variables per grid cell, per day",
            ha="center", fontsize=9.5, color=NAVY, fontweight="bold")
    ax.text(50, 15,
            "rainfall_mm  •  rain_3d / rain_7d / rain_14d  •  slope_deg  •  elevation_m\n"
            "distance_to_river_m  •  road_density  •  building_density  •  flood_polygon_intersection",
            ha="center", va="center", fontsize=8, family="monospace")
    for x, (sx, sy, _) in [(0, states["LOW"]), (1, states["MODERATE"]), (2, states["HIGH"])]:
        ax.add_patch(FancyArrowPatch((sx, sy - 9), (sx, 26), arrowstyle="-|>",
                                      mutation_scale=11, color=GREY, linewidth=1.0,
                                      linestyle=":"))
    ax.text(91, 21, "emits", fontsize=8, color=GREY, style="italic")
    ax.text(50, 4, "Transition probabilities are illustrative; the matrix is estimated from data via Baum-Welch.",
            ha="center", fontsize=7.5, color=GREY, style="italic")

    save(fig, "fig02_hmm_states.png")


# ---------------------------------------------------------------------------
# Figure 3: Use Case Diagram
# ---------------------------------------------------------------------------
def fig_use_case():
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(-6, 80)
    ax.axis("off")
    ax.set_title("Figure 3. Use Case Diagram", fontsize=12, fontweight="bold", pad=12)

    def stick(x, y, label):
        ax.add_patch(plt.Circle((x, y + 4), 1.2, color="black", fill=False, linewidth=1.5))
        ax.plot([x, x], [y + 2.8, y - 1.5], color="black", linewidth=1.5)
        ax.plot([x - 2.3, x + 2.3], [y + 1.5, y + 1.5], color="black", linewidth=1.5)
        ax.plot([x, x - 2], [y - 1.5, y - 4.5], color="black", linewidth=1.5)
        ax.plot([x, x + 2], [y - 1.5, y - 4.5], color="black", linewidth=1.5)
        ax.text(x, y - 6.5, label, ha="center", va="top", fontsize=9, fontweight="bold")

    def uc(x, y, label, w=20, h=5):
        ax.add_patch(mpatches.Ellipse((x, y), w, h, facecolor=LIGHT, edgecolor="black", linewidth=1))
        ax.text(x, y, label, ha="center", va="center", fontsize=7.8)

    ax.add_patch(Rectangle((24, 2), 52, 72, facecolor="none", edgecolor=NAVY, linewidth=1.5))
    ax.text(50, 77, "Geospatial Flood-Pressure Modelling System", ha="center", fontsize=10,
            color=NAVY, fontweight="bold")

    stick(9, 60, "Researcher /\nAnalyst")
    stick(9, 22, "Disaster Manager\n(MINEMA)")
    stick(91, 60, "Meteo Rwanda /\nData API")
    stick(91, 22, "Urban\nPlanner")

    uc(37, 68, "Acquire rainfall & geodata")
    uc(63, 68, "Build spatial grid")
    uc(37, 58, "Engineer features")
    uc(63, 58, "Derive flood-pressure labels")
    uc(37, 48, "Train ML classifier")
    uc(63, 48, "Run HMM transitions")
    uc(37, 37, "Generate risk maps")
    uc(63, 37, "Validate vs flood polygons")
    uc(37, 26, "Inspect by date / cell")
    uc(63, 26, "Export report")
    uc(50, 13, "Manage datasets & model runs")

    def line(x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color="black", linewidth=0.8)

    for y in [68, 58, 48, 37]:
        line(12, 60, 27, y)
    line(12, 22, 27, 26)
    line(12, 22, 27, 37)
    line(12, 22, 50, 13)
    line(88, 60, 73, 68)
    line(88, 60, 73, 58)
    line(88, 22, 73, 26)
    line(88, 22, 73, 37)
    line(88, 22, 50, 13)

    save(fig, "fig03_use_case.png")


# ---------------------------------------------------------------------------
# Figure 4: Class Diagram
# ---------------------------------------------------------------------------
def fig_class_diagram():
    fig, ax = plt.subplots(figsize=(13, 9.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 92)
    ax.axis("off")
    ax.set_title("Figure 4. Class Diagram (UML)", fontsize=12, fontweight="bold", pad=10)

    def umlclass(x, y, name, attrs, methods, w=22, color=LIGHT):
        a_lines = len(attrs); m_lines = len(methods)
        title_h = 4
        attr_h = 2 + 2.2 * a_lines
        meth_h = 2 + 2.2 * m_lines
        h = title_h + attr_h + meth_h
        ax.add_patch(Rectangle((x, y - h), w, h, facecolor=color, edgecolor="black", linewidth=1.2))
        ax.text(x + w / 2, y - 2, name, ha="center", va="center", fontsize=9, fontweight="bold")
        ax.plot([x, x + w], [y - title_h, y - title_h], color="black", linewidth=1)
        for i, a in enumerate(attrs):
            ax.text(x + 0.5, y - title_h - 2 - 2.2 * i, "- " + a, fontsize=7.0, va="center")
        ax.plot([x, x + w], [y - title_h - attr_h, y - title_h - attr_h], color="black", linewidth=1)
        for i, m in enumerate(methods):
            ax.text(x + 0.5, y - title_h - attr_h - 2 - 2.2 * i, "+ " + m, fontsize=7.0, va="center")
        return dict(x=x, y=y, w=w, h=h, cx=x + w / 2, cy=y - h / 2,
                    right=x + w, left=x, top=y, bottom=y - h)

    grid = umlclass(2, 90, "GridCell",
                    ["grid_id: str", "centroid_lat: float", "centroid_lon: float",
                     "elevation_m: float", "slope_deg: float"],
                    ["fromAOI()", "neighbours()"])
    rain = umlclass(28, 90, "RainfallObservation",
                    ["grid_id: str", "date: date", "rainfall_mm: float",
                     "rain_3d: float", "rain_7d: float", "rain_14d: float"],
                    ["rollingTotals()"])
    hydro = umlclass(54, 90, "HydrologyExposure",
                     ["grid_id: str", "dist_river_m: float", "dist_stream_m: float",
                      "road_density: float", "building_density: float"],
                     ["fromOSM()"])
    label = umlclass(78, 90, "FloodPressureLabel",
                     ["grid_id: str", "date: date", "state: enum",
                      "intersects_poly: bool"],
                     ["derive()"])

    clf = umlclass(4, 50, "ClassifierModel",
                   ["name: str", "version: str", "macro_f1: float", "path: str"],
                   ["train()", "predict(features)"])
    hmm = umlclass(30, 50, "HMMModel",
                   ["n_states: int", "trans_matrix: array", "emission: array"],
                   ["fit()", "predictNext()", "viterbi()"])
    rmap = umlclass(56, 50, "RiskMap",
                    ["run_id: UUID", "date: date", "layer: geojson"],
                    ["render()", "export()"])
    evalr = umlclass(80, 50, "EvaluationReport",
                     ["run_id: UUID", "macro_f1: float", "high_recall: float",
                      "spatial_overlap: float"],
                     ["compute()", "compare()"])

    run = umlclass(20, 16, "ModelRun",
                   ["run_id: UUID", "aoi: str", "grid_size_m: int",
                    "period: range", "created_at: ts"],
                   ["start()", "log()"])
    ds = umlclass(58, 16, "Dataset",
                  ["source: str", "kind: enum", "licence: str", "checksum: str"],
                  ["ingest()", "validate()"])

    def rel(x1, y1, x2, y2, m1="1", m2="*", dx=0.6):
        ax.plot([x1, x2], [y1, y2], color="black", linewidth=1)
        ax.text(x1 + dx, y1 + 0.8, m1, fontsize=7, color=RED, fontweight="bold")
        ax.text(x2 - 2.2, y2 + 0.8, m2, fontsize=7, color=RED, fontweight="bold")

    rel(grid["right"], 83, rain["left"], 83, "1", "*")
    rel(rain["right"], 83, hydro["left"], 83, "*", "1")
    rel(hydro["right"], 83, label["left"], 83, "1", "*")
    rel(grid["cx"], grid["bottom"], clf["cx"], clf["top"], "*", "1")
    rel(clf["right"], 46, hmm["left"], 46, "1", "1")
    rel(hmm["right"], 46, rmap["left"], 46, "1", "*")
    rel(rmap["right"], 46, evalr["left"], 46, "1", "1")
    rel(run["cx"], run["top"], clf["cx"], clf["bottom"], "1", "*")
    rel(ds["cx"], ds["top"], rmap["cx"], rmap["bottom"], "*", "*")
    rel(label["cx"], label["bottom"], hmm["cx"], hmm["top"], "*", "1")

    save(fig, "fig04_class.png")


# ---------------------------------------------------------------------------
# Figure 5: ERD
# ---------------------------------------------------------------------------
def fig_erd():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 72)
    ax.axis("off")
    ax.set_title("Figure 5. Entity-Relationship Diagram (Crow's-Foot Notation)",
                 fontsize=12, fontweight="bold", pad=10)

    def entity(x, y, name, fields, w=23):
        h = 4 + 2.6 * len(fields)
        ax.add_patch(Rectangle((x, y - h), w, h, facecolor=LIGHT, edgecolor="black", linewidth=1.3))
        ax.add_patch(Rectangle((x, y - 4), w, 4, facecolor=NAVY, edgecolor="black", linewidth=1.3))
        ax.text(x + w / 2, y - 2, name, ha="center", va="center", color="white", fontweight="bold", fontsize=8.5)
        for i, f in enumerate(fields):
            ax.text(x + 0.6, y - 5 - 2.6 * i, f, fontsize=7.0, va="center")
        return x, y, w, h

    def crow(x1, y1, x2, y2, left="1", right="N"):
        ax.plot([x1, x2], [y1, y2], color="black", linewidth=1)
        ax.text(x1, y1 + 1, left, fontsize=8, color=RED, fontweight="bold")
        ax.text(x2 - 2, y2 + 1, right, fontsize=8, color=RED, fontweight="bold")

    entity(2, 68, "GRID_CELLS",
           ["PK grid_id", "centroid_lat", "centroid_lon", "elevation_m", "slope_deg"])
    entity(38, 68, "RAINFALL_DAILY",
           ["PK obs_id", "FK grid_id", "obs_date", "rainfall_mm", "rain_7d_mm", "rain_14d_mm"])
    entity(74, 68, "PRESSURE_STATES",
           ["PK state_id", "FK grid_id", "obs_date", "state", "probability"])
    entity(2, 35, "HYDRO_EXPOSURE",
           ["PK feat_id", "FK grid_id", "dist_river_m", "road_density", "building_density"])
    entity(38, 35, "FLOOD_RISK_POLYGONS",
           ["PK poly_id", "source", "risk_class", "geometry"])
    entity(74, 35, "TRANSITIONS",
           ["PK trans_id", "FK run_id", "from_state", "to_state", "probability"])
    entity(2, 8, "MODEL_RUNS",
           ["PK run_id", "aoi", "grid_size_m", "period", "created_at"])
    entity(38, 8, "DATASETS",
           ["PK source", "kind", "licence", "checksum"])
    entity(74, 8, "EVALUATION_METRICS",
           ["PK metric_id", "FK run_id", "macro_f1", "high_recall", "spatial_overlap"])

    crow(2 + 23, 65, 38, 65, "1", "N")            # GRID 1-N RAINFALL
    crow(38 + 23, 65, 74, 65, "1", "N")           # RAINFALL 1-N PRESSURE (per day)
    crow(13, 68 - 17, 13, 35, "1", "N")           # GRID 1-N HYDRO
    crow(2 + 23, 33, 38, 33, "N", "N")            # HYDRO N-N FLOOD POLYGONS (intersection)
    crow(85, 68 - 17, 85, 35, "1", "N")           # PRESSURE relates to TRANSITIONS via run
    crow(13, 35 - 14, 13, 8, "1", "N")            # GRID via runs
    crow(2 + 23, 6, 38, 6, "N", "1")              # MODEL_RUNS use DATASETS
    crow(85, 35 - 14, 85, 8, "1", "N")            # RUN 1-N EVALUATION
    crow(20, 8, 74, 33, "1", "N")                 # RUN 1-N TRANSITIONS

    save(fig, "fig05_erd.png")


# ---------------------------------------------------------------------------
# Figure 6: Sequence Diagram - daily flood-pressure estimation
# ---------------------------------------------------------------------------
def fig_sequence():
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 80)
    ax.axis("off")
    ax.set_title("Figure 6. Sequence Diagram: Daily Flood-Pressure Estimation",
                 fontsize=12, fontweight="bold", pad=10)

    actors = ["Analyst", "Pipeline\nOrchestrator", "Data\nStore", "Feature\nEngine",
              "Classifier", "HMM\nLayer", "Map /\nReport"]
    xs = [8, 24, 40, 56, 70, 83, 95]
    top = 72
    bot = 6

    for x, a in zip(xs, actors):
        ax.add_patch(Rectangle((x - 5.5, top - 4), 11, 5, facecolor=LIGHT, edgecolor="black"))
        ax.text(x, top - 1.5, a, ha="center", va="center", fontsize=7.5, fontweight="bold")
        ax.plot([x, x], [top - 4, bot], color="black", linestyle="--", linewidth=0.8)

    def msg(y, x1, x2, label, dashed=False, color="black"):
        style = ":" if dashed else "-"
        ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>",
                                      mutation_scale=11, color=color,
                                      linestyle=style, linewidth=1.1))
        ax.text((x1 + x2) / 2, y + 1, label, fontsize=6.8, ha="center")

    def actbar(x, y1, y2):
        ax.add_patch(Rectangle((x - 1, y2), 2, y1 - y2, facecolor="white", edgecolor="black"))

    msg(66, xs[0], xs[1], "run(date, AOI)")
    actbar(xs[1], 66, 14)
    msg(61, xs[1], xs[2], "load grid + rainfall(date)")
    msg(56, xs[2], xs[1], "grid-cell-by-day rows", dashed=True)
    msg(51, xs[1], xs[3], "buildFeatures(rows)")
    actbar(xs[3], 51, 40)
    msg(46, xs[3], xs[2], "fetch terrain/hydrology/exposure")
    msg(41, xs[2], xs[3], "static features", dashed=True)
    msg(36, xs[3], xs[1], "feature matrix", dashed=True)
    msg(31, xs[1], xs[4], "predict(features)")
    msg(27, xs[4], xs[1], "state + probability", dashed=True)
    msg(22, xs[1], xs[5], "smooth(sequence)")
    msg(18, xs[5], xs[1], "next-step transitions", dashed=True)
    msg(13, xs[1], xs[6], "render map + metrics")
    msg(8, xs[6], xs[0], "risk map / report", dashed=True)

    save(fig, "fig06_sequence.png")


# ---------------------------------------------------------------------------
# Figure 7: Gantt Chart - 24 May to 28 July 2026
# ---------------------------------------------------------------------------
def fig_gantt():
    tasks = [
        ("Literature review & study-area selection", "2026-05-24", "2026-06-07"),
        ("Data acquisition (CHIRPS, SRTM, OSM, polygons)", "2026-05-31", "2026-06-14"),
        ("Grid creation & geospatial feature engineering", "2026-06-07", "2026-06-21"),
        ("Rainfall features & flood-pressure labelling", "2026-06-14", "2026-06-28"),
        ("Baseline & ML classifier training", "2026-06-21", "2026-07-12"),
        ("HMM temporal-layer integration", "2026-07-05", "2026-07-19"),
        ("Evaluation, spatial validation & mapping", "2026-07-12", "2026-07-22"),
        ("Dashboard / notebook & sensitivity analysis", "2026-07-15", "2026-07-24"),
        ("Results analysis & write-up", "2026-07-18", "2026-07-26"),
        ("Final submission & defence prep", "2026-07-22", "2026-07-28"),
    ]
    fig, ax = plt.subplots(figsize=(11, 5.8))
    colors = [NAVY, BLUE, GREEN, "#2e7d32", RED, AMBER, "#8e24aa", "#00838f", GREY, "black"]
    for i, (name, s, e) in enumerate(tasks):
        sd = datetime.strptime(s, "%Y-%m-%d")
        ed = datetime.strptime(e, "%Y-%m-%d")
        days = (ed - sd).days
        ax.barh(i, days, left=sd, color=colors[i], edgecolor="black", height=0.55)
        ax.text(ed, i, f"  {days}d", va="center", ha="left", fontsize=7.5, color=GREY)
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([t[0] for t in tasks], fontsize=8)
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_xlim(datetime(2026, 5, 22), datetime(2026, 7, 30))
    ax.grid(axis="x", linestyle=":", color="#cccccc")
    ax.set_title("Figure 7. Project Gantt Chart (24 May 2026 - 28 July 2026)",
                 fontsize=12, fontweight="bold", pad=10)
    ax.axvline(datetime(2026, 7, 28), color=RED, linestyle="--", linewidth=1.2)
    ax.text(datetime(2026, 7, 28), -0.7, " Submission", color=RED, fontsize=8, fontweight="bold")
    plt.tight_layout()
    save(fig, "fig07_gantt.png")


# ---------------------------------------------------------------------------
# Figure 8: Research Design / SDLC model
# ---------------------------------------------------------------------------
def fig_sdlc():
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    ax.axis("off")
    ax.set_title("Figure 8. Iterative Agile-Scrum Development Model Adapted for the Project",
                 fontsize=12, fontweight="bold", pad=10)
    phases = [("Sprint 0\nData & Scope", NAVY),
              ("Feature\nEngineering", BLUE),
              ("Model\nBuild", GREEN),
              ("Evaluation\n& Mapping", AMBER),
              ("Review &\nValidation", RED),
              ("Refactor &\nDocument", GREY)]
    width = 14
    gap = 2
    start = 4
    for i, (label, color) in enumerate(phases):
        x = start + i * (width + gap)
        ax.add_patch(FancyBboxPatch((x, 15), width, 12, boxstyle="round,pad=0.3",
                                     facecolor=color, edgecolor="black"))
        ax.text(x + width / 2, 21, label, ha="center", va="center", color="white",
                fontsize=9, fontweight="bold")
        if i < len(phases) - 1:
            ax.add_patch(FancyArrowPatch((x + width, 21), (x + width + gap, 21),
                                          arrowstyle="-|>", mutation_scale=12, linewidth=1.4))
    ax.add_patch(FancyArrowPatch((92, 14), (10, 14),
                                  arrowstyle="-|>", mutation_scale=14,
                                  connectionstyle="arc3,rad=-0.25", color=RED, linewidth=1.5))
    ax.text(50, 4, "Continuous feedback loop (every 2-week sprint)", ha="center",
            color=RED, fontsize=9, fontweight="bold")
    save(fig, "fig08_sdlc.png")


if __name__ == "__main__":
    fig_architecture()
    fig_hmm_states()
    fig_use_case()
    fig_class_diagram()
    fig_erd()
    fig_sequence()
    fig_gantt()
    fig_sdlc()
    print("DONE")
