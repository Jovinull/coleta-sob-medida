"""Laço principal da simulação (tempo discreto, passo de 15 min).

Em cada passo t:
  1. se for o horário de planejamento, a política gera as rotas do dia;
  2. resíduos são gerados (estado verdadeiro); excedentes acima da capacidade
     contam como transbordamento;
  3. os veículos avançam nas rotas até o fim do passo; ao chegar a um
     contêiner, coletam o volume verdadeiro naquele instante. Se a carga
     excederia a capacidade, o veículo faz um desvio ao depósito para
     descarregar e retorna (recurso clássico de VRP com demanda estocástica);
     se a jornada não comporta a próxima visita e o retorno, o veículo volta e
     as visitas restantes ficam não realizadas;
  4. dispositivos programados para o passo medem (sensor virtual) e
     transmitem pelo canal emulado; mensagens que chegam no passo são
     ingeridas pela plataforma.

O estado verdadeiro só é visível para a contabilização das métricas e para o
recurso de capacidade; as políticas B–D decidem exclusivamente com base no
estado estimado pela ingestão. A política A usa as taxas médias verdadeiras.
"""
from __future__ import annotations

import dataclasses as dc
import math
import time
from collections import defaultdict

import numpy as np

from . import demand as demand_mod
from . import geo as geo_mod
from . import network as net_mod
from . import policies
from . import sensor as sensor_mod
from .config import ScenarioConfig
from .ingest import Ingestor
from .telemetry import Reading, device_id

H = 3600.0


@dc.dataclass
class Truck:
    vid: int
    route: list[int]
    start_s: float
    end_s: float
    pos: int = 0            # nó corrente (0 = depósito; contêiner i → i+1)
    time_s: float = 0.0
    idx: int = 0
    load_l: float = 0.0
    km: float = 0.0
    trips: int = 1
    done: bool = False
    unserved: list[int] = dc.field(default_factory=list)
    collected_l: float = 0.0
    visits: int = 0


