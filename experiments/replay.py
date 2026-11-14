"""Gera traços gravados para o painel (replay A × D) e para as animações.

    python -m experiments.replay

Saídas (experiments/results/):
* replay.json      — A e D, mesma semente, N = 100, 7 dias avaliados (painel e animações C/D)
* trace_falha.npz  — política C sob interrupção regional de 48 h (animação E)
Os traços vêm de execuções reais do simulador; nada é editado.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from wastesim.config import ScenarioConfig
from wastesim.geo import street_paths
from wastesim.simulation import Simulation
from wastesim.telemetry import device_id

OUT = Path(__file__).parent / "results"
SEED = 1001
BASE = {"seed": SEED, "geo": {"kind": "osm", "n_containers": 100},
        "time": {"warmup_days": 7, "eval_days": 7}, "record_trace": True}


def run(policy: str, extra: dict | None = None):
    cfg = ScenarioConfig.from_dict({**BASE, "policy": {"name": policy}, **(extra or {})})
    sim = Simulation(cfg)
    res = sim.run()
    return sim, res


def export_replay():
    runs = []
    first = None
    labels = {"A": "periódica fixa", "D": "preditiva"}
    for pol in ("A", "D"):
        sim, res = run(pol)
        tr = sim.trace
        t = np.array(tr["t"])
        keep = np.nonzero(t >= sim.cfg.time.warmup_days * 86400)[0]
        ll = sim.geo.latlon
        trucks = []
        for k in keep:
            trucks.append([[round(float(ll[p, 0]), 5), round(float(ll[p, 1]), 5), v]
                           for v, p, done in tr["trucks"][k] if not done and p != 0])
        paths = {}
        for d in tr["routes"]:
            if d["day"] >= sim.cfg.time.warmup_days:
                paths[str(d["day"])] = [[(round(a, 5), round(b, 5)) for a, b in poly]
                                       for poly in street_paths(sim.geo, sim.cfg.geo, d["routes"])]
        k0 = np.array(tr["kpi"][keep[0]])
        kpi = [[round(a - k0[0], 2), int(b - k0[1]), round(c - k0[2], 3), int(e)]
               for a, b, c, e in (tr["kpi"][k] for k in keep)]
        runs.append(dict(policy=pol, label=labels[pol],
                         fill=[np.round(tr["fill"][k], 3).tolist() for k in keep],
                         est=[np.round(tr["est"][k], 3).tolist() for k in keep],
                         trucks=trucks, paths=paths, kpi=kpi,
                         summary={k: res[k] for k in ("km_per_day", "overflow_pct", "visits_per_day")}))
        first = first or (sim, t[keep])
    sim, tk = first
    ll = sim.geo.latlon
    data = dict(seed=SEED, n=sim.n, depot=[float(ll[0, 0]), float(ll[0, 1])],
                containers=[dict(id=device_id(i), lat=float(ll[i + 1, 0]), lon=float(ll[i + 1, 1]))
                            for i in range(sim.n)],
                frames_t=tk.tolist(), runs=runs,
                note=(f"Traço gravado de execuções reais do simulador (semente {SEED}, N = {sim.n}, "
                      "7 dias após 7 de aquecimento). Mesmas demandas nas duas políticas. "
                      "Cores: ocupação verdadeira. Posições de contêineres e depósito hipotéticas."))
    (OUT / "replay.json").write_text(json.dumps(data, separators=(",", ":")))
    print("replay.json", len(tk), "quadros", [r["summary"] for r in runs])


def export_failure():
    extra = {"network": {"outage_rate_per_day": 0.0}}
    cfg = ScenarioConfig.from_dict({**BASE, "policy": {"name": "C"}, **extra})
    sim = Simulation(cfg)
    # interrupção regional determinística: 50% dos dispositivos mais próximos de
    # um centro, do dia 9 às 0h ao dia 11 às 0h (48 h), injetada nos fluxos
    pts = sim.geo.xy_km[1:]
    c = np.median(pts, axis=0)
    idx = np.argsort(((pts - c) ** 2).sum(1))[: sim.n // 2]
    spd = sim.spd
    sim.net.net_up[idx, 9 * spd:11 * spd] = False
    res = sim.run()
    tr = sim.trace
    np.savez_compressed(OUT / "trace_falha.npz", t=np.array(tr["t"]), fill=np.array(tr["fill"]),
                        est=np.array(tr["est"]), stale=np.array(tr["stale"]), affected=idx,
                        latlon=sim.geo.latlon, kpi=np.array(tr["kpi"]),
                        outage=np.array([9 * 86400, 11 * 86400]))
    print("trace_falha.npz", {k: res[k] for k in ("overflow_pct", "telemetry_availability")})


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    export_replay()
    export_failure()
