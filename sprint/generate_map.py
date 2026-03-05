"""
generate_map.py — Extract a real street network via OSMnx and export as JSON
for Sprint's routing visualizer.

Usage:
    python generate_map.py

Output:
    city.json  — nodes (id, x, y normalised 0-1), edges (u, v, length, highway)
"""

import json
import osmnx as ox

# ── Config ────────────────────────────────────────────────────────────────────
CITY_LABEL  = "Manhattan, New York"
CENTER_LAT  = 40.7178   # Canal St area — nice mix of grid + irregular streets
CENTER_LON  = -74.0020
DIST_M      = 1200      # radius in metres
NETWORK     = "drive"
OUTPUT      = "city.json"

# Road types to export (in rendering order, thin→thick)
ROAD_RANKS = {
    "motorway":      5,
    "trunk":         4,
    "primary":       3,
    "secondary":     2,
    "tertiary":      1,
    "residential":   0,
    "unclassified":  0,
    "living_street": 0,
    "service":       0,
}

def road_rank(highway):
    if isinstance(highway, list):
        highway = highway[0]
    return ROAD_RANKS.get(highway, 0)

# ── Fetch & project ───────────────────────────────────────────────────────────
print(f"Fetching street network for {CITY_LABEL} ({DIST_M}m radius)…")
G = ox.graph_from_point(
    (CENTER_LAT, CENTER_LON),
    dist=DIST_M,
    network_type=NETWORK,
    simplify=True,
)
G = ox.project_graph(G)

nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
print(f"  Raw: {len(nodes_gdf)} nodes, {len(edges_gdf)} edges")

# ── Normalise coordinates to [0, 1] ──────────────────────────────────────────
x_vals = nodes_gdf.geometry.x
y_vals = nodes_gdf.geometry.y
x_min, x_max = x_vals.min(), x_vals.max()
y_min, y_max = y_vals.min(), y_vals.max()
span = max(x_max - x_min, y_max - y_min)  # keep aspect ratio

def norm_x(x):
    return (x - x_min) / span

def norm_y(y):
    # flip so north = top
    return 1.0 - (y - y_min) / span

# ── Build node dict ───────────────────────────────────────────────────────────
node_dict = {}
for nid, row in nodes_gdf.iterrows():
    node_dict[str(nid)] = {
        "x": round(norm_x(row.geometry.x), 6),
        "y": round(norm_y(row.geometry.y), 6),
    }

# ── Build edge list (undirected — add both directions for usability) ──────────
seen = set()
edge_list = []
for (u, v, _), row in edges_gdf.iterrows():
    su, sv = str(u), str(v)
    # deduplicate reverse duplicates
    key = (min(su, sv), max(su, sv))
    if key in seen:
        continue
    seen.add(key)

    highway = row.get("highway", "unclassified")
    edge_list.append({
        "u": su,
        "v": sv,
        "len": round(float(row.get("length", 1.0)), 1),
        "rank": road_rank(highway),
    })

print(f"  Exported: {len(node_dict)} nodes, {len(edge_list)} edges")

# ── Write ─────────────────────────────────────────────────────────────────────
output = {
    "city":  CITY_LABEL,
    "nodes": node_dict,
    "edges": edge_list,
}

with open(OUTPUT, "w") as f:
    json.dump(output, f, separators=(",", ":"))

size_kb = len(json.dumps(output).encode()) / 1024
print(f"  Saved {OUTPUT}  ({size_kb:.1f} KB)")
