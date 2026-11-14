import json
import numpy as np
import pytest
from wastesim import telemetry as Tm
from wastesim.ingest import Ingestor


def msg(dev="LX-0001", boot=0, seq=1, ts=100.0, occ=40.0, ok=True, d=70.0):
    return Tm.build_telemetry(dev, boot, seq, ts, d, occ, ok)


def test_roundtrip_json():
    m = msg()
    r = Tm.parse_telemetry(Tm.topic("LX-0001", "telemetria"), json.dumps(m))
    assert r.dev == "LX-0001" and r.seq == 1 and r.occupancy == 40.0 and r.valid


@pytest.mark.parametrize("mutate,topic_id", [
    (lambda m: m.update(v=2), "LX-0001"),
    (lambda m: m.update(id="LX-0002"), "LX-0001"),
    (lambda m: m.pop("seq"), "LX-0001"),
    (lambda m: m["leituras"][1].update(valor=150.0), "LX-0001"),
    (lambda m: m["leituras"][0].update(unidade="mm"), "LX-0001"),
])
def test_rejects_malformed(mutate, topic_id):
    m = msg(); mutate(m)
    with pytest.raises(Tm.InvalidMessage):
        Tm.parse_telemetry(Tm.topic(topic_id, "telemetria"), json.dumps(m))


def test_rejects_non_json():
    with pytest.raises(Tm.InvalidMessage):
        Tm.parse_telemetry("residuos/dispositivos/LX-0001/telemetria", b"\xff{")


def reading(**kw):
    return Tm.parse_telemetry(Tm.topic(kw.get("dev", "LX-0001"), "telemetria"), json.dumps(msg(**kw)))


def test_dedup_and_out_of_order():
    ing = Ingestor(2)
    assert ing.ingest(reading(seq=1, ts=100)) == "applied"
    assert ing.ingest(reading(seq=1, ts=100)) == "duplicate"
    assert ing.ingest(reading(seq=3, ts=300, occ=50)) == "applied"
    assert ing.ingest(reading(seq=2, ts=200, occ=10)) == "out_of_order"
    assert ing.stats["duplicates"] == 1 and ing.stats["out_of_order"] == 1


def test_same_seq_after_reboot_is_new_message():
    ing = Ingestor(1)
    ing.ingest(reading(seq=5, ts=100))
    assert ing.ingest(reading(boot=1, seq=5, ts=200)) == "applied"


def test_median_filter_rejects_isolated_spike():
    ing = Ingestor(1)
    for k, o in enumerate([40, 41, 98, 42]):
        ing.ingest(reading(seq=k, ts=100 + k, occ=o))
    assert ing.fill_obs[0] == pytest.approx(0.42)


def test_invalid_reading_counts_contact_but_not_state():
    ing = Ingestor(1, prior_fill=0.2)
    assert ing.ingest(reading(seq=1, ts=50, occ=None, ok=False, d=None)) == "invalid"
    assert ing.fill_obs[0] == 0.2 and ing.last_contact[0] == 50


def test_collection_resets_and_late_messages_ignored():
    ing = Ingestor(1)
    ing.ingest(reading(seq=1, ts=100, occ=80))
    ing.on_collected(0, 200.0)
    assert ing.fill_obs[0] == 0.0
    assert ing.ingest(reading(seq=2, ts=150, occ=81)) == "out_of_order"


def test_rate_estimate_recovers_linear_fill():
    ing = Ingestor(1)
    rate = 0.01  # fração por hora
    for k in range(30):
        ing.ingest(reading(seq=k, ts=k * 3600.0, occ=100 * rate * k))
    assert ing.rate(0, 29 * 3600.0) == pytest.approx(rate, rel=0.02)
    est, stale = ing.estimate(29 * 3600.0, "predicted", 24, True, horizon_h=10)
    assert est[0] == pytest.approx(rate * 39, abs=0.01) and not stale[0]


def test_stale_fallback():
    ing = Ingestor(1, prior_rate_per_h=0.01, prior_fill=0.1)
    est, stale = ing.estimate(48 * 3600.0, "observed", 24, True)
    assert stale[0] and est[0] == pytest.approx(0.1 + 0.48)
    est2, _ = ing.estimate(48 * 3600.0, "observed", 24, False)
    assert est2[0] == pytest.approx(0.1)
