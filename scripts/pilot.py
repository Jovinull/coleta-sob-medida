"""Execução-piloto: todas as políticas em uma semente (verificação rápida)."""
import sys, json
from wastesim.config import ScenarioConfig
from wastesim.simulation import run
KEYS = ["n_vehicles", "km_per_day", "visits_per_day", "overflow_pct", "overflow_events",
        "full_h_per_container_day", "km_per_m3", "mean_fill_at_collection",
        "pct_collections_below_50", "mean_wait_h", "vehicle_utilization", "recourse_trips",
        "unserved_planned", "dropped_mandatory", "solver_s_mean", "selected_per_day",
        "telemetry_availability", "pred_mae", "persist_mae", "wall_s"]
over = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
for pol, rt in [("A", "ortools"), ("B", "nn2opt"), ("B", "ortools"), ("C", "ortools"), ("D", "ortools")]:
    cfg = ScenarioConfig.from_dict({"seed": 1, **over}).with_overrides({"policy": {"name": pol, "routing": rt}})
    r = run(cfg)
    print(f"{pol}-{rt[:2]}", " ".join(f"{k}={r[k]:.3g}" if isinstance(r.get(k), float) else f"{k}={r.get(k)}" for k in KEYS), flush=True)
