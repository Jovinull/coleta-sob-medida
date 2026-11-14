import numpy as np
import pytest
from wastesim.config import ScenarioConfig
from wastesim.simulation import Simulation, run

SMALL = {"time": {"warmup_days": 2, "eval_days": 7}, "geo": {"n_containers": 25}}


def cfg(**pol):
    return ScenarioConfig.from_dict({**SMALL, "seed": 3, "policy": pol})


@pytest.mark.parametrize("pol", ["A", "B", "C", "D"])
def test_mass_balance_closes(pol):
    r = run(cfg(name=pol))
    assert abs(r["mass_balance_residual_l"]) < 1e-6 * max(r["generated_m3"] * 1000, 1)


@pytest.mark.parametrize("pol", ["A", "C"])
def test_reproducible(pol):
    a, b = run(cfg(name=pol)), run(cfg(name=pol))
    for k in ("km_total", "visits", "overflow_m3", "collected_m3"):
        assert a[k] == b[k]


def test_common_random_numbers_across_policies():
    s1, s2 = Simulation(cfg(name="A")), Simulation(cfg(name="D"))
    assert np.array_equal(s1.demand.inflow_l, s2.demand.inflow_l)
    assert np.array_equal(s1.geo.dist_km, s2.geo.dist_km)
    assert np.array_equal(s1.sensors.noise, s2.sensors.noise)
    assert np.array_equal(s1.net.u_loss, s2.net.u_loss)


def test_invariants_after_run():
    sim = Simulation(cfg(name="C"))
    r = sim.run()
    assert (sim.fill >= 0).all() and (sim.fill <= 1).all()
    assert 0 <= r["telemetry_availability"] <= 1
    assert r["vehicle_utilization"] <= 1.0 + 1e-9
    assert r["pct_collections_below_50"] <= 100
    for rl in sim.route_log:
        assert rl["end_s"] - rl["start_s"] <= sim.cfg.time.shift_hours * 3600 + 1


def test_total_loss_degrades_iot_policy():
    base = run(cfg(name="C"))
    dark = run(ScenarioConfig.from_dict({**SMALL, "seed": 3, "policy": {"name": "C"},
                                         "network": {"p_loss": 1.0}}))
    assert dark["telemetry_availability"] == 0
    assert dark["km_total"] != base["km_total"]
