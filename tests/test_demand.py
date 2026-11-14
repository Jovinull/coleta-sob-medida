import numpy as np
import pytest
from wastesim.config import ContainerCfg, DemandCfg, TimeCfg
from wastesim import demand as Dm


def gen(seed=0, **kw):
    t = TimeCfg(warmup_days=0, eval_days=kw.pop("days", 70))
    return Dm.generate(DemandCfg(**kw), t, ContainerCfg(), 200, np.random.default_rng(seed)), t


def test_profiles_normalized():
    for p in Dm.PROFILES:
        assert Dm.weekly_profile(p).mean() == pytest.approx(1)
        assert Dm.hourly_profile(p).sum() == pytest.approx(1)


def test_nonnegative_and_shape():
    d, t = gen()
    assert d.inflow_l.shape == (200, t.total_days * t.steps_per_day)
    assert (d.inflow_l >= 0).all()


def test_long_run_mean_matches_mu():
    d, t = gen(event_rate_per_day=0, days=140)
    daily = d.inflow_l.sum(1) / t.total_days
    ratio = daily / d.mu_l_day
    assert np.median(ratio) == pytest.approx(1.0, abs=0.05)


def test_deterministic_given_seed():
    a, _ = gen(seed=7)
    b, _ = gen(seed=7)
    c, _ = gen(seed=8)
    assert np.array_equal(a.inflow_l, b.inflow_l)
    assert not np.array_equal(a.inflow_l, c.inflow_l)


def test_intensity_scales():
    a, _ = gen(seed=3, intensity=1.0, event_rate_per_day=0)
    b, _ = gen(seed=3, intensity=1.5, event_rate_per_day=0)
    assert b.inflow_l.sum() / a.inflow_l.sum() == pytest.approx(1.5)


def test_regime_shift():
    a, t = gen(seed=4, event_rate_per_day=0)
    b, _ = gen(seed=4, event_rate_per_day=0, shift_day=10, shift_fraction=0.5, shift_factor=2.0)
    s = 10 * t.steps_per_day
    assert np.allclose(a.inflow_l[:, :s], b.inflow_l[:, :s])
    assert b.inflow_l[:, s:].sum() > 1.4 * a.inflow_l[:, s:].sum()
