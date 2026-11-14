import math
import numpy as np
import pytest
from wastesim.config import ContainerCfg, SensorCfg, TimeCfg
from wastesim import sensor as S

C = ContainerCfg(volume_l=1100, sensor_to_bottom_cm=110, mount_offset_cm=10)


def test_useful_height():
    assert S.useful_height_cm(C) == 100


@pytest.mark.parametrize("d,occ", [(110, 0.0), (60, 50.0), (10, 100.0), (35, 75.0)])
def test_occupancy_formula(d, occ):
    o, ok = S.occupancy_from_distance(d, C)
    assert ok and o == pytest.approx(occ)


def test_occupancy_clamped_to_physical_limits():
    assert S.occupancy_from_distance(5.0, C) == (100.0, True)      # acima da borda útil
    assert S.occupancy_from_distance(118.0, C) == (0.0, True)      # pouco além do fundo


@pytest.mark.parametrize("d", [None, float("nan"), float("inf"), 1.0, 500.0, 130.0])
def test_invalid_readings(d):
    o, ok = S.occupancy_from_distance(d, C)
    assert not ok and o is None


def test_roundtrip_fill_distance():
    for f in np.linspace(0, 1, 11):
        o, ok = S.occupancy_from_distance(float(S.distance_from_fill(f, C)), C)
        assert ok and o == pytest.approx(100 * f)


def test_original_formula_was_inverted():
    """A fórmula do firmware de 2024 (d/Tmax·100) cresce quando a lixeira esvazia."""
    tmax = 50.0
    orig = lambda d: d / tmax * 100
    assert orig(45) > orig(5)            # lixeira quase vazia → valor alto
    assert S.occupancy_from_distance(105, C)[0] < S.occupancy_from_distance(15, C)[0]


def test_speed_of_sound():
    assert S.speed_of_sound_m_s(20) == pytest.approx(343.42, abs=0.01)


def test_surface_bias_overestimates_occupancy():
    tcfg = TimeCfg(warmup_days=0, eval_days=5)
    scfg = SensorCfg(noise_sd_cm=0, surface_sd_cm=3, p_invalid=0, p_spike=0, mtbf_days=0)
    st = S.generate_streams(scfg, tcfg, 3, np.random.default_rng(0))
    occ = [S.occupancy_from_distance(S.measure(0.5, 0, t, st, scfg, C), C)[0] for t in range(400)]
    bias = np.mean(occ) - 50
    assert bias == pytest.approx(3 * math.sqrt(2 / math.pi), abs=0.4)


def test_availability_process_mean_downtime():
    tcfg = TimeCfg(warmup_days=0, eval_days=200)
    scfg = SensorCfg(mtbf_days=10, mttr_hours=24)
    st = S.generate_streams(scfg, tcfg, 50, np.random.default_rng(1))
    down = 1 - st.dev_up.mean()
    assert down == pytest.approx(1 / 11, rel=0.25)   # MTTR/(MTBF+MTTR)
