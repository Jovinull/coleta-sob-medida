"""Reexecuta uma amostra aleatória das execuções registradas e compara as métricas.

    python scripts/verify_reproducibility.py [--frac 0.03] [--workers 5]

Compara todas as métricas numéricas, exceto as que medem tempo de relógio
(wall_s, solver_s_mean, solver_s_max). Resultado em
experiments/results/reprodutibilidade.json.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np

from wastesim.config import ScenarioConfig
from wastesim.simulation import run

ROOT = Path(__file__).resolve().parent.parent
TIMING = {"wall_s", "solver_s_mean", "solver_s_max"}


def _rerun(rec):
    new = run(ScenarioConfig.from_dict(rec["cfg"]))
    diffs = {}
    for k, v in rec["metrics"].items():
        if k in TIMING or not isinstance(v, (int, float)):
            continue
        w = new.get(k)
        if w is None or not np.isclose(v, w, rtol=1e-12, atol=1e-9, equal_nan=True):
            diffs[k] = (v, w)
    return dict(exp=rec["exp"], condition=rec["condition"], policy=rec["policy"], seed=rec["seed"],
                identical=not diffs, diffs=diffs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.03)
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    rng = np.random.default_rng(42)
    sample = []
    for f in sorted((ROOT / "experiments/raw").glob("E*.jsonl")):
        if f.stem == "E5":      # GLS é limitado por tempo: não determinístico por construção
            recs = [json.loads(x) for x in f.read_text().splitlines()]
            recs = [r for r in recs if r["status"] == "ok" and r["condition"] == "greedy_descent"]
        else:
            recs = [json.loads(x) for x in f.read_text().splitlines()]
            recs = [r for r in recs if r["status"] == "ok"]
        k = max(3, int(round(a.frac * len(recs))))
        sample += [recs[i] for i in rng.choice(len(recs), size=min(k, len(recs)), replace=False)]
    with mp.get_context("spawn").Pool(a.workers) as pool:
        out = pool.map(_rerun, sample)
    res = dict(n=len(out), identical=sum(o["identical"] for o in out), runs=out)
    (ROOT / "experiments/results/reprodutibilidade.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"{res['identical']}/{res['n']} execuções reproduzidas com métricas idênticas")
    for o in out:
        if not o["identical"]:
            print("DIFERENÇA", o["exp"], o["condition"], o["policy"], o["seed"], list(o["diffs"])[:5])


if __name__ == "__main__":
    main()
