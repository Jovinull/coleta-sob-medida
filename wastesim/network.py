"""Emulação do canal de comunicação dispositivo → plataforma.

Nos experimentos em lote, o transporte MQTT é substituído por este modelo de
canal para que centenas de milhares de mensagens por réplica possam ser
processadas em segundos. A lógica de ingestão (validação, deduplicação,
ordenação, estimação de estado) é a **mesma** usada no caminho MQTT real
(``wastesim.mqtt_bridge``); o que não é exercitado aqui é a serialização e o
broker. A equivalência entre os dois caminhos é verificada no experimento de
integração (``experiments/mqtt_integration.py``).

Fenômenos modelados por mensagem: perda independente, duplicação, atraso
(lognormal, com cauda de atrasos longos) e interrupções regionais de
conectividade durante as quais as mensagens são perdidas — o firmware não
armazena leituras para reenvio (QoS 0 no PubSubClient).
"""
from __future__ import annotations

import dataclasses as dc

import numpy as np

from .config import NetworkCfg, TimeCfg


@dc.dataclass
class NetworkStreams:
    u_loss: np.ndarray      # (N, T)
    u_dup: np.ndarray       # (N, T)
    delay_s: np.ndarray     # (N, T)
    net_up: np.ndarray      # (N, T) bool


def generate_streams(ncfg: NetworkCfg, tcfg: TimeCfg, n: int, xy_km: np.ndarray,
                     rng: np.random.Generator) -> NetworkStreams:
    T = tcfg.total_days * tcfg.steps_per_day
    u_loss = rng.random((n, T)).astype(np.float32)
    u_dup = rng.random((n, T)).astype(np.float32)
    mu = np.log(max(ncfg.delay_median_s, 1e-6))
    delay = rng.lognormal(mu, ncfg.delay_sigma, size=(n, T)).astype(np.float32)
    long_ = rng.random((n, T)) < ncfg.p_long_delay
    delay[long_] = rng.uniform(3600, 6 * 3600, size=int(long_.sum()))

    net_up = np.ones((n, T), dtype=bool)
    if ncfg.outage_rate_per_day > 0 and ncfg.outage_hours > 0:
        days = tcfg.total_days
        n_ev = rng.poisson(ncfg.outage_rate_per_day * days)
        dur = int(round(ncfg.outage_hours * 60 / tcfg.step_min))
        pts = xy_km[1:]
        k = max(1, int(round(ncfg.outage_fraction * n)))
        for _ in range(n_ev):
            t0 = int(rng.integers(0, T))
            # interrupção regional: os k dispositivos mais próximos de um centro
            c = pts[rng.integers(0, n)]
            idx = np.argsort(((pts - c) ** 2).sum(1))[:k]
            net_up[idx, t0:t0 + dur] = False
    return NetworkStreams(u_loss, u_dup, delay, net_up)


def transmit(i: int, t: int, s: NetworkStreams, ncfg: NetworkCfg,
             step_s: float) -> list[int]:
    """Retorna a lista de passos de chegada (vazia se perdida)."""
    if not s.net_up[i, t] or s.u_loss[i, t] < ncfg.p_loss:
        return []
    arr = t + int(s.delay_s[i, t] // step_s)
    out = [arr]
    if s.u_dup[i, t] < ncfg.p_duplicate:
        out.append(arr + 1)
    return out
