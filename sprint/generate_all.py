"""
generate_all.py — batch-generate city JSON + PNG files for Sprint.
One JSON + one PNG per city, saved as sprint/{slug}.json and sprint/{slug}.png

Usage:
    python generate_all.py [slug1 slug2 ...]   # generate specific cities
    python generate_all.py                      # generate all
"""

import json, sys, os
import matplotlib
matplotlib.use('Agg')   # non-interactive backend — must come before pyplot
import matplotlib.pyplot as plt
import matplotlib.collections as mc
import osmnx as ox

CITIES = [
    {"slug": "manhattan",     "label": "Manhattan",     "lat":  40.7178,  "lon":  -74.0020,  "dist": 1200, "net": "drive"},
    {"slug": "san-francisco", "label": "San Francisco", "lat":  37.7870,  "lon": -122.4010,  "dist": 1000, "net": "drive"},
    {"slug": "barcelona",     "label": "Barcelona",     "lat":  41.3851,  "lon":    2.1734,  "dist": 1000, "net": "drive"},
    {"slug": "venice",        "label": "Venice",        "lat":  45.4341,  "lon":   12.3380,  "dist":  500, "net": "walk"},
    {"slug": "tokyo",         "label": "Tokyo",         "lat":  35.6896,  "lon":  139.7006,  "dist": 1000, "net": "drive"},
    {"slug": "mumbai",        "label": "Mumbai",        "lat":  18.9320,  "lon":   72.8350,  "dist":  900, "net": "drive"},
    {"slug": "marrakech",     "label": "Marrakech",     "lat":  31.6295,  "lon":   -7.9811,  "dist":  550, "net": "walk"},
    {"slug": "singapore",     "label": "Singapore",     "lat":   1.2810,  "lon":  103.8476,  "dist": 1000, "net": "drive"},
    {"slug": "melbourne",     "label": "Melbourne",     "lat": -37.8136,  "lon":  144.9631,  "dist": 1000, "net": "drive"},
    {"slug": "dubai",         "label": "Dubai",         "lat":  25.1976,  "lon":   55.2796,  "dist": 1200, "net": "drive"},
    {"slug": "seattle",       "label": "Seattle",       "lat":  47.6062,  "lon": -122.3321,  "dist": 1000, "net": "drive"},
]

ROAD_RANKS = {
    "motorway": 5, "trunk": 4, "primary": 3, "secondary": 2,
    "tertiary": 1, "residential": 0, "unclassified": 0,
    "living_street": 0, "service": 0, "pedestrian": 0,
    "footway": 0, "path": 0, "steps": 0,
}

# Road styles per rank: (RGBA tuple, linewidth)
# Base color: #88c4f7 = rgb(0.533, 0.769, 0.969)
_C = (0.533, 0.769, 0.969)
ROAD_STYLES = [
    ((*_C, 0.12), 0.40),   # rank 0 - residential/footway
    ((*_C, 0.20), 0.60),   # rank 1 - tertiary
    ((*_C, 0.32), 0.90),   # rank 2 - secondary
    ((*_C, 0.48), 1.40),   # rank 3 - primary
    ((*_C, 0.65), 2.00),   # rank 4 - trunk
    ((*_C, 0.85), 2.80),   # rank 5 - motorway
]

IMG_DPI    = 150
IMG_MAX_IN = 8.0   # max image dimension in inches

def road_rank(hw):
    if isinstance(hw, list): hw = hw[0]
    return ROAD_RANKS.get(str(hw), 0)

def generate(city):
    slug  = city["slug"]
    label = city["label"]
    out_json = f"{slug}.json"
    out_png  = f"{slug}.png"

    print(f"[{slug}] fetching {city['dist']}m {city['net']} network...", flush=True)
    try:
        G = ox.graph_from_point(
            (city["lat"], city["lon"]),
            dist=city["dist"],
            network_type=city["net"],
            simplify=True,
        )
        G = ox.project_graph(G)
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    x_vals = nodes_gdf.geometry.x
    y_vals = nodes_gdf.geometry.y
    x_min, x_max = float(x_vals.min()), float(x_vals.max())
    y_min, y_max = float(y_vals.min()), float(y_vals.max())
    x_range = x_max - x_min
    y_range = y_max - y_min
    aspect  = x_range / y_range  # width / height ratio

    # Per-axis normalization: both x and y span exactly [0, 1]
    node_dict = {
        str(nid): {
            "x": round((row.geometry.x - x_min) / x_range, 6),
            "y": round(1.0 - (row.geometry.y - y_min) / y_range, 6),
        }
        for nid, row in nodes_gdf.iterrows()
    }

    seen, edge_list = set(), []
    for (u, v, _), row in edges_gdf.iterrows():
        su, sv = str(u), str(v)
        key = (min(su, sv), max(su, sv))
        if key in seen: continue
        seen.add(key)
        edge_list.append({
            "u": su, "v": sv,
            "len": round(float(row.get("length", 1.0)), 1),
            "rank": road_rank(row.get("highway", "unclassified")),
        })

    data = {"city": label, "aspect": round(aspect, 6), "nodes": node_dict, "edges": edge_list}
    with open(out_json, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    kb = os.path.getsize(out_json) / 1024
    print(f"  {len(node_dict)} nodes, {len(edge_list)} edges -> {out_json} ({kb:.0f} KB)", flush=True)

    # ── Render PNG ────────────────────────────────────────────────────────────
    print(f"  rendering {out_png}...", flush=True)

    fig_w = IMG_MAX_IN if aspect >= 1.0 else IMG_MAX_IN * aspect
    fig_h = IMG_MAX_IN / aspect if aspect >= 1.0 else IMG_MAX_IN

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor='#010008')
    ax  = fig.add_axes([0, 0, 1, 1], facecolor='#010008')
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('auto')
    ax.axis('off')

    # Group edge geometry segments by road rank
    segments_by_rank = [[] for _ in range(6)]
    for (u, v, _), row in edges_gdf.iterrows():
        rank = road_rank(row.get("highway", "unclassified"))
        geom = row.get("geometry")
        if geom is None:
            continue
        try:
            coords = list(geom.coords)
            for i in range(len(coords) - 1):
                segments_by_rank[rank].append([coords[i], coords[i + 1]])
        except Exception:
            continue

    for rank, segs in enumerate(segments_by_rank):
        if not segs:
            continue
        color, lw = ROAD_STYLES[rank]
        lc = mc.LineCollection(segs, colors=[color], linewidths=lw, capstyle='round')
        ax.add_collection(lc)

    plt.savefig(out_png, dpi=IMG_DPI, facecolor='#010008')
    plt.close(fig)

    img_kb = os.path.getsize(out_png) / 1024
    print(f"  -> {out_png} ({img_kb:.0f} KB)", flush=True)

# ─────────────────────────────────────────────────────────────
targets = sys.argv[1:] if len(sys.argv) > 1 else [c["slug"] for c in CITIES]
for city in CITIES:
    if city["slug"] in targets:
        generate(city)

print("done.")
