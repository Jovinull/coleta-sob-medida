"""Painel operacional (FastAPI).

    uvicorn dashboard.app:app --port 8050

Fontes de dados (todas produzidas pela aplicação, nenhuma digitada à mão):
* live/state.json e live/plataforma.db — escritos por ``python -m wastesim.live``
  (telemetria recebida via broker MQTT, ingerida e persistida);
* experiments/results/replay.json — traço gravado de uma simulação (A × D);
* experiments/results/dashboard.json — resumo dos experimentos (analysis.py);
* data/aracaju/roads.json — malha viária (OSM).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
app = FastAPI(title="Painel de coleta de RSU")


def _json(path: Path):
    if not path.exists():
        raise HTTPException(404, f"{path.relative_to(ROOT)} ainda não foi gerado")
    return JSONResponse(json.loads(path.read_text()))


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/static/{name}")
def static(name: str):
    f = (STATIC / name).resolve()
    if f.parent != STATIC or not f.exists():
        raise HTTPException(404)
    return FileResponse(f)


@app.get("/api/roads")
def roads():
    return FileResponse(ROOT / "data/aracaju/roads.json", media_type="application/json")


@app.get("/api/state")
def state():
    return _json(ROOT / "live/state.json")


@app.get("/api/history/{dev}")
def history(dev: str, limit: int = 500):
    db = ROOT / "live/plataforma.db"
    if not db.exists():
        raise HTTPException(404, "banco da plataforma ainda não existe")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute("SELECT ts, ocupacao, valida, resultado FROM telemetria WHERE dev=? "
                       "ORDER BY ts DESC LIMIT ?", (dev, limit)).fetchall()
    col = con.execute("SELECT ts, volume_l FROM coletas WHERE dev=? ORDER BY ts", (dev,)).fetchall()
    con.close()
    return {"dev": dev, "telemetria": rows[::-1], "coletas": col}


@app.get("/api/events")
def events(limit: int = 30):
    db = ROOT / "live/plataforma.db"
    if not db.exists():
        return []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute("SELECT dev, ts, tipo, detalhe FROM eventos ORDER BY rowid DESC LIMIT ?",
                       (limit,)).fetchall()
    con.close()
    return rows


@app.get("/api/replay")
def replay():
    return FileResponse(ROOT / "experiments/results/replay.json", media_type="application/json")


@app.get("/api/results")
def results():
    return _json(ROOT / "experiments/results/dashboard.json")