class Simulation:
    def __init__(self, cfg: ScenarioConfig):
        self.cfg = cfg
        t = cfg.time
        self.step_s = t.step_min * 60.0
        self.spd = t.steps_per_day
        self.T = t.total_days * self.spd
        self.warm_step = t.warmup_days * self.spd
        ss = np.random.SeedSequence(cfg.seed).spawn(6)
        rngs = [np.random.default_rng(s) for s in ss]
        self.geo = geo_mod.build(cfg.geo, rngs[0])
        self.n = self.geo.n
        self.V = cfg.container.volume_l
        self.demand = demand_mod.generate(cfg.demand, t, cfg.container, self.n, rngs[1])
        self.sensors = sensor_mod.generate_streams(cfg.sensor, t, self.n, rngs[2])
        self.net = net_mod.generate_streams(cfg.network, t, self.n, self.geo.xy_km, rngs[3])
        self.fill = rngs[4].uniform(0, cfg.container.initial_fill_max, self.n)
        f = cfg.fleet
        self.n_vehicles = f.n_vehicles or max(
            1, math.ceil(self.demand.mu_l_day.sum() / (f.target_utilization * f.capacity_l)))
        speed = f.speed_kmh / 3.6
        self.travel_s = self.geo.dist_km * 1000 / speed
        self.last_collect_true = np.zeros(self.n)
        prior = float(np.median(self.demand.mu_l_day)) / self.V / 24  # só p/ inicialização
        self.ingest = Ingestor(self.n, prior_rate_per_h=prior)
        self.policy = policies.make(self)
        self.sample_k = max(1, cfg.sensor.sample_every_min // t.step_min)
        self._queue: dict[int, list[Reading]] = defaultdict(list)
        self._seq = np.zeros(self.n, np.int64)
        self._stuck_d: dict[int, float | None] = {}
        self.trucks: list[Truck] = []
        self._init_metrics()

    # ------------------------------------------------------------ métricas
    def _init_metrics(self):
        self.m = defaultdict(float)
        self.coll_fill: list[float] = []         # ocupação verdadeira na coleta
        self.coll_events: list[tuple] = []       # (t_s, i, vol, vid)
        self.route_log: list[dict] = []
        self.plan_log: list[dict] = []
        self.full_since = np.full(self.n, -1.0)  # instante em que encheu
        self.cross80 = np.full(self.n, -1.0)     # cruzamento de 80% (para espera)
        self.waits_h: list[float] = []
        self.pred_pairs: list[tuple] = []        # (t_alvo, i, pred, persist)
        self.trace = None
        if self.cfg.record_trace:
            self.trace = dict(fill=[], est=[], t=[], trucks=[], routes=[], kpi=[], stale=[])

    def _in_eval(self, step: int) -> bool:
        return step >= self.warm_step

    # ------------------------------------------------------------ execução
    def run(self) -> dict:
        t_wall = time.perf_counter()
        tc = self.cfg.time
        plan_step = int(tc.plan_hour * self.spd / 24)
        V = self.V
        for t in range(self.T):
            now = t * self.step_s
            day = t // self.spd
            if t == self.warm_step:
                self.m["stock_start_l"] = float(self.fill.sum() * V)
            if t % self.spd == plan_step:
                self._plan(day, now)
            self._generate(t, now)
            # 3. veículos
            for tr in self.trucks:
                if not tr.done:
                    self._advance(tr, now + self.step_s, t)
            # 4. sensores e canal
            self._sense(t, now + self.step_s)
            for r in self._queue.pop(t, ()):
                self.ingest.ingest(r, int(r.dev[3:]) - 1)
            if self.trace is not None and t % (self.spd // 24) == 0:
                self._snap(now)
            self._check_predictions(t, now + self.step_s)
        for tr in self.trucks:          # encerra rotas pendentes
            if not tr.done:
                self._advance(tr, math.inf, self.T - 1)
        self.m["stock_end_l"] = float(self.fill.sum() * V)
        out = self._summarize()
        out["wall_s"] = time.perf_counter() - t_wall
        return out

    def _generate(self, t: int, now: float):
        """Geração de resíduos no passo t e contabilização de transbordamento."""
        V = self.V
        q = self.demand.inflow_l[:, t]
        prev_full = self.fill >= 1.0
        self.fill += q / V
        over = self.fill > 1.0
        ev = self._in_eval(t)
        if ev:
            self.m["generated_l"] += q.sum()
            if over.any():
                self.m["overflow_l"] += float(((self.fill[over] - 1.0) * V).sum())
        self.fill[over] = 1.0
        full = self.fill >= 1.0
        if ev:
            self.m["overflow_events"] += int((full & ~prev_full).sum())
            self.m["full_container_h"] += float(full.sum()) * self.step_s / H
        c80 = (self.fill >= 0.8) & (self.cross80 < 0)
        self.cross80[c80] = now + self.step_s

    def _plan(self, day: int, now: float):
        tc = self.cfg.time
        for tr in self.trucks:          # garante encerramento do dia anterior
            if not tr.done:
                self._advance(tr, math.inf, int(now // self.step_s))
        plan = self.policy.plan(day, now)
        start = day * 86400 + tc.shift_start_h * H
        end = start + tc.shift_hours * H
        self.trucks = [Truck(v, r, start, end, time_s=start) for v, r in enumerate(plan.routes)]
        ev = self._in_eval(day * self.spd)
        self.plan_log.append(dict(day=day, eval=ev, selected=plan.selected,
                                  mandatory=plan.mandatory, dropped_mandatory=plan.dropped_mandatory,
                                  runtime_s=plan.runtime_s, planned_km=plan.planned_km,
                                  n_routes=len(plan.routes), method=plan.method))
        if self.trace is not None:
            self.trace["routes"].append(dict(day=day, routes=plan.routes))
        if self.cfg.policy.name in ("C", "D", "B") and day >= 1:
            self._log_predictions(now)

    def _advance(self, tr: Truck, until_s: float, step: int):
        T, D = self.travel_s, self.geo.dist_km
        serv = self.cfg.fleet.service_min * 60
        unload = self.cfg.fleet.unload_min * 60
        Q = self.cfg.fleet.capacity_l
        ev = self._in_eval(step)
        while not tr.done:
            if tr.idx >= len(tr.route):
                self._finish(tr, ev)
                return
            c = tr.route[tr.idx]
            node = c + 1
            arr = tr.time_s + T[tr.pos, node]
            if arr > until_s:
                return
            if arr + serv + T[node, 0] > tr.end_s:
                tr.unserved = tr.route[tr.idx:]
                self._finish(tr, ev)
                return
            vol = self.fill[c] * self.V
            if tr.load_l + vol > Q:
                arr2 = arr + T[node, 0] + unload + T[0, node]
                if arr2 + serv + T[node, 0] > tr.end_s:
                    tr.km += D[tr.pos, node]
                    tr.pos = node
                    tr.unserved = tr.route[tr.idx:]
                    self._finish(tr, ev)
                    return
                tr.km += D[tr.pos, node] + D[node, 0] + D[0, node]
                tr.load_l = 0.0
                tr.trips += 1
                arr = arr2
            else:
                tr.km += D[tr.pos, node]
            vol = self.fill[c] * self.V
            self._collect(c, arr, vol, tr, ev)
            tr.time_s = arr + serv
            tr.pos = node
            tr.idx += 1

    def _collect(self, c: int, t_s: float, vol: float, tr: Truck, ev: bool):
        tr.load_l += vol
        tr.collected_l += vol
        tr.visits += 1
        if ev:
            self.m["collected_l"] += vol
            self.m["visits"] += 1
            self.coll_fill.append(vol / self.V)
            if self.cross80[c] >= 0:
                self.waits_h.append(max(0.0, t_s - self.cross80[c]) / H)
        self.cross80[c] = -1.0
        self.fill[c] = 0.0
        self.last_collect_true[c] = t_s
        self.ingest.on_collected(c, t_s)
        self.coll_events.append((t_s, c, vol, tr.vid))

    def _finish(self, tr: Truck, ev: bool):
        tr.km += self.geo.dist_km[tr.pos, 0]
        tr.time_s += self.travel_s[tr.pos, 0]
        tr.pos = 0
        tr.done = True
        if tr.unserved and isinstance(self.policy, policies.PeriodicPolicy):
            self.policy.on_unserved(tr.unserved)
        if ev:
            self.m["km"] += tr.km
            self.m["trips"] += tr.trips
            self.m["routes"] += 1
            self.m["unserved_planned"] += len(tr.unserved)
            self.m["route_h"] += (tr.time_s - tr.start_s) / H
        self.route_log.append(dict(vid=tr.vid, start_s=tr.start_s, end_s=tr.time_s, km=tr.km,
                                   visits=tr.visits, trips=tr.trips, collected_l=tr.collected_l,
                                   unserved=len(tr.unserved), eval=ev))

    # ------------------------------------------------------------ sensores
    def _sense(self, t: int, ts: float):
        s, k = self.sensors, self.sample_k
        due = np.nonzero(((t + s.phase) % k) == 0)[0]
        scfg, ccfg, ncfg = self.cfg.sensor, self.cfg.container, self.cfg.network
        ev = self._in_eval(t)
        for i in due:
            if ev:
                self.m["expected_msgs"] += 1
            if not s.dev_up[i, t]:
                continue
            d = sensor_mod.measure(self.fill[i], i, t, s, scfg, ccfg)
            sf = s.stuck_from[i]
            if 0 <= sf <= t:
                if i not in self._stuck_d:
                    self._stuck_d[i] = d
                d = self._stuck_d[i]
            occ, ok = sensor_mod.occupancy_from_distance(d, ccfg)
            self._seq[i] += 1
            r = Reading(device_id(i), 0, int(self._seq[i]), ts, d, occ, ok)
            arrivals = net_mod.transmit(i, t, self.net, ncfg, self.step_s)
            if ev:
                self.m["sent_msgs"] += 1
                if not arrivals:
                    self.m["lost_msgs"] += 1
                elif arrivals[0] > t:
                    self.m["delayed_msgs"] += 1
                if ok and arrivals:
                    self.m["valid_delivered"] += 1
            for a in arrivals:
                if a < self.T:
                    self._queue[a].append(r)

    # ------------------------------------------------------------ predição
    def _log_predictions(self, now: float):
        c = self.cfg.policy
        pred, stale = self.ingest.estimate(now, "predicted", c.stale_hours, c.fallback, 24.0)
        pers = self.ingest.fill_obs
        t_target = now + 24 * H
        fresh = np.nonzero(~stale)[0]
        self._pending_pred = (t_target, fresh, pred[fresh].copy(), pers[fresh].copy(), now)

    def _check_predictions(self, t: int, ts: float):
        pp = getattr(self, "_pending_pred", None)
        if pp is None or ts < pp[0]:
            return
        t_target, idx, pred, pers, t_made = pp
        ok = self.last_collect_true[idx] < t_made   # sem coleta no intervalo
        if self._in_eval(t):
            for i, a, b in zip(idx[ok], pred[ok], pers[ok]):
                self.pred_pairs.append((float(self.fill[i]), float(min(a, 1.0)), float(b)))
        self._pending_pred = None

    # ------------------------------------------------------------ traço
    def _snap(self, now: float):
        c = self.cfg.policy
        est, stale = self.ingest.estimate(now, "observed", c.stale_hours, False)
        tr = [(tr.vid, tr.pos, tr.done) for tr in self.trucks]
        self.trace["t"].append(now)
        self.trace["fill"].append(self.fill.astype(np.float32).copy())
        self.trace["est"].append(np.where(stale, -1.0, est).astype(np.float32))
        self.trace["trucks"].append(tr)
        self.trace["stale"].append(stale.copy())
        km_now = self.m.get("km", 0.0) + sum(t.km for t in self.trucks if not t.done)
        self.trace["kpi"].append((km_now, int(self.m.get("visits", 0)),
                                  self.m.get("overflow_l", 0.0) / 1000, int((self.fill >= 1.0).sum())))

    # ------------------------------------------------------------ resumo
    def _summarize(self) -> dict:
        m = dict(self.m)
        days = self.cfg.time.eval_days
        V = self.V
        cf = np.array(self.coll_fill) if self.coll_fill else np.zeros(0)
        ev_plans = [p for p in self.plan_log if p["eval"]]
        out = dict(
            scenario=self.cfg.name, policy=self.cfg.policy.name, routing=self.cfg.policy.routing,
            seed=self.cfg.seed, n=self.n, n_vehicles=self.n_vehicles, eval_days=days,
            km_total=m.get("km", 0.0),
            km_per_day=m.get("km", 0.0) / days,
            visits=m.get("visits", 0),
            visits_per_day=m.get("visits", 0) / days,
            collected_m3=m.get("collected_l", 0.0) / 1000,
            generated_m3=m.get("generated_l", 0.0) / 1000,
            overflow_m3=m.get("overflow_l", 0.0) / 1000,
            overflow_pct=100 * m.get("overflow_l", 0.0) / max(m.get("generated_l", 1.0), 1.0),
            overflow_events=m.get("overflow_events", 0),
            full_container_h=m.get("full_container_h", 0.0),
            full_h_per_container_day=m.get("full_container_h", 0.0) / (self.n * days),
            km_per_m3=m.get("km", 0.0) / max(m.get("collected_l", 1.0) / 1000, 1e-9),
            mean_fill_at_collection=float(cf.mean()) if cf.size else float("nan"),
            pct_collections_below_50=100 * float((cf < 0.5).mean()) if cf.size else float("nan"),
            pct_collections_below_30=100 * float((cf < 0.3).mean()) if cf.size else float("nan"),
            mean_wait_h=float(np.mean(self.waits_h)) if self.waits_h else float("nan"),
            p95_wait_h=float(np.percentile(self.waits_h, 95)) if self.waits_h else float("nan"),
            vehicle_utilization=m.get("collected_l", 0.0) / max(m.get("trips", 1) * self.cfg.fleet.capacity_l, 1),
            recourse_trips=m.get("trips", 0) - m.get("routes", 0),
            route_h_mean=m.get("route_h", 0.0) / max(m.get("routes", 1), 1),
            unserved_planned=m.get("unserved_planned", 0),
            dropped_mandatory=sum(p["dropped_mandatory"] for p in ev_plans),
            solver_s_mean=float(np.mean([p["runtime_s"] for p in ev_plans])) if ev_plans else 0.0,
            solver_s_max=float(np.max([p["runtime_s"] for p in ev_plans])) if ev_plans else 0.0,
            selected_per_day=float(np.mean([p["selected"] for p in ev_plans])) if ev_plans else 0.0,
            expected_msgs=m.get("expected_msgs", 0),
            sent_msgs=m.get("sent_msgs", 0),
            lost_msgs=m.get("lost_msgs", 0),
            delayed_msgs=m.get("delayed_msgs", 0),
            telemetry_availability=m.get("valid_delivered", 0) / max(m.get("expected_msgs", 1), 1),
            ingest_duplicates=self.ingest.stats["duplicates"],
            ingest_out_of_order=self.ingest.stats["out_of_order"],
            ingest_invalid=self.ingest.stats["invalid_reading"],
            demand_events=self.demand.event_count,
            fingerprint=self.cfg.fingerprint(),
        )
        if self.pred_pairs:
            a = np.array(self.pred_pairs)
            out["pred_mae"] = float(np.mean(np.abs(a[:, 1] - a[:, 0])))
            out["persist_mae"] = float(np.mean(np.abs(a[:, 2] - a[:, 0])))
            out["pred_bias"] = float(np.mean(a[:, 1] - a[:, 0]))
            out["pred_n"] = int(len(a))
        out["V_l"] = V
        # balanço de massa (volume) na janela avaliada: deve fechar em ~0
        out["mass_balance_residual_l"] = (m.get("generated_l", 0.0) - m.get("collected_l", 0.0)
                                          - m.get("overflow_l", 0.0)
                                          - (m.get("stock_end_l", 0.0) - m.get("stock_start_l", 0.0)))
        return out


def run(cfg: ScenarioConfig) -> dict:
    return Simulation(cfg).run()
