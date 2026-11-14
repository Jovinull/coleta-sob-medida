"""Ingestão de telemetria e estimação do estado dos contêineres.

Usado de forma idêntica pelo simulador em lote e pelo serviço MQTT real.

Regras (docs/mqtt/contrato-mqtt.md):
1. deduplicação por (dispositivo, boot, seq);
2. mensagens com ``ts`` anterior ao último estado aplicado (ou à última coleta
   registrada) são contadas como fora de ordem e não alteram o estado;
3. leituras inválidas atualizam apenas o "último contato";
4. a ocupação observada é a mediana das 3 últimas leituras válidas do ciclo
   corrente (filtro contra leituras espúrias isoladas); a extrapolação usa o
   instante da leitura mediana, para não acumular o atraso do filtro;
5. a taxa de enchimento é estimada por mínimos quadrados sobre as leituras
   das últimas 48 h do ciclo (exige ≥ 6 leituras abrangendo ≥ 12 h); na falta
   delas, usa-se a média móvel exponencial das taxas de ciclos anteriores e,
   por último, uma taxa *a priori* comum (mediana da frota).

O estado estimado é a "sombra digital" de cada contêiner: atualizado
automaticamente a partir dos dados, mas sem atuação automática de volta no
objeto físico (a decisão de coleta é executada por veículos).
"""
from __future__ import annotations

import math
from collections import deque

import numpy as np

from .telemetry import Reading, device_index

H = 3600.0


class Ingestor:
    def __init__(self, n: int, prior_rate_per_h: float = 0.0125, t0: float = 0.0,
                 prior_fill: float = 0.25, window: int = 3, ewma_alpha: float = 0.3):
        self.n = n
        self.window = window
        self.alpha = ewma_alpha
        self.default_prior = prior_rate_per_h
        self.fill_obs = np.full(n, prior_fill)
        self.last_ts = np.full(n, t0)            # instante do estado aplicado
        self.obs_ts = np.full(n, t0)             # instante da leitura escolhida pela mediana
        self.last_reading_ts = np.full(n, -math.inf)  # última leitura válida aplicada
        self.last_contact = np.full(n, -math.inf)
        self.last_collect = np.full(n, t0)
        self.r_long = np.zeros(n)
        self.has_long = np.zeros(n, bool)
        self._win = [deque(maxlen=window) for _ in range(n)]
        self._cycle: list[list[tuple[float, float]]] = [[] for _ in range(n)]
        self._seen: list[set[tuple[int, int]]] = [set() for _ in range(n)]
        self._maxseq = np.zeros(n, np.int64)
        self.stats = dict(received=0, applied=0, duplicates=0, out_of_order=0,
                          invalid_reading=0, rejected=0)

    # ------------------------------------------------------------ ingestão
    def reject(self) -> None:
        """Mensagem rejeitada na validação de esquema (caminho MQTT)."""
        self.stats["rejected"] += 1

    def ingest(self, r: Reading, idx: int | None = None) -> str:
        i = device_index(r.dev) if idx is None else idx
        self.stats["received"] += 1
        key = (r.boot, r.seq)
        seen = self._seen[i]
        if key in seen:
            self.stats["duplicates"] += 1
            return "duplicate"
        seen.add(key)
        if len(seen) > 4096:   # poda: mantém apenas as sequências recentes
            cut = max(s for _, s in seen) - 2048
            self._seen[i] = {k for k in seen if k[1] >= cut}
        self.last_contact[i] = max(self.last_contact[i], r.ts)
        if not r.valid or r.occupancy is None:
            self.stats["invalid_reading"] += 1
            return "invalid"
        if r.ts < self.last_ts[i] or r.ts < self.last_collect[i]:
            self.stats["out_of_order"] += 1
            return "out_of_order"
        f = r.occupancy / 100.0
        w = self._win[i]
        w.append((r.ts, f))
        # mediana com o instante correspondente (evita atraso na extrapolação)
        srt = sorted(w, key=lambda p: p[1])
        mid = srt[(len(srt) - 1) // 2] if len(srt) % 2 else None
        if mid is not None:
            self.obs_ts[i], self.fill_obs[i] = mid
        else:
            a, b = srt[len(srt) // 2 - 1], srt[len(srt) // 2]
            self.obs_ts[i], self.fill_obs[i] = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        self.last_ts[i] = r.ts
        self.last_reading_ts[i] = r.ts
        self._cycle[i].append((r.ts, f))
        self.stats["applied"] += 1
        return "applied"

    def on_collected(self, i: int, ts: float, residual: float = 0.0) -> None:
        slope = self._cycle_slope(i, ts, window_h=None)
        if slope is not None:
            if self.has_long[i]:
                self.r_long[i] = (1 - self.alpha) * self.r_long[i] + self.alpha * slope
            else:
                self.r_long[i] = slope
                self.has_long[i] = True
        self._win[i].clear()
        self._cycle[i] = []
        self.fill_obs[i] = residual
        self.last_ts[i] = ts
        self.obs_ts[i] = ts
        self.last_collect[i] = ts

    # ------------------------------------------------------------ estimação
    def _cycle_slope(self, i: int, now: float, window_h: float | None = 48.0,
                     min_n: int = 6, min_span_h: float = 12.0) -> float | None:
        pts = self._cycle[i]
        if window_h is not None:
            pts = [p for p in pts if p[0] >= now - window_h * H]
        if len(pts) < min_n:
            return None
        t = np.fromiter((p[0] for p in pts), float) / H
        f = np.fromiter((p[1] for p in pts), float)
        if t[-1] - t[0] < min_span_h:
            return None
        tc = t - t.mean()
        den = float((tc ** 2).sum())
        if den <= 0:
            return None
        return max(0.0, float((tc * (f - f.mean())).sum() / den))

    def prior_rate(self) -> float:
        if self.has_long.any():
            return float(np.median(self.r_long[self.has_long]))
        return self.default_prior

    def long_rate(self, i: int) -> float:
        return float(self.r_long[i]) if self.has_long[i] else self.prior_rate()

    def rate(self, i: int, now: float) -> float:
        s = self._cycle_slope(i, now)
        return s if s is not None else self.long_rate(i)

    def is_stale(self, i: int, now: float, stale_h: float) -> bool:
        return (now - self.last_ts[i]) > stale_h * H

    def estimate(self, now: float, mode: str, stale_h: float, fallback: bool,
                 horizon_h: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
        """Ocupação estimada (fração) para todos os contêineres.

        mode="observed": último valor filtrado (políticas B/C), com estimativa
        por taxa de longo prazo apenas para dados desatualizados (fallback).
        mode="predicted": valor filtrado + taxa × (idade + horizonte) (D).
        Retorna (estimativa, máscara de desatualizados).
        """
        est = self.fill_obs.copy()
        stale = (now - self.last_ts) > stale_h * H
        prior = self.prior_rate()
        for i in range(self.n):
            age_h = (now - self.obs_ts[i]) / H
            if mode == "predicted":
                r = self.rate(i, now) if not stale[i] else (
                    self.r_long[i] if self.has_long[i] else prior)
                if stale[i] and not fallback:
                    r = 0.0
                est[i] = self.fill_obs[i] + r * (age_h + horizon_h)
            elif stale[i] and fallback:
                r = self.r_long[i] if self.has_long[i] else prior
                est[i] = self.fill_obs[i] + r * age_h
        return np.clip(est, 0.0, None), stale

    def online(self, now: float, period_s: float, k: int = 3) -> np.ndarray:
        return (now - self.last_contact) <= k * period_s
