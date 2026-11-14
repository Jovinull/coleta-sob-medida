"""Modo live: o simulador de campo publica a telemetria por MQTT real.

Diferenças em relação ao modo em lote:
* o canal emulado é substituído pelo broker Mosquitto local: cada contêiner
  virtual é um cliente MQTT próprio (``VirtualDevice``);
* a plataforma recebe as mensagens por assinatura (``PlatformSubscriber``),
  valida, ingere e persiste em SQLite; o planejador usa exclusivamente esse
  estado ingerido;
* o relógio simulado avança passo a passo com ritmo opcional de parede
  (``step_wall_s``) para visualização no painel.

Uso:
    python -m wastesim.live --n 60 --days 5 --policy D --step-wall 0.2
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from . import sensor as sensor_mod
from .config import ScenarioConfig
from .mqtt_bridge import PlatformSubscriber, VirtualDevice
from .persistence import Store
from .simulation import Simulation
from .telemetry import device_id

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "live"


class LiveSimulation(Simulation):
    def __init__(self, cfg: ScenarioConfig, host="127.0.0.1", port=1883, qos=1,
                 step_wall_s=0.0, db_path=None, state_path=None, prefix="residuos"):
        super().__init__(cfg)
        self.step_wall_s = step_wall_s
        self.prefix = prefix
        self.store = Store(db_path or LIVE / "plataforma.db")
        self.sub = PlatformSubscriber(self.ingest, self.store, host, port, prefix=prefix)
        self.sub.connected.wait(10)
        self.devices = [VirtualDevice(device_id(i), host, port, qos, prefix=prefix) for i in range(self.n)]
        for d in self.devices:
            d.connected.wait(10)
        self.published = 0
        self.pub_wall: dict[tuple, float] = {}
        self.state_path = Path(state_path or LIVE / "state.json")
        self.alert = np.zeros(self.n, bool)
        self.cur_day_routes: list[list[int]] = []
        self.cur_paths: list = []

    # sensoriamento → MQTT (sem o canal emulado)
    def _sense(self, t: int, ts: float):
        s, k = self.sensors, self.sample_k
        due = np.nonzero(((t + s.phase) % k) == 0)[0]
        scfg, ccfg = self.cfg.sensor, self.cfg.container
        for i in due:
            if self._in_eval(t):
                self.m["expected_msgs"] += 1
            if not s.dev_up[i, t]:
                continue
            d = sensor_mod.measure(self.fill[i], i, t, s, scfg, ccfg)
            occ, ok = sensor_mod.occupancy_from_distance(d, ccfg)
            dev = self.devices[i]
            seq, _ = dev.telemetry(ts, d, occ, ok)
            self.pub_wall[(dev.dev, dev.boot, seq)] = time.time()
            self.published += 1
            if ok:   # eventos de limiar com histerese (80% / 70%)
                if occ >= 80 and not self.alert[i]:
                    self.alert[i] = True
                    dev.event("limiar_excedido", ts, {"ocupacao": round(occ, 1), "limiar": 80})
                elif occ < 70 and self.alert[i]:
                    self.alert[i] = False
                    dev.event("limiar_normalizado", ts, {"ocupacao": round(occ, 1), "limiar": 70})
        # aguarda a entrega antes de prosseguir (até 2 s)
        deadline = time.time() + 2.0
        while self.sub.received < self.published and time.time() < deadline:
            time.sleep(0.002)

    def _plan(self, day, now):
        with self.sub.lock:
            super()._plan(day, now)
        self.cur_day_routes = [tr.route for tr in self.trucks]
        from .geo import street_paths
        self.cur_paths = [[(round(a, 5), round(b, 5)) for a, b in poly]
                          for poly in street_paths(self.geo, self.cfg.geo, self.cur_day_routes)]
        for tr in self.trucks:
            self.store.route(day, tr.vid, [device_id(c) for c in tr.route], 0.0)

    def _collect(self, c, t_s, vol, tr, ev):
        with self.sub.lock:
            super()._collect(c, t_s, vol, tr, ev)
        self.alert[c] = False
        self.store.collection(t_s, device_id(c), vol, tr.vid)

    def run_live(self) -> dict:
        tc = self.cfg.time
        plan_step = int(tc.plan_hour * self.spd / 24)
        V = self.V
        t_wall = time.time()
        for t in range(self.T):
            t0 = time.time()
            now = t * self.step_s
            if t == self.warm_step:
                self.m["stock_start_l"] = float(self.fill.sum() * V)
            if t % self.spd == plan_step:
                self._plan(t // self.spd, now)
            self._generate(t, now)
            for tr in self.trucks:
                if not tr.done:
                    self._advance(tr, now + self.step_s, t)
            self._sense(t, now + self.step_s)
            self._write_state(now + self.step_s)
            if self.step_wall_s:
                time.sleep(max(0.0, self.step_wall_s - (time.time() - t0)))
        for tr in self.trucks:
            if not tr.done:
                self._advance(tr, float("inf"), self.T - 1)
        self.m["stock_end_l"] = float(self.fill.sum() * V)
        self.store.commit()
        lat = [self.sub.recv_wall[k] - w for k, w in self.pub_wall.items() if k in self.sub.recv_wall]
        return dict(published=self.published, received=self.sub.received,
                    ingest=dict(self.ingest.stats), wall_s=time.time() - t_wall,
                    latency_ms_median=1000 * float(np.median(lat)) if lat else None,
                    latency_ms_p99=1000 * float(np.percentile(lat, 99)) if lat else None)

    def _write_state(self, now: float):
        c = self.cfg.policy
        with self.sub.lock:
            est, stale = self.ingest.estimate(now, "observed", c.stale_hours, False)
            status = {k: v.get("estado") for k, v in self.sub.status.items()}
        geo = self.geo
        ll = geo.latlon if geo.latlon is not None else geo.xy_km
        conts = [dict(id=device_id(i), lat=float(ll[i + 1, 0]), lon=float(ll[i + 1, 1]),
                      real=round(float(self.fill[i]), 3), estimado=round(float(est[i]), 3),
                      desatualizado=bool(stale[i]), estado=status.get(device_id(i), "?"),
                      alerta=bool(self.alert[i]))
                 for i in range(self.n)]
        trucks = []
        for tr in self.trucks:
            p = tr.pos
            trucks.append(dict(vid=tr.vid, lat=float(ll[p, 0]), lon=float(ll[p, 1]), done=tr.done,
                               rota=[device_id(x) for x in tr.route], prox=tr.idx,
                               carga_l=round(tr.load_l)))
        st = dict(t=now, dia=int(now // 86400), hora=round((now % 86400) / 3600, 2),
                  politica=self.cfg.policy.name, deposito=[float(ll[0, 0]), float(ll[0, 1])],
                  contentores=conts, veiculos=trucks, caminhos=self.cur_paths,
                  kpi=dict(km=round(self.m.get("km", 0.0), 1), visitas=int(self.m.get("visits", 0)),
                           transbordo_m3=round(self.m.get("overflow_l", 0.0) / 1000, 2),
                           msgs_publicadas=self.published, msgs_recebidas=self.sub.received,
                           duplicadas=self.ingest.stats["duplicates"],
                           rejeitadas=self.ingest.stats["rejected"]))
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st))
        tmp.replace(self.state_path)

    def close(self):
        for d in self.devices:
            d.stop()
        self.sub.stop()
        self.store.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--policy", default="D")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--step-wall", type=float, default=0.15)
    ap.add_argument("--qos", type=int, default=1)
    a = ap.parse_args()
    LIVE.mkdir(exist_ok=True)
    db = LIVE / "plataforma.db"
    if db.exists():
        db.unlink()
    cfg = ScenarioConfig.from_dict({"seed": a.seed, "geo": {"kind": "osm", "n_containers": a.n},
                                    "time": {"warmup_days": 0, "eval_days": a.days},
                                    "policy": {"name": a.policy}})
    sim = LiveSimulation(cfg, qos=a.qos, step_wall_s=a.step_wall, db_path=db)
    try:
        print(json.dumps(sim.run_live(), indent=1))
    finally:
        sim.close()


if __name__ == "__main__":
    main()
