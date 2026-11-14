"""Políticas de coleta comparadas.

A — Periódica fixa. Cada contêiner recebe uma frequência p_i (dias) tal que o
    enchimento médio esperado na coleta seja ≈ ``periodic_target``, calculada
    a partir da **taxa média de longo prazo verdadeira** (premissa otimista: um
    planejador com histórico perfeito). As fases são distribuídas para
    equilibrar a carga diária. Não usa telemetria. Visitas planejadas e não
    realizadas são reprogramadas para o dia seguinte. Rotas: OR-Tools.

B — Limiar. Elegíveis: ocupação observada ≥ θ_hi. Rotas: vizinho mais próximo
    + 2-opt (variante "B-OR": mesmas elegibilidades com OR-Tools).

C — Dinâmica otimizada. Obrigatórios: ocupação observada ≥ θ_hi; opcionais:
    θ_lo ≤ ocupação < θ_hi, incluídos quando o desvio na rota custa menos que
    o prêmio λ·volume. Rotas: CVRP com prêmios (OR-Tools).

D — Preditiva. Como C, mas com ocupações projetadas pela taxa estimada:
    obrigatórios = projeção no meio do turno ≥ θ_hi OU projeção no fim do turno
    seguinte ≥ θ_crit (transbordaria antes da próxima oportunidade).

Nas políticas B–D, contêineres sem dado recente (> ``stale_hours``) têm a
ocupação estimada pela taxa de longo prazo (``fallback``); sem fallback, o
último valor observado é usado indefinidamente.
"""
from __future__ import annotations

import dataclasses as dc

import numpy as np

from .routing import BIG_PENALTY, RoutingProblem, solve_nn2opt, solve_ortools

H = 3600.0


@dc.dataclass
class Plan:
    routes: list[list[int]]          # índices globais (0..N-1)
    selected: int
    mandatory: int
    dropped_mandatory: int
    runtime_s: float
    planned_km: float
    method: str


class PolicyBase:
    def __init__(self, sim):
        self.sim = sim
        self.cfg = sim.cfg.policy

    def _solve(self, idx: np.ndarray, demand_l: np.ndarray, penalty: np.ndarray,
               method: str) -> Plan:
        sim = self.sim
        f = sim.cfg.fleet
        nodes = np.concatenate([[0], idx + 1])
        D = np.rint(sim.geo.dist_km[np.ix_(nodes, nodes)] * 1000).astype(np.int64)
        dem = np.concatenate([[0], np.minimum(demand_l, sim.V)]).astype(np.int64)
        pen = np.concatenate([[0], penalty]).astype(np.int64)
        p = RoutingProblem(D, dem, pen, sim.n_vehicles, int(f.capacity_l),
                           f.speed_kmh / 3.6, f.service_min * 60, sim.cfg.time.shift_hours * H)
        if len(idx) == 0:
            return Plan([], 0, 0, 0, 0.0, 0.0, method)
        if method == "ortools":
            res = solve_ortools(p, self.cfg.solver_time_s, None, self.cfg.solver)
        else:
            res = solve_nn2opt(p)
        routes = [[int(idx[k - 1]) for k in r] for r in res.routes]
        mand = pen >= BIG_PENALTY
        dropped_m = int(sum(mand[k] for k in res.dropped))
        return Plan(routes, len(idx), int(mand[1:].sum()), dropped_m, res.runtime_s,
                    res.distance_m / 1000, method)

    def plan(self, day: int, now: float) -> Plan:  # pragma: no cover
        raise NotImplementedError


class PeriodicPolicy(PolicyBase):
    def __init__(self, sim):
        super().__init__(sim)
        mu = sim.demand.mu_l_day
        target = self.cfg.periodic_target * sim.V
        self.period = np.clip(np.floor(target / mu), 1, self.cfg.periodic_max_days).astype(int)
        horizon = 420  # mmc(1..7)
        load = np.zeros(horizon)
        self.phase = np.zeros(sim.n, int)
        for i in np.argsort(-mu * self.period):
            p = self.period[i]
            costs = [load[ph::p].sum() for ph in range(p)]
            ph = int(np.argmin(costs))
            self.phase[i] = ph
            load[ph::p] += mu[i] * p
        self.pending = np.zeros(sim.n, bool)

    def plan(self, day: int, now: float) -> Plan:
        sim = self.sim
        due = ((day - self.phase) % self.period == 0) | self.pending
        idx = np.nonzero(due)[0]
        days_since = (now - sim.last_collect_true[idx]) / 86400 + 0.5
        demand = sim.demand.mu_l_day[idx] * np.maximum(days_since, 0.5)
        pen = np.full(len(idx), BIG_PENALTY)
        plan = self._solve(idx, demand, pen, "ortools")
        self.pending[:] = False
        served = {c for r in plan.routes for c in r}
        for c in idx:
            if c not in served:
                self.pending[c] = True
        return plan

    def on_unserved(self, idx: list[int]) -> None:
        self.pending[idx] = True


class ThresholdPolicy(PolicyBase):
    def plan(self, day: int, now: float) -> Plan:
        c = self.cfg
        est, _ = self.sim.ingest.estimate(now, "observed", c.stale_hours, c.fallback)
        idx = np.nonzero(est >= c.theta_hi)[0]
        pen = BIG_PENALTY + np.rint(1e6 * np.minimum(est[idx], 2)).astype(np.int64)
        return self._solve(idx, est[idx] * self.sim.V, pen, c.routing)


class DynamicPolicy(PolicyBase):
    mode = "observed"

    def _levels(self, now: float):
        c = self.cfg
        est, _ = self.sim.ingest.estimate(now, "observed", c.stale_hours, c.fallback)
        return est, est

    def plan(self, day: int, now: float) -> Plan:
        c = self.cfg
        f_now, urgency = self._levels(now)
        must = (f_now >= c.theta_hi) | (urgency >= c.theta_crit)
        may = (~must) & (f_now >= c.theta_lo)
        idx = np.nonzero(must | may)[0]
        vol = np.minimum(f_now[idx], 1.0) * self.sim.V
        pen = np.where(must[idx],
                       BIG_PENALTY + np.rint(1e6 * np.minimum(urgency[idx], 2)),
                       np.rint(c.may_go_m_per_l * vol)).astype(np.int64)
        return self._solve(idx, vol, pen, c.routing)


class PredictivePolicy(DynamicPolicy):
    def _levels(self, now: float):
        c = self.cfg
        t = self.sim.cfg.time
        mid = (t.shift_start_h - t.plan_hour) + t.shift_hours / 2
        nxt = 24 + (t.shift_start_h - t.plan_hour) + t.shift_hours
        f_mid, _ = self.sim.ingest.estimate(now, "predicted", c.stale_hours, c.fallback, mid)
        f_next, _ = self.sim.ingest.estimate(now, "predicted", c.stale_hours, c.fallback, nxt)
        return f_mid, f_next


def make(sim):
    name = sim.cfg.policy.name
    if name == "A":
        return PeriodicPolicy(sim)
    if name == "B":
        return ThresholdPolicy(sim)
    if name == "C":
        return DynamicPolicy(sim)
    if name == "D":
        return PredictivePolicy(sim)
    raise ValueError(name)


def periodic_mean_fill(mu: np.ndarray, V: float, target: float, max_days: int) -> float:
    p = np.clip(np.floor(target * V / mu), 1, max_days)
    return float(np.mean(p * mu / V))


