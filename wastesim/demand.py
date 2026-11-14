"""Modelo estocástico de geração de resíduos (volume solto, em litros).

Para o contêiner i, no passo t do dia d (dia da semana w, hora h):

    q[i,t] = mu_i · I · W[p_i, w] · Z[i,d] · H[p_i, h] · E[i,t] + eventos

* mu_i  — taxa média diária de longo prazo (L/dia). Para cada perfil p há uma
          taxa mediana; a heterogeneidade entre contêineres é lognormal com
          média 1 e coeficiente de variação ``between_container_cv``.
* I     — intensidade global do cenário (análise de sensibilidade).
* W     — perfil semanal (média 1 na semana).
* Z     — fator diário ~ Gama(média 1, CV = ``day_cv``): dias atípicos.
* H     — perfil horário (soma 1 no dia).
* E     — irregularidade intradiária ~ Gama(média 1, CV = ``step_cv``):
          descartes chegam em "pacotes", não continuamente.
* eventos — descartes volumosos esporádicos (processo de Poisson por
          contêiner), distribuídos ao longo de 1 h.

Os perfis semanais e horários são **hipóteses de cenário**: não foram
calibrados com medições de contêineres reais (indisponíveis para este estudo).
A ordem de grandeza de mu_i é discutida em ``docs/parametros.md``.

Toda a matriz de geração é sorteada antes da simulação a partir de um fluxo
aleatório próprio, de modo que todas as políticas comparadas em uma mesma
semente recebem exatamente a mesma demanda (números aleatórios comuns).
"""
from __future__ import annotations

import dataclasses as dc

import numpy as np

from .config import ContainerCfg, DemandCfg, TimeCfg

PROFILES = ("residencial", "comercial", "institucional")

# Perfis semanais (segunda → domingo), normalizados para média 1.
_WEEKLY = {
    "residencial": [1.00, 0.97, 0.97, 0.97, 1.00, 1.04, 1.05],
    "comercial": [1.05, 1.05, 1.05, 1.05, 1.10, 0.75, 0.30],
    "institucional": [1.30, 1.30, 1.30, 1.30, 1.25, 0.30, 0.25],
}
# Perfis horários relativos (0h → 23h), normalizados para soma 1.
_HOURLY = {
    "residencial": [.2, .1, .1, .1, .2, .5, 1.2, 1.6, 1.4, 1.0, .9, 1.0,
                    1.1, 1.0, .8, .8, .9, 1.2, 1.6, 1.7, 1.4, 1.0, .6, .3],
    "comercial": [.05, .05, .05, .05, .05, .1, .3, .7, 1.2, 1.4, 1.5, 1.6,
                  1.7, 1.6, 1.5, 1.5, 1.5, 1.4, 1.2, .9, .6, .3, .1, .05],
    "institucional": [.02, .02, .02, .02, .02, .05, .4, 1.3, 1.6, 1.6, 1.5, 1.6,
                      1.8, 1.6, 1.5, 1.4, 1.2, .7, .3, .2, .1, .05, .02, .02],
}


def weekly_profile(p: str) -> np.ndarray:
    w = np.asarray(_WEEKLY[p], float)
    return w / w.mean()


def hourly_profile(p: str) -> np.ndarray:
    h = np.asarray(_HOURLY[p], float)
    return h / h.sum()


def _gamma_mean1(rng: np.random.Generator, cv: float, size) -> np.ndarray:
    if cv <= 0:
        return np.ones(size)
    k = 1.0 / cv ** 2
    return rng.gamma(k, 1.0 / k, size=size)


@dc.dataclass
class Demand:
    profile: np.ndarray        # (N,) índice do perfil
    mu_l_day: np.ndarray       # (N,) taxa média de longo prazo (sem eventos) — usada no
                               #      dimensionamento da frota
    inflow_l: np.ndarray       # (N, T) volume gerado por passo
    event_count: int
    mu_total_l_day: np.ndarray | None = None  # (N,) média de longo prazo INCLUINDO o valor
                               # esperado dos descartes volumosos — o "histórico perfeito" da política A

    @property
    def profile_names(self) -> list[str]:
        return [PROFILES[k] for k in self.profile]


def generate(cfg: DemandCfg, tcfg: TimeCfg, ccfg: ContainerCfg, n: int,
             rng: np.random.Generator) -> Demand:
    spd = tcfg.steps_per_day
    steps_per_h = spd // 24
    days = tcfg.total_days
    T = days * spd

    names = list(cfg.profile_mix)
    probs = np.array([cfg.profile_mix[k] for k in names], float)
    probs /= probs.sum()
    prof_local = rng.choice(len(names), size=n, p=probs)
    profile = np.array([PROFILES.index(names[k]) for k in prof_local])

    s = np.sqrt(np.log(1 + cfg.between_container_cv ** 2))
    het = rng.lognormal(-s ** 2 / 2, s, size=n)          # média 1
    base = np.array([cfg.mean_l_per_day[PROFILES[k]] for k in profile])
    mu = base * het

    W = np.stack([weekly_profile(p) for p in PROFILES])   # (3,7)
    Hh = np.stack([hourly_profile(p) for p in PROFILES])  # (3,24)
    Hs = np.repeat(Hh, steps_per_h, axis=1) / steps_per_h  # (3, spd)

    Z = _gamma_mean1(rng, cfg.day_cv, (n, days))
    E = _gamma_mean1(rng, cfg.step_cv, (n, T))

    dow = np.arange(days) % 7                               # dia 0 = segunda
    daily = mu[:, None] * cfg.intensity * W[profile][:, dow] * Z  # (N, days)
    inflow = np.repeat(daily, spd, axis=1) * np.tile(Hs[profile], (1, days)) * E

    if cfg.shift_day is not None and cfg.shift_fraction > 0:
        k = int(round(cfg.shift_fraction * n))
        idx = rng.choice(n, size=k, replace=False)
        inflow[idx, cfg.shift_day * spd:] *= cfg.shift_factor

    n_ev = rng.poisson(cfg.event_rate_per_day * days, size=n)
    lo, hi = cfg.event_volume_frac
    total_ev = 0
    for i in np.nonzero(n_ev)[0]:
        for _ in range(n_ev[i]):
            t0 = rng.integers(0, T - steps_per_h)
            vol = rng.uniform(lo, hi) * ccfg.volume_l
            inflow[i, t0:t0 + steps_per_h] += vol / steps_per_h
            total_ev += 1
    ev_mean = cfg.event_rate_per_day * 0.5 * (lo + hi) * ccfg.volume_l
    return Demand(profile=profile, mu_l_day=mu * cfg.intensity,
                  inflow_l=inflow, event_count=total_ev,
                  mu_total_l_day=mu * cfg.intensity + ev_mean)
