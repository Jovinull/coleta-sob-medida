"""Transporte MQTT real (paho-mqtt 2.x, protocolo MQTT 3.1.1).

* ``VirtualDevice`` — um cliente MQTT por contêiner virtual, com Last Will
  retido em ``.../estado`` (``offline``/``lwt``), publicação retida de
  ``online`` a cada conexão e reconexão automática com recuo exponencial
  (``reconnect_delay_set``: 1 s → 32 s).
* ``PlatformSubscriber`` — cliente da plataforma com sessão persistente
  (``clean_session=False`` e id fixo), assinaturas QoS 1, validação pelo
  contrato (``telemetry.parse_telemetry``), ingestão (``Ingestor``) e
  persistência (``Store``).

Diferença declarada em relação ao firmware: o ESP32 (PubSubClient) publica
somente com QoS 0 e não enfileira mensagens desconectado; os dispositivos
virtuais podem usar QoS 1, caso em que a biblioteca paho mantém mensagens
pendentes em memória durante a desconexão.
"""
from __future__ import annotations

import json
import threading
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from . import telemetry as tm
from .ingest import Ingestor
from .persistence import Store


def _client(cid: str, clean: bool = True) -> mqtt.Client:
    c = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=cid, protocol=mqtt.MQTTv311,
                    clean_session=clean)
    c.reconnect_delay_set(min_delay=1, max_delay=32)
    c.max_queued_messages_set(0)   # 0 = sem limite (apenas QoS > 0 é enfileirado)
    return c


class VirtualDevice:
    def __init__(self, dev: str, host: str = "127.0.0.1", port: int = 1883, qos: int = 1,
                 boot: int = 0, prefix: str = tm.PREFIX):
        self.dev, self.qos, self.boot, self.prefix = dev, qos, boot, prefix
        self.seq = 0
        self.ev_seq = 0
        self.connected = threading.Event()
        self.connects = 0
        c = _client(dev)
        c.will_set(tm.topic(dev, "estado", prefix), json.dumps(tm.build_status(dev, False)),
                   qos=1, retain=True)
        c.on_connect = self._on_connect
        c.on_disconnect = lambda *a, **k: self.connected.clear()
        self.c = c
        c.connect_async(host, port, keepalive=15)
        c.loop_start()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.connects += 1
            client.publish(tm.topic(self.dev, "estado", self.prefix),
                           json.dumps(tm.build_status(self.dev, True, time.time())), qos=1, retain=True)
            if self.connects > 1:
                self.event("reconexao", time.time(), {"conexoes": self.connects})
            self.connected.set()

    def telemetry(self, ts: float, distance_cm, occupancy, valid: bool):
        self.seq += 1
        msg = tm.build_telemetry(self.dev, self.boot, self.seq, ts, distance_cm, occupancy, valid)
        info = self.c.publish(tm.topic(self.dev, "telemetria", self.prefix), json.dumps(msg), qos=self.qos)
        return self.seq, info

    def event(self, tipo: str, ts: float, detalhe: dict | None = None):
        self.ev_seq += 1
        msg = {"v": 1, "id": self.dev, "seq": self.ev_seq, "ts": ts, "tipo": tipo, "detalhe": detalhe or {}}
        self.c.publish(tm.topic(self.dev, "eventos", self.prefix), json.dumps(msg), qos=self.qos)

    def crash(self):
        """Falha abrupta: fecha o socket sem DISCONNECT → o broker publica o LWT."""
        self.c.loop_stop()
        sock = self.c.socket()
        if sock is not None:
            sock.close()

    def stop(self):
        self.c.publish(tm.topic(self.dev, "estado", self.prefix),
                       json.dumps({"v": 1, "id": self.dev, "estado": "offline", "motivo": "desligamento"}),
                       qos=1, retain=True).wait_for_publish(2)
        self.c.disconnect()
        self.c.loop_stop()


class PlatformSubscriber:
    def __init__(self, ingestor: Ingestor, store: Store | None = None, host: str = "127.0.0.1",
                 port: int = 1883, client_id: str = "plataforma-ingestao", clean: bool = False,
                 prefix: str = tm.PREFIX, index_of=tm.device_index):
        self.ing, self.store, self.prefix, self.index_of = ingestor, store, prefix, index_of
        self.lock = threading.RLock()   # reentrante: planejamento → coleta → ingestão
        self.received = 0
        self.recv_wall: dict[tuple, float] = {}
        self.status: dict[str, dict] = {}
        self.events: list[dict] = []
        self.connected = threading.Event()
        c = _client(client_id, clean)
        c.on_connect = self._on_connect
        c.on_message = self._on_message
        c.on_disconnect = lambda *a, **k: self.connected.clear()
        self.c = c
        c.connect_async(host, port, keepalive=15)
        c.loop_start()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            for k in ("telemetria", "estado", "eventos"):
                client.subscribe(f"{self.prefix}/dispositivos/+/{k}", qos=1)
            self.connected.set()

    def _on_message(self, client, userdata, msg):
        now = time.time()
        kind = msg.topic.rsplit("/", 1)[-1]
        try:
            if kind == "telemetria":
                r = tm.parse_telemetry(msg.topic, msg.payload)
                with self.lock:
                    res = self.ing.ingest(r, self.index_of(r.dev))
                    self.received += 1
                    self.recv_wall.setdefault((r.dev, r.boot, r.seq), now)
                if self.store:
                    self.store.telemetry(r, now, res)
            elif kind == "estado":
                d = json.loads(msg.payload)
                with self.lock:
                    self.status[d["id"]] = dict(d, recebido_em=now, retido=bool(msg.retain))
                if self.store:
                    self.store.status(d["id"], d.get("estado"), d.get("motivo"), d.get("ts"), now)
            elif kind == "eventos":
                d = json.loads(msg.payload)
                with self.lock:
                    self.events.append(dict(d, recebido_em=now))
                if self.store:
                    self.store.event(d["id"], d.get("seq", 0), d.get("ts", 0), d.get("tipo", "?"), d.get("detalhe"))
        except (tm.InvalidMessage, json.JSONDecodeError, KeyError, ValueError) as e:
            with self.lock:
                self.ing.reject()
            if self.store:
                self.store.rejected(now, msg.topic, str(e)[:200])

    def stop(self):
        self.c.disconnect()
        self.c.loop_stop()
        if self.store:
            self.store.commit()
