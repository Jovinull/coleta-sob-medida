"""Geometria dos cenários: localização dos contêineres, depósito e distâncias.

Dois tipos de cenário são suportados:

* ``synthetic`` — quadrado de lado ``area_km``; distância de viagem =
  distância euclidiana × fator de tortuosidade (``circuity``). Útil para
  controlar a distribuição espacial isoladamente.
* ``osm`` — malha viária dirigível extraída do OpenStreetMap (recorte da área
  urbana de Aracaju-SE, ver ``scripts/build_osm_graph.py``). Os contêineres
  são posicionados em nós da malha sorteados; **as posições são hipotéticas**
  e não representam equipamentos existentes. Distâncias são caminhos mínimos
  na malha dirigida (respeitando sentidos de via).

O índice 0 é sempre o depósito.
"""
from __future__ import annotations

import dataclasses as dc

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from .config import GeoCfg


@dc.dataclass
class Geography:
    xy_km: np.ndarray            # (N+1, 2) coordenadas planas em km
    dist_km: np.ndarray          # (N+1, N+1) distâncias de viagem (pode ser assimétrica)
    latlon: np.ndarray | None = None   # (N+1, 2) se cenário OSM
    node_ids: np.ndarray | None = None  # índices dos nós da malha (OSM)
    kind: str = "synthetic"

    @property
    def n(self) -> int:
        return self.dist_km.shape[0] - 1


