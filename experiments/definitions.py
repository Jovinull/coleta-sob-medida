"""Definição declarativa dos experimentos (ver docs/protocolo-experimental.md).

Cada experimento é uma lista de execuções (condição, política, semente,
sobrescritas de configuração). As sementes 1001–1030 são exclusivas das
rodadas definitivas.
"""
from __future__ import annotations

from wastesim.config import deep_update

SEEDS30 = list(range(1001, 1031))
SEEDS20 = SEEDS30[:20]
SEEDS10 = SEEDS30[:10]

BASE = {"geo": {"kind": "osm", "n_containers": 100}}

POLICIES = {
    "A": {"policy": {"name": "A", "routing": "ortools"}},
    "B": {"policy": {"name": "B", "routing": "nn2opt"}},
    "B-OR": {"policy": {"name": "B", "routing": "ortools"}},
    "C": {"policy": {"name": "C", "routing": "ortools"}},
    "D": {"policy": {"name": "D", "routing": "ortools"}},
}


def _runs(exp, conditions, policies, seeds):
    out = []
    for cond, over in conditions.items():
        for pol in policies:
            for s in seeds:
                cfg = deep_update(deep_update(BASE, over), POLICIES[pol] if isinstance(pol, str) else pol[1])
                label = pol if isinstance(pol, str) else pol[0]
                cfg = deep_update(cfg, {"seed": s, "name": f"{exp}/{cond}"})
                out.append(dict(exp=exp, condition=cond, policy=label, seed=s, cfg=cfg))
    return out


def e1():
    conds = {f"N{n}": {"geo": {"n_containers": n}} for n in (20, 100, 500)}
    return _runs("E1", conds, ["A", "B", "B-OR", "C", "D"], SEEDS30)


def e2():
    runs = []
    for x in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        runs += _runs("E2", {f"A_target={x}": {}},
                      [("A", deep_update(POLICIES["A"], {"policy": {"periodic_target": x}}))], SEEDS20)
    for x in (0.5, 0.6, 0.7, 0.8, 0.9):
        runs += _runs("E2", {f"B-OR_theta={x}": {}},
                      [("B-OR", deep_update(POLICIES["B-OR"], {"policy": {"theta_hi": x}}))], SEEDS20)
        runs += _runs("E2", {f"C_theta={x}": {}},
                      [("C", deep_update(POLICIES["C"], {"policy": {"theta_hi": x, "theta_lo": round(x - 0.25, 2)}}))],
                      SEEDS20)
        runs += _runs("E2", {f"D_theta={x}": {}},
                      [("D", deep_update(POLICIES["D"], {"policy": {"theta_hi": x, "theta_lo": round(x - 0.25, 2),
                                                                    "theta_crit": round(x + 0.2, 2)}}))],
                      SEEDS20)
    return runs


OUTAGE = {"network": {"outage_rate_per_day": 1 / 7, "outage_hours": 48, "outage_fraction": 0.5}}


def e3():
    conds = {
        "base": {},
        "perda_5%": {"network": {"p_loss": 0.05}},
        "perda_20%": {"network": {"p_loss": 0.20}},
        "perda_50%": {"network": {"p_loss": 0.50}},
        "interrupcao_48h": OUTAGE,
        "ruido_0": {"sensor": {"noise_sd_cm": 0, "surface_sd_cm": 0, "p_invalid": 0, "p_spike": 0}},
        "ruido_3x": {"sensor": {"noise_sd_cm": 4.5, "surface_sd_cm": 9.0}},
        "ruido_6x": {"sensor": {"noise_sd_cm": 9.0, "surface_sd_cm": 18.0}},
        "falha_perm_10%": {"sensor": {"p_permanent_failure": 0.10}},
        "falha_perm_30%": {"sensor": {"p_permanent_failure": 0.30}},
        "congelado_10%": {"sensor": {"stuck_fraction": 0.10}},
        "amostra_15min": {"sensor": {"sample_every_min": 15}},
        "amostra_6h": {"sensor": {"sample_every_min": 360}},
        "amostra_24h": {"sensor": {"sample_every_min": 1440}},
    }
    runs = _runs("E3", conds, ["A", "B-OR", "C", "D"], SEEDS30)
    nofb = {
        "falha_perm_30%_sem_fallback": deep_update(conds["falha_perm_30%"], {"policy": {"fallback": False}}),
        "interrupcao_48h_sem_fallback": deep_update(OUTAGE, {"policy": {"fallback": False}}),
    }
    runs += _runs("E3", nofb, ["B-OR", "C", "D"], SEEDS30)
    # a sobrescrita da política vem depois da condição; reaplica fallback=False
    for r in runs:
        if r["condition"].endswith("sem_fallback"):
            r["cfg"] = deep_update(r["cfg"], {"policy": {"fallback": False}})
    return runs


def e4():
    conds = {
        "base": {},
        "demanda_0.7": {"demand": {"intensity": 0.7}},
        "demanda_1.3": {"demand": {"intensity": 1.3}},
        "alta_variabilidade": {"demand": {"day_cv": 0.5, "step_cv": 2.0, "event_rate_per_day": 0.1}},
        "mudanca_regime_30%x1.6": {"demand": {"shift_day": 14, "shift_fraction": 0.3, "shift_factor": 1.6}},
        "surto_geral_x1.3": {"demand": {"shift_day": 14, "shift_fraction": 1.0, "shift_factor": 1.3}},
        "frota_reduzida": {"fleet": {"target_utilization": 0.95}},
        "layout_agrupado": {"geo": {"layout": "clustered"}},
        "velocidade_15": {"fleet": {"speed_kmh": 15}},
        "velocidade_30": {"fleet": {"speed_kmh": 30}},
    }
    return _runs("E4", conds, ["A", "B-OR", "C", "D"], SEEDS30)


def e5():
    runs = []
    for solver in ("greedy_descent", "gls"):
        over = {"geo": {"n_containers": 500}, "policy": {"solver": solver, "solver_time_s": 5.0}}
        rs = _runs("E5", {solver: over}, ["A", "C", "D"], SEEDS10)
        for r in rs:
            r["cfg"] = deep_update(r["cfg"], {"policy": {"solver": solver, "solver_time_s": 5.0}})
        runs += rs
    return runs


EXPERIMENTS = {"E1": e1, "E2": e2, "E3": e3, "E4": e4, "E5": e5}
