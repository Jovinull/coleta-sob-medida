"""Rótulos legíveis das condições experimentais (tabelas e figuras)."""
from __future__ import annotations

COND = {
    "base": "base",
    "perda_5%": "perda 5%",
    "perda_20%": "perda 20%",
    "perda_50%": "perda 50%",
    "interrupcao_48h": "interrupção 48 h",
    "interrupcao_48h_sem_fallback": "interrupção 48 h, sem fallback",
    "ruido_0": "sem ruído",
    "ruido_3x": "ruído ×3",
    "ruido_6x": "ruído ×6",
    "falha_perm_10%": "falha permanente 10%",
    "falha_perm_30%": "falha permanente 30%",
    "falha_perm_30%_sem_fallback": "falha perm. 30%, sem fallback",
    "congelado_10%": "congelados 10%",
    "amostra_15min": "amostragem 15 min",
    "amostra_6h": "amostragem 6 h",
    "amostra_24h": "amostragem 24 h",
    "demanda_0.7": "demanda ×0,7",
    "demanda_1.3": "demanda ×1,3",
    "alta_variabilidade": "alta variabilidade",
    "mudanca_regime_30%x1.6": "mudança de regime (30%, ×1,6)",
    "surto_geral_x1.3": "aumento geral (×1,3)",
    "frota_reduzida": "frota reduzida (1 veículo)",
    "layout_agrupado": "layout agrupado",
    "velocidade_15": "velocidade 15 km/h",
    "velocidade_30": "velocidade 30 km/h",
    "greedy_descent": "descida gulosa",
    "gls": "GLS (5 s)",
}


def plain(c: str) -> str:
    return COND.get(c, c.replace("_", " "))


def latex(c: str) -> str:
    s = plain(c).replace("%", r"\%").replace("×", r"$\times$")
    return s.replace("fallback", r"\emph{fallback}")
