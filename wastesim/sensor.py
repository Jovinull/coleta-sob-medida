"""Sensor ultrassônico virtual e conversão distância → ocupação.

Geometria adotada: contêiner prismático (seção transversal constante), sensor
fixado no topo apontando para baixo. Sejam

    D0  distância do sensor ao fundo (cm)
    off deslocamento de montagem / zona morta (tampa, borda) (cm)
    H   = D0 − off   altura útil (cm)

Para seção constante, a fração de volume ocupada é igual à fração de altura:

    ocupação(%) = 100 · (H − (d − off)) / H ,   limitada a [0, 100]

em que d é a distância medida até a superfície dos resíduos. Para geometrias
não prismáticas (tampas inclinadas, fundos arredondados) seria necessária uma
curva altura→volume específica; essa generalização **não** é feita aqui.

Modelo de medição (hipóteses, ver docs/modelo-sensor.md):

    d_med = d_real + N(0, σ_ruído) − |N(0, σ_sup)|

O termo negativo semi-normal representa a irregularidade da superfície: o
HC-SR04 retorna o primeiro eco dentro do cone, isto é, o ponto mais alto do
monte de resíduos, de modo que a ocupação tende a ser **superestimada**.
Leituras inválidas (eco perdido) e espúrias (obstrução momentânea perto do
sensor) ocorrem com probabilidades configuráveis.
"""
from __future__ import annotations

import dataclasses as dc
import math

import numpy as np

from .config import ContainerCfg, SensorCfg, TimeCfg

HCSR04_MIN_CM = 2.0      # faixa nominal do HC-SR04 (datasheet): 2 cm a 400 cm
HCSR04_MAX_CM = 400.0
PLAUSIBILITY_MARGIN_CM = 15.0


def useful_height_cm(c: ContainerCfg) -> float:
    return c.sensor_to_bottom_cm - c.mount_offset_cm


def distance_from_fill(fill: np.ndarray | float, c: ContainerCfg):
    """Distância verdadeira sensor → superfície para uma fração de volume."""
    return c.sensor_to_bottom_cm - np.asarray(fill) * useful_height_cm(c)


def occupancy_from_distance(d_cm: float | None, c: ContainerCfg) -> tuple[float | None, bool]:
    """Converte distância (cm) em ocupação (%) com verificação de validade.

    Retorna (ocupação, válida). Leituras ausentes, não finitas, fora da faixa
    do HC-SR04 ou além do fundo do contêiner (+ margem) são inválidas.
    """
    if d_cm is None or not math.isfinite(d_cm):
        return None, False
    if d_cm < HCSR04_MIN_CM or d_cm > HCSR04_MAX_CM:
        return None, False
    if d_cm > c.sensor_to_bottom_cm + PLAUSIBILITY_MARGIN_CM:
        return None, False
    H = useful_height_cm(c)
    occ = 100.0 * (H - (d_cm - c.mount_offset_cm)) / H
    return min(100.0, max(0.0, occ)), True


def speed_of_sound_m_s(temp_c: float) -> float:
    """Aproximação linear usual: c ≈ 331,3 + 0,606·T (m/s)."""
    return 331.3 + 0.606 * temp_c


@dc.dataclass
class SensorStreams:
    """Números aleatórios pré-sorteados (comuns a todas as políticas)."""
    phase: np.ndarray          # (N,) defasagem da amostragem, em passos
    noise: np.ndarray          # (N, T) ruído gaussiano padrão
    surface: np.ndarray        # (N, T) |N(0,1)|
    u_invalid: np.ndarray      # (N, T) uniformes
    spike_cm: np.ndarray       # (N, T) distância espúria
    dev_up: np.ndarray         # (N, T) bool: dispositivo operacional
    stuck_from: np.ndarray     # (N,) passo a partir do qual a leitura congela (-1 = nunca)


def generate_streams(scfg: SensorCfg, tcfg: TimeCfg, n: int,
                     rng: np.random.Generator) -> SensorStreams:
    spd = tcfg.steps_per_day
    T = tcfg.total_days * spd
    k = max(1, scfg.sample_every_min // tcfg.step_min)
    phase = rng.integers(0, k, size=n)
    noise = rng.standard_normal((n, T)).astype(np.float32)
    surface = np.abs(rng.standard_normal((n, T))).astype(np.float32)
    u_inv = rng.random((n, T)).astype(np.float32)
    spike = rng.uniform(3.0, 20.0, size=(n, T)).astype(np.float32)

    # Indisponibilidade temporária: cadeia de Markov de dois estados.
    up = np.ones((n, T), dtype=bool)
    if scfg.mtbf_days > 0 and scfg.mttr_hours > 0:
        step_h = tcfg.step_min / 60
        p_fail = step_h / (scfg.mtbf_days * 24)
        p_rep = min(1.0, step_h / scfg.mttr_hours)
        state = np.ones(n, dtype=bool)
        u = rng.random((n, T))
        for t in range(T):
            fail = state & (u[:, t] < p_fail)
            rep = (~state) & (u[:, t] < p_rep)
            state = (state & ~fail) | rep
            up[:, t] = state
    # Falha permanente: a partir de um instante uniforme no horizonte.
    if scfg.p_permanent_failure > 0:
        dead = rng.random(n) < scfg.p_permanent_failure
        t_dead = rng.integers(0, T, size=n)
        for i in np.nonzero(dead)[0]:
            up[i, t_dead[i]:] = False
    stuck_from = np.full(n, -1)
    if scfg.stuck_fraction > 0:
        st = rng.random(n) < scfg.stuck_fraction
        stuck_from[st] = rng.integers(0, T, size=int(st.sum()))
    return SensorStreams(phase, noise, surface, u_inv, spike, up, stuck_from)


def measure(true_fill: float, i: int, t: int, s: SensorStreams,
            scfg: SensorCfg, c: ContainerCfg) -> float | None:
    """Distância medida (cm) ou None (eco perdido)."""
    u = s.u_invalid[i, t]
    if u < scfg.p_invalid:
        return None
    if u < scfg.p_invalid + scfg.p_spike:
        return float(s.spike_cm[i, t])
    d = float(distance_from_fill(true_fill, c))
    d += scfg.noise_sd_cm * float(s.noise[i, t]) - scfg.surface_sd_cm * float(s.surface[i, t])
    return d
