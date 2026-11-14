"""Extrai a malha viária dirigível de Aracaju-SE de um extrato OSM (.pbf).

Fonte: extrato "nordeste" da Geofabrik (dados © colaboradores do
OpenStreetMap, licença ODbL 1.0). Uso:

    python scripts/build_osm_graph.py <nordeste-AAMMDD.osm.pbf> data/aracaju/aracaju_drive.npz

Etapas:
1. Localiza a relação administrativa ``boundary=administrative``,
   ``admin_level=8``, ``name=Aracaju`` e monta o polígono do município.
2. Seleciona vias com ``highway`` dirigível (mesmo conjunto usado pelo filtro
   "drive" do OSMnx, simplificado), respeitando ``oneway``.
3. Mantém nós dentro do polígono, calcula comprimentos (haversine) e conserva
   a maior componente fortemente conexa.
4. Salva arrays (lat, lon, u, v, length_m, junction) e metadados.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import osmium
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from shapely import wkb as shp_wkb
from shapely.prepared import prep

DRIVE = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
         "residential", "living_street", "motorway_link", "trunk_link",
         "primary_link", "secondary_link", "tertiary_link", "road", "service"}
EXCLUDE_SERVICE = {"parking_aisle", "driveway", "drive-through", "parking", "emergency_access"}


def find_boundary(pbf: str):
    fab = osmium.geom.WKBFactory()
    fp = osmium.FileProcessor(pbf).with_areas(osmium.filter.TagFilter(("boundary", "administrative")))
    fp = fp.with_filter(osmium.filter.EntityFilter(osmium.osm.AREA))
    for obj in fp:
        if obj.tags.get("admin_level") == "8" and obj.tags.get("name") == "Aracaju" \
                and not obj.from_way():
            return shp_wkb.loads(fab.create_multipolygon(obj), hex=True), obj.orig_id()
    raise RuntimeError("limite municipal de Aracaju não encontrado")


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371008.8
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def main(pbf: str, out: str) -> None:
    poly, rel_id = find_boundary(pbf)
    minx, miny, maxx, maxy = poly.bounds
    ppoly = prep(poly)
    print(f"limite: relação {rel_id}, bbox lon[{minx:.4f},{maxx:.4f}] lat[{miny:.4f},{maxy:.4f}]")

    ways = []  # (list of (id, lat, lon), oneway)
    fp = osmium.FileProcessor(pbf, osmium.osm.WAY | osmium.osm.NODE).with_locations()
    fp = fp.with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
    fp = fp.with_filter(osmium.filter.KeyFilter("highway"))
    for w in fp:
        hw = w.tags.get("highway")
        if hw not in DRIVE:
            continue
        if hw == "service" and w.tags.get("service") in EXCLUDE_SERVICE:
            continue
        if w.tags.get("access") in ("private", "no") or w.tags.get("area") == "yes":
            continue
        try:
            pts = [(n.ref, n.lat, n.lon) for n in w.nodes]
        except osmium.InvalidLocationError:
            continue
        if not any(minx <= lo <= maxx and miny <= la <= maxy for _, la, lo in pts):
            continue
        ow = w.tags.get("oneway", "no")
        junction = w.tags.get("junction", "")
        oneway = 1 if ow in ("yes", "true", "1") or junction == "roundabout" \
            or hw in ("motorway",) else (-1 if ow == "-1" else 0)
        ways.append((pts, oneway))
    print(f"vias candidatas: {len(ways)}")

    from shapely.geometry import Point
    inside: dict[int, bool] = {}
    coord: dict[int, tuple[float, float]] = {}
    use_count: dict[int, int] = {}
    for pts, _ in ways:
        for k, (nid, la, lo) in enumerate(pts):
            if nid not in inside:
                inside[nid] = ppoly.contains(Point(lo, la))
                coord[nid] = (la, lo)
            inc = 2 if k in (0, len(pts) - 1) else 1
            use_count[nid] = use_count.get(nid, 0) + inc

    edges = []
    for pts, oneway in ways:
        for (a, la1, lo1), (b, la2, lo2) in zip(pts[:-1], pts[1:]):
            if not (inside[a] and inside[b]):
                continue
            L = float(haversine_m(la1, lo1, la2, lo2))
            if oneway >= 0:
                edges.append((a, b, L))
            if oneway <= 0:
                edges.append((b, a, L))
    ids = sorted({e[0] for e in edges} | {e[1] for e in edges})
    idx = {nid: k for k, nid in enumerate(ids)}
    u = np.array([idx[e[0]] for e in edges], np.int32)
    v = np.array([idx[e[1]] for e in edges], np.int32)
    L = np.array([e[2] for e in edges], np.float64)
    n = len(ids)
    g = csr_matrix((np.ones_like(L), (u, v)), shape=(n, n))
    ncomp, lab = connected_components(g, directed=True, connection="strong")
    big = np.argmax(np.bincount(lab))
    keep = lab == big
    remap = -np.ones(n, np.int64)
    remap[keep] = np.arange(keep.sum())
    m = keep[u] & keep[v]
    u2, v2, L2 = remap[u[m]], remap[v[m]], L[m]
    kept_ids = np.array(ids)[keep]
    lat = np.array([coord[i][0] for i in kept_ids])
    lon = np.array([coord[i][1] for i in kept_ids])
    junction = np.array([use_count[i] >= 2 for i in kept_ids])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, lat=lat, lon=lon, u=u2.astype(np.int32), v=v2.astype(np.int32),
                        length_m=L2, junction=junction, osm_id=kept_ids.astype(np.int64),
                        meta_source=np.array(Path(pbf).name),
                        meta_boundary_relation=np.array(str(rel_id)),
                        meta_license=np.array("ODbL 1.0 - (c) OpenStreetMap contributors"),
                        meta_boundary_wkt_bounds=np.array(str(poly.bounds)))
    print(f"nós: {n} → {keep.sum()} (maior CFC de {ncomp}); arcos: {len(L2)}; "
          f"km de arcos: {L2.sum()/1000:.1f}; junções: {junction.sum()}")
    # contorno municipal para figuras
    import json
    from shapely.geometry import mapping
    Path(out).with_suffix(".boundary.geojson").write_text(json.dumps(mapping(poly)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