# --------------------------------------------------------------------------
def _sample_layout(rng: np.random.Generator, cfg: GeoCfg, n: int,
                   lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Amostra n pontos no retângulo [lo, hi] (km) segundo o layout."""
    if cfg.layout == "uniform":
        return rng.uniform(lo, hi, size=(n, 2))
    if cfg.layout == "clustered":
        span = hi - lo
        centers = rng.uniform(lo + 0.15 * span, hi - 0.15 * span, size=(cfg.n_clusters, 2))
        weights = rng.dirichlet(np.full(cfg.n_clusters, 2.0))
        lab = rng.choice(cfg.n_clusters, size=n, p=weights)
        pts = centers[lab] + rng.normal(0, cfg.cluster_sigma_km, size=(n, 2))
        return np.clip(pts, lo, hi)
    raise ValueError(f"layout desconhecido: {cfg.layout}")


def synthetic(cfg: GeoCfg, rng: np.random.Generator) -> Geography:
    n, L = cfg.n_containers, cfg.area_km
    lo, hi = np.zeros(2), np.full(2, L)
    pts = _sample_layout(rng, cfg, n, lo, hi)
    depot = np.array([L / 2, L / 2]) if cfg.depot == "center" else np.array([0.0, L / 2])
    xy = np.vstack([depot, pts])
    diff = xy[:, None, :] - xy[None, :, :]
    d = np.sqrt((diff ** 2).sum(-1)) * cfg.circuity
    return Geography(xy_km=xy, dist_km=d, kind="synthetic")


# --------------------------------------------------------------------------
class RoadNetwork:
    """Malha viária carregada de um arquivo .npz gerado por build_osm_graph."""

    def __init__(self, path: str):
        z = np.load(path, allow_pickle=False)
        self.lat = z["lat"]
        self.lon = z["lon"]
        self.u = z["u"]
        self.v = z["v"]
        self.length_m = z["length_m"]
        self.junction = z["junction"] if "junction" in z.files else np.ones(len(self.lat), bool)
        n = len(self.lat)
        self.graph = csr_matrix((self.length_m, (self.u, self.v)), shape=(n, n))
        # projeção equiretangular local (km)
        self.lat0, self.lon0 = float(np.mean(self.lat)), float(np.mean(self.lon))
        kx = 111.320 * np.cos(np.radians(self.lat0))
        self.x = (self.lon - self.lon0) * kx
        self.y = (self.lat - self.lat0) * 110.574
        self.meta = {k: str(z[k]) for k in z.files if k.startswith("meta_")}

    def nearest_node(self, lat: float, lon: float) -> int:
        kx = 111.320 * np.cos(np.radians(self.lat0))
        x, y = (lon - self.lon0) * kx, (lat - self.lat0) * 110.574
        return int(np.argmin((self.x - x) ** 2 + (self.y - y) ** 2))

    def shortest(self, sources: np.ndarray, return_predecessors: bool = False):
        return dijkstra(self.graph, directed=True, indices=sources,
                        return_predecessors=return_predecessors)


_NET_CACHE: dict[str, RoadNetwork] = {}


def load_network(path: str) -> RoadNetwork:
    if path not in _NET_CACHE:
        _NET_CACHE[path] = RoadNetwork(path)
    return _NET_CACHE[path]


def osm(cfg: GeoCfg, rng: np.random.Generator) -> Geography:
    net = load_network(cfg.osm_graph)
    depot = net.nearest_node(*cfg.osm_depot_latlon)
    junc = np.nonzero(net.junction)[0]       # candidatos: interseções da malha
    if cfg.layout == "uniform":
        # uniforme sobre interseções: acompanha a densidade de ruas
        cand = rng.choice(junc, size=min(len(junc), cfg.n_containers * 3), replace=False)
    else:
        # centros sorteados entre interseções; pontos gaussianos ao redor,
        # projetados na interseção mais próxima
        jx, jy = net.x[junc], net.y[junc]
        centers = rng.choice(junc, size=cfg.n_clusters, replace=False)
        w = rng.dirichlet(np.full(cfg.n_clusters, 2.0))
        lab = rng.choice(cfg.n_clusters, size=cfg.n_containers * 3, p=w)
        px = net.x[centers][lab] + rng.normal(0, cfg.cluster_sigma_km, lab.size)
        py = net.y[centers][lab] + rng.normal(0, cfg.cluster_sigma_km, lab.size)
        cand = np.array([junc[np.argmin((jx - a) ** 2 + (jy - b) ** 2)] for a, b in zip(px, py)])
    # remove duplicatas e o próprio depósito, preservando a ordem sorteada
    _, first = np.unique(cand, return_index=True)
    cand = cand[np.sort(first)]
    cand = cand[cand != depot][: cfg.n_containers]
    if len(cand) < cfg.n_containers:
        raise RuntimeError("malha insuficiente para o número de contêineres")
    nodes = np.concatenate([[depot], cand])
    dist = net.shortest(nodes)[:, nodes] / 1000.0
    if not np.all(np.isfinite(dist)):
        raise RuntimeError("malha não fortemente conexa entre os nós sorteados")
    xy = np.column_stack([net.x[nodes], net.y[nodes]])
    latlon = np.column_stack([net.lat[nodes], net.lon[nodes]])
    return Geography(xy_km=xy, dist_km=dist, latlon=latlon, node_ids=nodes, kind="osm")


def build(cfg: GeoCfg, rng: np.random.Generator) -> Geography:
    if cfg.kind == "synthetic":
        return synthetic(cfg, rng)
    if cfg.kind == "osm":
        return osm(cfg, rng)
    raise ValueError(cfg.kind)


def street_paths(geo: Geography, cfg: GeoCfg, routes: list[list[int]]) -> list[list[tuple[float, float]]]:
    """Polilinhas (lat, lon) das rotas pela malha: depósito → contêineres → depósito.

    ``routes`` usa índices de contêiner 0..N-1. Somente para cenários OSM; nos
    sintéticos, devolve segmentos retos em coordenadas planas (km).
    """
    out = []
    if geo.kind != "osm":
        for r in routes:
            pts = [0, *[c + 1 for c in r], 0]
            out.append([tuple(geo.xy_km[p]) for p in pts])
        return out
    net = load_network(cfg.osm_graph)
    key = id(geo)
    cache = _PRED_CACHE.get(key)
    if cache is None:
        _, pred = net.shortest(geo.node_ids, return_predecessors=True)
        cache = _PRED_CACHE[key] = pred
    pred = cache
    for r in routes:
        pts = [0, *[c + 1 for c in r], 0]
        poly = []
        for a, b in zip(pts[:-1], pts[1:]):
            src, dst = geo.node_ids[a], geo.node_ids[b]
            seq = [dst]
            while seq[-1] != src and seq[-1] >= 0:
                seq.append(pred[a, seq[-1]])
            seq.reverse()
            poly.extend((float(net.lat[k]), float(net.lon[k])) for k in seq if k >= 0)
        out.append(poly)
    return out


_PRED_CACHE: dict[int, np.ndarray] = {}
