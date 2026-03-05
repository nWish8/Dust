"""
generate_pngs.py — Regenerate Sprint city PNGs in maptoposter style.

Adds water bodies, parks, and double-stroke roads on top of the existing
generate_all.py city configs/coordinate system.

Usage (from repo root):
    .venv/Scripts/python.exe sprint/generate_pngs.py [slug1 slug2 ...]
    .venv/Scripts/python.exe sprint/generate_pngs.py   # all cities

Output: sprint/{slug}.png (overwrites existing)
"""

import sys, os
import matplotlib
matplotlib.use('Agg')
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

# rank -> (outline_lw, surface_lw, surface_rgba)
# outline color is always '#030318'
_B = (136/255, 196/255, 247/255)
ROAD_STYLES = {
    5: (2.4, 2.0, (*_B, 1.00)),  # motorway
    4: (2.0, 1.6, (*_B, 0.92)),  # trunk
    3: (1.6, 1.3, (*_B, 0.80)),  # primary
    2: (1.2, 1.0, (*_B, 0.65)),  # secondary
    1: (0.8, 0.7, (*_B, 0.50)),  # tertiary
    0: (None, 0.55, (*_B, 0.32)), # residential — no outline
}

IMG_DPI    = 150
IMG_MAX_IN = 8.0

BG_COLOR    = '#0d0d1f'
OUTLINE_COLOR = '#030318'
WATER_COLOR = (40/255, 80/255, 140/255, 0.85)
PARKS_COLOR = (4/255, 16/255, 8/255, 0.92)

def road_rank(hw):
    if isinstance(hw, list): hw = hw[0]
    return ROAD_RANKS.get(str(hw), 0)

def generate(city):
    slug  = city["slug"]
    lat, lon = city["lat"], city["lon"]
    dist  = city["dist"]
    out_png = f"{slug}.png"

    print(f"[{slug}] fetching {dist}m {city['net']} network...", flush=True)
    try:
        G = ox.graph_from_point((lat, lon), dist=dist, network_type=city["net"], simplify=True)
        G = ox.project_graph(G)
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
    except Exception as e:
        print(f"  ERROR fetching network: {e}")
        return

    graph_crs = G.graph['crs']
    x_vals = nodes_gdf.geometry.x
    y_vals = nodes_gdf.geometry.y
    x_min, x_max = float(x_vals.min()), float(x_vals.max())
    y_min, y_max = float(y_vals.min()), float(y_vals.max())
    x_range = x_max - x_min
    y_range = y_max - y_min
    aspect  = x_range / y_range

    fig_w = IMG_MAX_IN if aspect >= 1.0 else IMG_MAX_IN * aspect
    fig_h = IMG_MAX_IN / aspect if aspect >= 1.0 else IMG_MAX_IN

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=BG_COLOR)
    ax  = fig.add_axes([0, 0, 1, 1], facecolor=BG_COLOR)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('auto')
    ax.axis('off')

    # ── Water ─────────────────────────────────────────────────────────────────
    try:
        print(f"  fetching water...", flush=True)
        water = ox.features_from_point(
            (lat, lon), dist=dist,
            tags={"natural": ["water", "bay"], "waterway": ["river", "riverbank", "canal"]},
        )
        water = water.to_crs(graph_crs)
        polys = water[water.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
        if len(polys):
            polys.plot(ax=ax, color=WATER_COLOR, linewidth=0, zorder=1)
            print(f"    {len(polys)} water polys", flush=True)
    except Exception as e:
        print(f"    no water: {e}", flush=True)

    # ── Parks ─────────────────────────────────────────────────────────────────
    try:
        print(f"  fetching parks...", flush=True)
        parks = ox.features_from_point(
            (lat, lon), dist=dist,
            tags={"leisure": "park", "landuse": ["grass", "park"]},
        )
        parks = parks.to_crs(graph_crs)
        polys = parks[parks.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
        if len(polys):
            polys.plot(ax=ax, color=PARKS_COLOR, linewidth=0, zorder=2)
            print(f"    {len(polys)} park polys", flush=True)
    except Exception as e:
        print(f"    no parks: {e}", flush=True)

    # ── Roads — double stroke: outline then surface ───────────────────────────
    print(f"  rendering roads...", flush=True)
    segs_by_rank = {r: [] for r in range(6)}
    for _, row in edges_gdf.iterrows():
        rank = road_rank(row.get("highway", "unclassified"))
        geom = row.get("geometry")
        if geom is None:
            continue
        try:
            coords = list(geom.coords)
            for i in range(len(coords) - 1):
                segs_by_rank[rank].append([coords[i], coords[i + 1]])
        except Exception:
            continue

    # Outline pass (all ranks low→high)
    for rank in range(6):
        outline_lw, _, _ = ROAD_STYLES[rank]
        segs = segs_by_rank[rank]
        if not segs or outline_lw is None:
            continue
        lc = mc.LineCollection(segs, colors=OUTLINE_COLOR, linewidths=outline_lw,
                               capstyle='round', joinstyle='round', zorder=3 + rank * 2)
        ax.add_collection(lc)

    # Surface pass
    for rank in range(6):
        _, surface_lw, surface_rgba = ROAD_STYLES[rank]
        segs = segs_by_rank[rank]
        if not segs:
            continue
        lc = mc.LineCollection(segs, colors=[surface_rgba], linewidths=surface_lw,
                               capstyle='round', joinstyle='round', zorder=4 + rank * 2)
        ax.add_collection(lc)

    plt.savefig(out_png, dpi=IMG_DPI, facecolor=BG_COLOR)
    plt.close(fig)

    img_kb = os.path.getsize(out_png) / 1024
    print(f"  -> {out_png} ({img_kb:.0f} KB)", flush=True)

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    targets = sys.argv[1:] if len(sys.argv) > 1 else [c["slug"] for c in CITIES]
    for city in CITIES:
        if city["slug"] in targets:
            generate(city)
    print("done.")
