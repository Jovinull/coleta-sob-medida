"""Configuração de cenários.

Todos os parâmetros do modelo ficam aqui, com valores padrão documentados.
A origem de cada valor (literatura, dado público ou hipótese de cenário) está
registrada em ``docs/parametros.md``; nada neste arquivo é medição de campo.

Um cenário é descrito por um dicionário aninhado (YAML) que sobrescreve os
padrões. ``ScenarioConfig.from_dict`` aceita sobrescritas parciais.
"""
from __future__ import annotations

import copy
import dataclasses as dc
import hashlib
import json
from typing import Any

import yaml


@dc.dataclass
class TimeCfg:
    step_min: int = 15            # passo de tempo da simulação (min)
    warmup_days: int = 7          # dias descartados das métricas
    eval_days: int = 28           # dias avaliados (4 semanas completas)
    plan_hour: float = 6.0        # hora do planejamento diário
    shift_start_h: float = 7.0    # início do turno de coleta
    shift_hours: float = 8.0      # duração máxima do turno (inclui retorno)

    @property
    def steps_per_day(self) -> int:
        return int(24 * 60 // self.step_min)

    @property
    def total_days(self) -> int:
        return self.warmup_days + self.eval_days


@dc.dataclass
class GeoCfg:
    kind: str = "synthetic"       # "synthetic" | "osm"
    n_containers: int = 100
    layout: str = "uniform"       # "uniform" | "clustered"
    n_clusters: int = 5
    cluster_sigma_km: float = 0.6
    area_km: float = 6.0          # lado do quadrado (cenário sintético)
    circuity: float = 1.35        # fator de tortuosidade (sintético)
    depot: str = "edge"           # "center" | "edge"  (sintético)
    osm_graph: str = "data/aracaju/aracaju_drive.npz"
    osm_depot_latlon: tuple[float, float] = (-10.9260, -37.0985)


@dc.dataclass
class ContainerCfg:
    volume_l: float = 1100.0      # capacidade nominal (L); 1100 L: monteiro2001manual
    sensor_to_bottom_cm: float = 110.0  # distância sensor → fundo
    mount_offset_cm: float = 10.0       # zona morta / tampa: H = 110 - 10 = 100 cm
    initial_fill_max: float = 0.5        # enchimento inicial ~ U(0, max)


@dc.dataclass
class DemandCfg:
    # Mistura de perfis (proporções) e taxa média diária por perfil (L/dia).
    profile_mix: dict[str, float] = dc.field(default_factory=lambda: {
        "residencial": 0.6, "comercial": 0.25, "institucional": 0.15})
    mean_l_per_day: dict[str, float] = dc.field(default_factory=lambda: {
        "residencial": 300.0, "comercial": 380.0, "institucional": 260.0})
    between_container_cv: float = 0.35   # dispersão (lognormal) entre contêineres
    day_cv: float = 0.25                 # variação dia a dia (gama, média 1)
    step_cv: float = 1.0                 # irregularidade dentro do dia (gama)
    intensity: float = 1.0               # multiplicador global de demanda
    # Eventos esporádicos (descarte volumoso): taxa por contêiner por dia
    event_rate_per_day: float = 1 / 30
    event_volume_frac: tuple[float, float] = (0.15, 0.45)
    # Mudança de regime: a partir do dia `shift_day`, uma fração dos
    # contêineres passa a gerar `shift_factor` vezes a taxa original.
    shift_day: int | None = None
    shift_fraction: float = 0.0
    shift_factor: float = 1.0
    # Calibração alternativa por população atendida (somente documentação):
    per_capita_kg_day: float = 0.88   # RDO coletado, Nordeste (brasil2025sinisa)
    bulk_density_kg_m3: float = 230.0  # resíduo domiciliar solto (monteiro2001manual)


@dc.dataclass
class SensorCfg:
    sample_every_min: int = 60    # período nominal de medição/transmissão
    noise_sd_cm: float = 1.5      # ruído aleatório da distância (cm)
    surface_sd_cm: float = 3.0    # irregularidade da superfície (cm), por leitura
    p_invalid: float = 0.01       # leitura inválida (timeout/eco perdido)
    p_spike: float = 0.005        # leitura espúria curta (obstrução momentânea)
    # Indisponibilidade temporária do dispositivo (processo liga/desliga)
    mtbf_days: float = 60.0       # tempo médio entre falhas temporárias
    mttr_hours: float = 12.0      # duração média da indisponibilidade
    p_permanent_failure: float = 0.0  # fração que falha definitivamente
    stuck_fraction: float = 0.0   # fração com leitura "congelada" após falha


@dc.dataclass
class NetworkCfg:
    p_loss: float = 0.01          # perda independente por mensagem
    p_duplicate: float = 0.002    # duplicação (reentrega)
    delay_median_s: float = 0.5   # atraso (lognormal)
    delay_sigma: float = 1.0
    p_long_delay: float = 0.002   # cauda: atraso de 1 a 6 h (fila/armazenamento)
    # Interrupções regionais de conectividade
    outage_rate_per_day: float = 0.0    # episódios por dia (toda a rede)
    outage_hours: float = 0.0           # duração de cada episódio
    outage_fraction: float = 1.0        # fração dos dispositivos afetados


@dc.dataclass
class FleetCfg:
    n_vehicles: int | None = None  # None → dimensionado automaticamente
    capacity_l: float = 26000.0    # 15 m³ × 400 kg/m³ ≈ 6 t ≈ 26 m³ soltos a 230 kg/m³
    target_utilization: float = 0.7  # para o dimensionamento automático
    speed_kmh: float = 20.0
    service_min: float = 1.0        # ~42 s medidos (carlos2019influence) + posicionamento
    unload_min: float = 15.0        # descarga (exemplo de monteiro2001manual, Tab. 1)


@dc.dataclass
class PolicyCfg:
    name: str = "C"                 # "A" | "B" | "C" | "D"
    routing: str = "ortools"        # "ortools" | "nn2opt"
    theta_hi: float = 0.75          # limiar de coleta obrigatória
    theta_lo: float = 0.50          # limiar de coleta opcional (C/D)
    theta_crit: float = 0.95        # D: risco de transbordar antes do próximo ciclo
    may_go_m_per_l: float = 1.0     # prêmio (m de rota por litro coletado) p/ opcionais
    periodic_target: float = 0.8    # A: frequência p/ enchimento médio alvo
    periodic_max_days: int = 7
    stale_hours: float = 24.0       # dado desatualizado após este tempo
    fallback: bool = True           # estimativa por taxa quando desatualizado
    solver: str = "greedy_descent"  # "greedy_descent" (determinístico) | "gls"
    solver_time_s: float = 30.0     # limite de tempo (GLS) / salvaguarda (descida)


@dc.dataclass
class ScenarioConfig:
    name: str = "base"
    seed: int = 1
    time: TimeCfg = dc.field(default_factory=TimeCfg)
    geo: GeoCfg = dc.field(default_factory=GeoCfg)
    container: ContainerCfg = dc.field(default_factory=ContainerCfg)
    demand: DemandCfg = dc.field(default_factory=DemandCfg)
    sensor: SensorCfg = dc.field(default_factory=SensorCfg)
    network: NetworkCfg = dc.field(default_factory=NetworkCfg)
    fleet: FleetCfg = dc.field(default_factory=FleetCfg)
    policy: PolicyCfg = dc.field(default_factory=PolicyCfg)
    record_trace: bool = False

    # ---------------------------------------------------------------- utils
    def to_dict(self) -> dict[str, Any]:
        return dc.asdict(self)

    def fingerprint(self) -> str:
        """Hash estável da configuração (proveniência)."""
        blob = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None = None) -> "ScenarioConfig":
        cfg = cls()
        if d:
            _merge_into(cfg, d)
        return cfg

    @classmethod
    def from_yaml(cls, path: str) -> "ScenarioConfig":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh))

    def with_overrides(self, d: dict[str, Any]) -> "ScenarioConfig":
        new = copy.deepcopy(self)
        _merge_into(new, d)
        return new


def _merge_into(obj: Any, d: dict[str, Any]) -> None:
    for key, val in d.items():
        if not hasattr(obj, key):
            raise KeyError(f"parâmetro desconhecido: {type(obj).__name__}.{key}")
        cur = getattr(obj, key)
        if dc.is_dataclass(cur) and isinstance(val, dict):
            _merge_into(cur, val)
        else:
            if isinstance(cur, tuple) and isinstance(val, list):
                val = tuple(val)
            setattr(obj, key, val)


def deep_update(base: dict, upd: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in upd.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = v
    return out
