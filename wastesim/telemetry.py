"""Construção e validação de mensagens segundo docs/mqtt/contrato-mqtt.md."""
from __future__ import annotations

import dataclasses as dc
import json
import math
import re

SCHEMA_VERSION = 1
PREFIX = "residuos"
ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
UNITS = {"distancia": "cm", "ocupacao": "%", "temperatura": "degC", "umidade": "%RH"}


def device_id(i: int) -> str:
    return f"LX-{i + 1:04d}"


def device_index(dev_id: str) -> int:
    return int(dev_id.split("-")[1]) - 1


def topic(dev_id: str, kind: str, prefix: str = PREFIX) -> str:
    assert kind in ("telemetria", "estado", "eventos", "comandos")
    return f"{prefix}/dispositivos/{dev_id}/{kind}"


@dc.dataclass(slots=True)
class Reading:
    """Telemetria já validada, em forma compacta (usada pela ingestão)."""
    dev: str
    boot: int
    seq: int
    ts: float
    distance_cm: float | None
    occupancy: float | None      # 0–100
    valid: bool


def quantize(distance_cm: float | None, occupancy: float | None, valid: bool):
    """Arredondamento aplicado pelo contrato MQTT (0,1 cm; 0,1 %)."""
    d = None if distance_cm is None else round(distance_cm, 1)
    o = None if (not valid or occupancy is None) else round(occupancy, 1)
    return d, o


def build_telemetry(dev: str, boot: int, seq: int, ts: float, distance_cm: float | None,
                    occupancy: float | None, valid: bool, ts_src: str = "sim",
                    extra: list[dict] | None = None) -> dict:
    dq, oq = quantize(distance_cm, occupancy, valid)
    leit = [
        {"tipo": "distancia", "valor": dq, "unidade": "cm", "valida": distance_cm is not None},
        {"tipo": "ocupacao", "valor": oq, "unidade": "%", "valida": bool(valid)},
    ]
    if extra:
        leit.extend(extra)
    return {"v": SCHEMA_VERSION, "id": dev, "boot": boot, "seq": seq, "ts": round(ts, 3),
            "ts_src": ts_src, "leituras": leit}


class InvalidMessage(ValueError):
    pass


def parse_telemetry(topic_str: str, payload: bytes | str) -> Reading:
    """Valida uma mensagem de telemetria; levanta InvalidMessage."""
    parts = topic_str.split("/")
    if len(parts) != 4 or parts[1] != "dispositivos" or parts[3] != "telemetria":
        raise InvalidMessage("tópico inesperado")
    try:
        msg = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise InvalidMessage(f"JSON inválido: {e}") from None
    if not isinstance(msg, dict) or msg.get("v") != SCHEMA_VERSION:
        raise InvalidMessage("versão de esquema ausente ou desconhecida")
    dev = msg.get("id")
    if not isinstance(dev, str) or not ID_RE.match(dev) or dev != parts[2]:
        raise InvalidMessage("id ausente, inválido ou divergente do tópico")
    for k in ("boot", "seq"):
        if not isinstance(msg.get(k), int) or msg[k] < 0:
            raise InvalidMessage(f"campo {k} inválido")
    ts = msg.get("ts")
    if not isinstance(ts, (int, float)) or not math.isfinite(ts):
        raise InvalidMessage("ts inválido")
    leituras = msg.get("leituras")
    if not isinstance(leituras, list):
        raise InvalidMessage("leituras ausentes")
    dist = occ = None
    occ_valid = False
    for r in leituras:
        if not isinstance(r, dict):
            raise InvalidMessage("leitura malformada")
        tipo, val, ok = r.get("tipo"), r.get("valor"), r.get("valida")
        if tipo in UNITS and r.get("unidade") != UNITS[tipo]:
            raise InvalidMessage(f"unidade incorreta para {tipo}")
        if ok and not isinstance(val, (int, float)):
            raise InvalidMessage(f"valor inválido para {tipo}")
        if tipo == "distancia" and ok:
            dist = float(val)
        elif tipo == "ocupacao":
            occ_valid = bool(ok)
            if ok:
                occ = float(val)
                if not 0.0 <= occ <= 100.0:
                    raise InvalidMessage("ocupação fora de [0, 100]")
    return Reading(dev, msg["boot"], msg["seq"], float(ts), dist, occ, occ_valid)


def build_status(dev: str, online: bool, ts: float | None = None, fw: str = "sim-2.0") -> dict:
    if not online:
        return {"v": SCHEMA_VERSION, "id": dev, "estado": "offline", "motivo": "lwt"}
    return {"v": SCHEMA_VERSION, "id": dev, "estado": "online", "ts": ts, "fw": fw}
