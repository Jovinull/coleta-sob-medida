"""Persistência em SQLite (modo live e integração MQTT).

Tabelas:
* ``telemetria`` — toda mensagem recebida (inclusive duplicadas/fora de ordem),
  com o resultado da ingestão;
* ``estado`` — último estado conhecido por dispositivo (online/offline, LWT);
* ``eventos`` — eventos publicados pelos dispositivos;
* ``coletas`` — coletas executadas pelos veículos;
* ``rotas`` — planos diários.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS telemetria(
  dev TEXT, boot INT, seq INT, ts REAL, recebido_em REAL,
  distancia_cm REAL, ocupacao REAL, valida INT, resultado TEXT);
CREATE INDEX IF NOT EXISTS ix_tel_dev_ts ON telemetria(dev, ts);
CREATE TABLE IF NOT EXISTS estado(
  dev TEXT PRIMARY KEY, estado TEXT, motivo TEXT, ts REAL, recebido_em REAL);
CREATE TABLE IF NOT EXISTS eventos(dev TEXT, seq INT, ts REAL, tipo TEXT, detalhe TEXT);
CREATE TABLE IF NOT EXISTS coletas(ts REAL, dev TEXT, volume_l REAL, veiculo INT);
CREATE TABLE IF NOT EXISTS rotas(dia INT, veiculo INT, sequencia TEXT, km_planejado REAL);
CREATE TABLE IF NOT EXISTS rejeitadas(recebido_em REAL, topico TEXT, motivo TEXT);
"""


class Store:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.lock = threading.Lock()
        self._pending = 0

    def _exec(self, sql: str, args: tuple):
        with self.lock:
            self.db.execute(sql, args)
            self._pending += 1
            if self._pending >= 500:
                self.db.commit()
                self._pending = 0

    def commit(self):
        with self.lock:
            self.db.commit()
            self._pending = 0

    def telemetry(self, r, recv: float, result: str):
        self._exec("INSERT INTO telemetria VALUES(?,?,?,?,?,?,?,?,?)",
                   (r.dev, r.boot, r.seq, r.ts, recv, r.distance_cm, r.occupancy, int(r.valid), result))

    def status(self, dev: str, estado: str, motivo: str | None, ts: float | None, recv: float):
        self._exec("INSERT OR REPLACE INTO estado VALUES(?,?,?,?,?)", (dev, estado, motivo, ts, recv))

    def event(self, dev: str, seq: int, ts: float, tipo: str, detalhe: dict | None):
        self._exec("INSERT INTO eventos VALUES(?,?,?,?,?)", (dev, seq, ts, tipo, json.dumps(detalhe or {})))

    def collection(self, ts: float, dev: str, vol: float, vid: int):
        self._exec("INSERT INTO coletas VALUES(?,?,?,?)", (ts, dev, vol, vid))

    def route(self, day: int, vid: int, seq: list[str], km: float):
        self._exec("INSERT INTO rotas VALUES(?,?,?,?)", (day, vid, json.dumps(seq), km))

    def rejected(self, recv: float, topic: str, why: str):
        self._exec("INSERT INTO rejeitadas VALUES(?,?,?)", (recv, topic, why))

    def query(self, sql: str, args: tuple = ()):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def close(self):
        self.commit()
        self.db.close()
