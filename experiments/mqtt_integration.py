"""E6 — integração com broker MQTT real (Mosquitto 2.0.20 local).

Testes:
  T1 entrega e latência sob carga (100 dispositivos; QoS 0 e QoS 1; 3 repetições)
  T2 equivalência: modo live (MQTT) × modo em lote com canal ideal (mesma semente)
  T3 reinício do broker durante a publicação (QoS 0 × QoS 1)
  T4 Last Will: queda abrupta de 10 dispositivos
  T5 mensagens malformadas são rejeitadas sem alterar o estado

Uso: scripts/broker.sh start && python -m experiments.mqtt_integration
Resultado: experiments/results/E6_mqtt.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from wastesim import telemetry as tm
from wastesim.config import ScenarioConfig
from wastesim.ingest import Ingestor
from wastesim.live import LiveSimulation
from wastesim.mqtt_bridge import PlatformSubscriber, VirtualDevice
from wastesim.simulation import Simulation

OUT = Path(__file__).parent / "results"
ENGINE = shutil.which("docker") or shutil.which("podman")
BROKER = "residuos-mosquitto"


def fleet(n, qos, prefix):
    devs = [VirtualDevice(tm.device_id(i), qos=qos, prefix=prefix) for i in range(n)]
    for d in devs:
        d.connected.wait(10)
    return devs


def t1_load(n=100, per_dev=200, rate_hz=400, qos=1, rep=0):
    prefix = f"e6t1q{qos}r{rep}"
    ing = Ingestor(n)
    sub = PlatformSubscriber(ing, None, client_id=f"plat-{prefix}", clean=True, prefix=prefix)
    sub.connected.wait(10)
    devs = fleet(n, qos, prefix)
    pub = {}
    gap = 1.0 / rate_hz
    t0 = time.time()
    for k in range(per_dev):
        for d in devs:
            seq, _ = d.telemetry(float(k), 60.0, 50.0, True)
            pub[(d.dev, 0, seq)] = time.time()
            time.sleep(gap)
    time.sleep(3)
    lat = np.array([sub.recv_wall[k] - w for k, w in pub.items() if k in sub.recv_wall]) * 1000
    res = dict(qos=qos, rep=rep, published=len(pub), received_unique=len(sub.recv_wall),
               delivered_pct=100 * len(sub.recv_wall) / len(pub), duplicates=ing.stats["duplicates"],
               rate_msgs_s=len(pub) / (time.time() - t0 - 3),
               lat_ms_median=float(np.median(lat)), lat_ms_p95=float(np.percentile(lat, 95)),
               lat_ms_p99=float(np.percentile(lat, 99)), lat_ms_max=float(lat.max()))
    for d in devs:
        d.stop()
    sub.stop()
    return res


def t2_equivalence(seed=2024, n=40, days=6):
    base = {"seed": seed, "geo": {"kind": "osm", "n_containers": n},
            "time": {"warmup_days": 1, "eval_days": days - 1}, "policy": {"name": "D"},
            "network": {"p_loss": 0.0, "p_duplicate": 0.0, "p_long_delay": 0.0, "delay_median_s": 0.001}}
    cfg = ScenarioConfig.from_dict(base)
    batch = Simulation(cfg).run()
    live = LiveSimulation(cfg, db_path=OUT / "e6_equivalencia.db", state_path=OUT / "e6_state.json",
                          prefix="e6t2")
    try:
        info = live.run_live()
        lv = live._summarize()
    finally:
        live.close()
    keys = ["km_total", "visits", "collected_m3", "overflow_m3", "overflow_events"]
    return dict(batch={k: batch[k] for k in keys}, live={k: lv[k] for k in keys},
                identical=all(abs(batch[k] - lv[k]) < 1e-9 for k in keys), live_info=info)


def t3_restart(qos, n=100, seconds=30, rate_hz=300, restart_at=10):
    prefix = f"e6t3q{qos}"
    ing = Ingestor(n)
    sub = PlatformSubscriber(ing, None, client_id=f"plat-{prefix}", clean=False, prefix=prefix)
    sub.connected.wait(10)
    devs = fleet(n, qos, prefix)
    pub, rc_fail = {}, 0
    t0 = time.time()
    restarted = None
    k = 0
    while time.time() - t0 < seconds:
        if restarted is None and time.time() - t0 > restart_at:
            restarted = time.time()
            subprocess.run([ENGINE, "restart", "-t", "2", BROKER], check=True, capture_output=True)
            restart_dur = time.time() - restarted
        d = devs[k % n]
        seq, info = d.telemetry(float(k), 60.0, 50.0, True)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            rc_fail += 1
        pub[(d.dev, 0, seq)] = time.time()
        k += 1
        time.sleep(1.0 / rate_hz)
    # espera reconexões e reenvios
    for _ in range(60):
        if all(d.connected.is_set() for d in devs) and sub.connected.is_set():
            break
        time.sleep(1)
    time.sleep(5)
    recon = [d.connects - 1 for d in devs]
    res = dict(qos=qos, published_calls=len(pub), publish_rc_not_success=rc_fail,
               received_unique=len(sub.recv_wall),
               delivered_pct=100 * len(sub.recv_wall) / len(pub),
               lost=len(pub) - len(sub.recv_wall), duplicates=ing.stats["duplicates"],
               broker_restart_s=restart_dur, devices_reconnected=int(sum(r >= 1 for r in recon)),
               reconnection_events=[e["tipo"] for e in sub.events].count("reconexao"))
    for d in devs:
        d.stop()
    sub.stop()
    return res


def t4_lwt(n=30, crash=10):
    prefix = "e6t4"
    ing = Ingestor(n)
    sub = PlatformSubscriber(ing, None, client_id="plat-e6t4", clean=True, prefix=prefix)
    sub.connected.wait(10)
    devs = fleet(n, 0, prefix)
    time.sleep(1)
    t_crash = time.time()
    for d in devs[:crash]:
        d.crash()
    time.sleep(5)
    off = {k: v for k, v in sub.status.items() if v.get("estado") == "offline"}
    det = [v["recebido_em"] - t_crash for v in off.values()]
    res = dict(crashed=crash, offline_detected=len(off),
               all_lwt=all(v.get("motivo") == "lwt" for v in off.values()),
               correct_ids=sorted(off) == sorted(d.dev for d in devs[:crash]),
               detection_s_max=max(det) if det else None)
    # retido: um novo assinante recebe o estado offline imediatamente
    sub2 = PlatformSubscriber(Ingestor(n), None, client_id="plat-e6t4b", clean=True, prefix=prefix)
    time.sleep(2)
    res["retained_offline_seen_by_new_subscriber"] = sum(
        1 for v in sub2.status.values() if v.get("estado") == "offline" and v.get("retido"))
    for d in devs[crash:]:
        d.stop()
    sub.stop()
    sub2.stop()
    return res


def t5_malformed():
    prefix = "e6t5"
    ing = Ingestor(3, prior_fill=0.2)
    sub = PlatformSubscriber(ing, None, client_id="plat-e6t5", clean=True, prefix=prefix)
    sub.connected.wait(10)
    c = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="e6t5-inj", protocol=mqtt.MQTTv311)
    c.connect("127.0.0.1", 1883)
    c.loop_start()
    good = tm.build_telemetry("LX-0001", 0, 1, 1.0, 60.0, 50.0, True)
    bad = [b"nao-json", json.dumps({**good, "v": 9}), json.dumps({**good, "id": "LX-0002"}),
           json.dumps({k: v for k, v in good.items() if k != "seq"}),
           json.dumps({**good, "leituras": [{"tipo": "ocupacao", "valor": 140, "unidade": "%", "valida": True}]})]
    for k in range(50):
        c.publish(tm.topic("LX-0001", "telemetria", prefix), bad[k % len(bad)], qos=1).wait_for_publish(2)
    time.sleep(2)
    res = dict(sent=50, rejected=ing.stats["rejected"], state_unchanged=bool(ing.fill_obs[0] == 0.2))
    c.disconnect()
    c.loop_stop()
    sub.stop()
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ver = subprocess.run([ENGINE, "exec", BROKER, "mosquitto", "-h"], capture_output=True, text=True)
    res = dict(broker=(ver.stdout or ver.stderr).splitlines()[0], paho=mqtt.__version__ if hasattr(mqtt, "__version__") else None,
               started=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    from importlib.metadata import version
    res["paho"] = version("paho-mqtt")
    res["T1"] = [t1_load(qos=q, rep=r) for q in (0, 1) for r in range(3)]
    print("T1", json.dumps(res["T1"], indent=0), flush=True)
    res["T2"] = t2_equivalence()
    print("T2", res["T2"]["identical"], flush=True)
    res["T3"] = [t3_restart(0), t3_restart(1)]
    print("T3", json.dumps(res["T3"], indent=0), flush=True)
    res["T4"] = t4_lwt()
    print("T4", res["T4"], flush=True)
    res["T5"] = t5_malformed()
    print("T5", res["T5"], flush=True)
    (OUT / "E6_mqtt.json").write_text(json.dumps(res, indent=2, default=float))


if __name__ == "__main__":
    main()
