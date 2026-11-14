"""Executa experimentos com checkpoint por execução.

    python -m experiments.run E1 [E2 ...] [--workers 5]

Resultados: experiments/raw/<EXP>.jsonl (uma linha por execução, inclui a
configuração completa e a semente). Execuções já presentes no arquivo são
puladas, de modo que a rodada pode ser interrompida e retomada.
Proveniência: experiments/raw/<EXP>.manifest.json.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from experiments.definitions import EXPERIMENTS
from wastesim.config import ScenarioConfig
from wastesim.simulation import run

RAW = Path(__file__).parent / "raw"


def _key(r: dict) -> str:
    return f"{r['condition']}|{r['policy']}|{r['seed']}"


def _work(r: dict) -> dict:
    t0 = time.time()
    try:
        cfg = ScenarioConfig.from_dict(r["cfg"])
        res = run(cfg)
        status, err = "ok", None
    except Exception:  # registra a falha em vez de descartá-la
        res, status, err = {}, "error", traceback.format_exc()
    return dict(exp=r["exp"], condition=r["condition"], policy=r["policy"], seed=r["seed"],
                status=status, error=err, metrics=res, cfg=r["cfg"],
                finished_at=datetime.now(timezone.utc).isoformat(), wall_s=time.time() - t0)


def manifest(exp: str, n_runs: int) -> dict:
    def git(*a):
        try:
            return subprocess.check_output(["git", *a], text=True).strip()
        except Exception:
            return None
    pk = {p: metadata.version(p) for p in ("numpy", "scipy", "pandas", "ortools", "paho-mqtt",
                                           "matplotlib", "networkx")}
    return dict(experiment=exp, n_runs=n_runs, git_commit=git("rev-parse", "HEAD"),
                git_dirty=bool(git("status", "--porcelain")), python=sys.version,
                platform=platform.platform(), cpu_count=os.cpu_count(), packages=pk,
                started_at=datetime.now(timezone.utc).isoformat())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("exps", nargs="+")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    for exp in a.exps:
        runs = EXPERIMENTS[exp]()
        out = RAW / f"{exp}.jsonl"
        done = set()
        if out.exists():
            for line in out.read_text().splitlines():
                d = json.loads(line)
                if d["status"] == "ok":
                    done.add(_key(d))
        todo = [r for r in runs if _key(r) not in done]
        # execuções mais longas primeiro (melhor balanceamento)
        todo.sort(key=lambda r: -r["cfg"]["geo"]["n_containers"])
        man = manifest(exp, len(runs))
        man["resumed_skipped"] = len(runs) - len(todo)
        (RAW / f"{exp}.manifest.json").write_text(json.dumps(man, indent=2))
        print(f"{exp}: {len(runs)} execuções, {len(todo)} pendentes", flush=True)
        t0 = time.time()
        with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=20) as pool, out.open("a") as fh:
            for k, res in enumerate(pool.imap_unordered(_work, todo), 1):
                fh.write(json.dumps(res, default=float) + "\n")
                fh.flush()
                if res["status"] != "ok":
                    print("FALHA", _key(res), res["error"].splitlines()[-1], flush=True)
                if k % 25 == 0 or k == len(todo):
                    el = time.time() - t0
                    print(f"  {exp} {k}/{len(todo)}  {el/60:.1f} min", flush=True)
        man["finished_at"] = datetime.now(timezone.utc).isoformat()
        (RAW / f"{exp}.manifest.json").write_text(json.dumps(man, indent=2))


if __name__ == "__main__":
    main()
