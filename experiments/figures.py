"""Figuras científicas (PDF vetorial em paper/figures/ e PNG em figures/).

    python -m experiments.figures

Todas as figuras são geradas a partir de execuções registradas
(experiments/raw, experiments/results) ou de execuções do simulador feitas
aqui mesmo com sementes fixas (indicadas na legenda de cada figura).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

from experiments.labels import plain as cond_plain  # noqa: E402
from wastesim import sensor as S  # noqa: E402
from wastesim.config import ContainerCfg, ScenarioConfig  # noqa: E402
from wastesim.demand import PROFILES  # noqa: E402
from wastesim.simulation import Simulation  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "experiments/results"
OUTP = ROOT / "paper/figures"
OUTG = ROOT / "figures"
# paleta validada (dataviz/palette.md, slots 1–4) + cinza neutro para a linha de base A
COL = {"A": "#52514e", "B": "#eda100", "B-OR": "#1baf7a", "C": "#2a78d6", "D": "#eb6834"}
MRK = {"A": "s", "B": "v", "B-OR": "^", "C": "o", "D": "D"}
ORDER = ["A", "B", "B-OR", "C", "D"]
PROF_COL = {"residencial": "#2a78d6", "comercial": "#eb6834", "institucional": "#1baf7a"}
INK, MUTED, GRID, ROAD = "#0b0b0b", "#52514e", "#e4e4e0", "#d3d6da"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Nimbus Roman", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.03, "axes.formatter.use_locale": False,
})


def comma(ax, axis="both", d=None):
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: (f"{v:.{d}f}" if d is not None else f"{v:g}").replace(".", ","))
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(fmt)
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(fmt)


def save(fig, name):
    OUTP.mkdir(parents=True, exist_ok=True)
    OUTG.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTP / f"{name}.pdf")
    fig.savefig(OUTG / f"{name}.png", dpi=170)
    plt.close(fig)
    print("figura", name)


def roads(ax, lw=0.3):
    z = json.loads((ROOT / "data/aracaju/roads.json").read_text())
    s = np.array(z["segments"]).reshape(-1, 4)
    segs = np.stack([s[:, [1, 0]], s[:, [3, 2]]], 1)
    ax.add_collection(LineCollection(segs, colors=ROAD, linewidths=lw, zorder=0))
    b = z["boundary"]
    rings = [r for poly in b["coordinates"] for r in poly] if b["type"] == "MultiPolygon" else b["coordinates"]
    for r in rings:
        r = np.array(r)
        ax.plot(r[:, 0], r[:, 1], color=MUTED, lw=0.6, ls=(0, (3, 2)), zorder=0)
    ax.set_aspect(1 / np.cos(np.radians(-10.95)))
    ax.set_xticks([]), ax.set_yticks([])
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)


def ci_dot(ax, x, m, lo, hi, color, marker, label=None, off=0.0):
    ax.errorbar(x + off, m, yerr=[[m - lo], [hi - m]], fmt=marker, color=color, ms=5.5, capsize=2.5,
                elinewidth=1.1, mec="white", mew=0.6, label=label)


# ------------------------------------------------------------------ cenário
def fig_cenario():
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 4.6))
    for ax, n in zip(axs, (100, 500)):
        sim = Simulation(ScenarioConfig.from_dict({"seed": 1001, "geo": {"kind": "osm", "n_containers": n}}))
        roads(ax)
        ll = sim.geo.latlon
        prof = np.array(sim.demand.profile_names)
        for p in PROFILES:
            k = prof == p
            ax.scatter(ll[1:][k, 1], ll[1:][k, 0], s=4 + sim.demand.mu_l_day[k] / 18, c=PROF_COL[p],
                       edgecolors="white", linewidths=0.4, label=p, zorder=3)
        ax.scatter(ll[0, 1], ll[0, 0], marker="D", s=40, c=INK, zorder=4, label="depósito")
        ax.set_title(f"$N$ = {n} (semente 1001)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.03),
               title="perfil de geração (área do círculo ∝ taxa média diária)", title_fontsize=8)
    fig.text(0.5, 0.0, "Malha viária: © colaboradores do OpenStreetMap (ODbL). Posições hipotéticas.",
             ha="center", fontsize=7, color=MUTED)
    save(fig, "fig_cenario")


# ------------------------------------------------------------------ sensor
def fig_sensor():
    c = ContainerCfg()
    d = np.linspace(5, 120, 300)
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 2.6))
    ax = axs[0]
    ax.plot(d, d / 50 * 100, color=COL["D"], label="2024: $d/T_{max}\\cdot100$ ($T_{max}$ = 50 cm)")
    occ = [S.occupancy_from_distance(x, c)[0] for x in d]
    ax.plot(d, occ, color=COL["C"], label="2026: $100(H-(d-off))/H$, limitada")
    ax.axvline(51, color=MUTED, lw=0.8, ls=":")
    ax.annotate("eco perdido → 51 cm\n(biblioteca de 2024)", (51, 102), (14, 150), fontsize=7, color=MUTED,
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.6))
    ax.set_xlabel("distância medida $d$ (cm)")
    ax.set_ylabel("valor publicado (%)")
    ax.legend(frameon=False, loc="upper left", fontsize=7)
    ax.set_title("(a) fórmula de 2024 vs. corrigida")
    comma(ax)
    ax = axs[1]
    rng = np.random.default_rng(3)
    f = rng.uniform(0, 1, 1500)
    for k, (ns, ss, lab, col) in enumerate([(1.5, 3, "base (σ = 1,5 cm; sup. 3 cm)", COL["C"]),
                                            (9, 18, "6× (σ = 9 cm; sup. 18 cm)", COL["D"])]):
        dm = S.distance_from_fill(f, c) + ns * rng.standard_normal(f.size) - ss * np.abs(rng.standard_normal(f.size))
        o = np.array([S.occupancy_from_distance(x, c)[0] or np.nan for x in dm])
        ax.scatter(100 * f, o, s=3, color=col, alpha=0.35, label=lab, rasterized=True, edgecolors="none")
    ax.plot([0, 100], [0, 100], color=INK, lw=0.8)
    ax.set_xlabel("ocupação verdadeira (%)")
    ax.set_ylabel("ocupação medida (%)")
    ax.set_title("(b) modelo de medição (1.500 leituras)")
    ax.legend(frameon=False, loc="upper left", markerscale=3, fontsize=7)
    comma(ax)
    fig.tight_layout()
    save(fig, "fig_sensor")


# ------------------------------------------------------------------ séries e mapas do replay
def replay():
    return json.loads((RES / "replay.json").read_text())


def fig_series():
    R = replay()
    t = np.array(R["frames_t"]) / 86400
    A, D = (np.array(r["fill"]) for r in R["runs"])
    # quatro contêineres com taxas diferentes (maior, mediana, ...)
    mean_fill = A.mean(0)
    idx = np.argsort(mean_fill)[[-1, -12, len(mean_fill) // 2, 8]]
    fig, axs = plt.subplots(2, 2, figsize=(6.3, 3.7), sharex=True, sharey=True)
    for ax, i in zip(axs.ravel(), idx):
        ax.plot(t, 100 * A[:, i], color=COL["A"], lw=1.2, label="A (periódica)")
        ax.plot(t, 100 * D[:, i], color=COL["D"], lw=1.2, ls="--", label="D (preditiva)")
        ax.axhline(75, color=MUTED, lw=0.7, ls=":")
        ax.set_title(R["containers"][i]["id"], fontsize=8.5)
        ax.set_ylim(0, 105)
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="upper center", ncol=2, fontsize=8)
    for ax in axs[1]:
        ax.set_xlabel("dia da simulação")
    for ax in axs[:, 0]:
        ax.set_ylabel("ocupação verdadeira (%)")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "fig_series")


def fig_mapa_rotas():
    R = replay()
    t = np.array(R["frames_t"])
    day = int(t[0] // 86400) + 2
    lat = np.array([c["lat"] for c in R["containers"]])
    lon = np.array([c["lon"] for c in R["containers"]])
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 4.6))
    vc = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    for ax, run in zip(axs, R["runs"]):
        roads(ax)
        full_h = (np.array(run["fill"]) >= 0.999).sum(0)
        for k, poly in enumerate(run["paths"].get(str(day), [])):
            p = np.array(poly)
            ax.plot(p[:, 1], p[:, 0], color=vc[k % 4], lw=1.3, alpha=0.85, zorder=2, label=f"veículo {k + 1}")
        ax.scatter(lon, lat, s=7, c="#9a9a96", zorder=3, edgecolors="none")
        m = full_h > 0
        sc = ax.scatter(lon[m], lat[m], s=8 + 3 * full_h[m], facecolors="none", edgecolors="#e34948",
                        linewidths=0.9, zorder=4)
        ax.scatter(*R["depot"][::-1], marker="D", s=36, c=INK, zorder=5)
        ax.set_title(f"Política {run['policy']} ({run['label']}) — rotas do dia {day + 1}\n"
                     f"círculos: horas cheio em 7 dias (total {int(full_h.sum())} h)", fontsize=8.5)
        ax.legend(frameon=False, loc="lower left", fontsize=7)
    fig.text(0.5, 0.01, f"Traço gravado, semente {R['seed']}, N = {R['n']}. Rotas desenhadas pelos caminhos mínimos da malha. "
             "© colaboradores do OpenStreetMap.", ha="center", fontsize=7, color=MUTED)
    save(fig, "fig_mapa_rotas")


def fig_falha():
    z = np.load(RES / "trace_falha.npz")
    t = z["t"] / 86400
    aff = z["affected"]
    fill, est, stale = z["fill"], z["est"], z["stale"]
    o0, o1 = z["outage"] / 86400
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 2.5))
    ax = axs[0]
    ax.axvspan(o0, o1, color="#e34948", alpha=0.10, lw=0)
    ax.plot(t, 100 * stale.mean(1), color=COL["C"], label="todos")
    ax.plot(t, 100 * stale[:, aff].mean(1), color=COL["D"], ls="--", label="área afetada")
    ax.set_ylabel("contêineres sem dado recente (%)")
    ax.set_xlabel("dia")
    ax.set_title("(a) dados desatualizados (> 24 h)")
    ax.legend(frameon=False, fontsize=7)
    ax.set_xlim(7, t.max())
    ax = axs[1]
    k = aff[np.argmax(fill[(t >= o0) & (t <= o1)][:, aff].mean(0))]
    ax.axvspan(o0, o1, color="#e34948", alpha=0.10, lw=0)
    ax.plot(t, 100 * fill[:, k], color=INK, lw=1.2, label="verdadeira")
    e = est[:, k].astype(float)
    e[e < 0] = np.nan
    ax.plot(t, 100 * e, color=COL["C"], lw=1.2, ls="--", label="estimada (último valor)")
    ax.set_xlim(o0 - 1.5, o1 + 2)
    ax.set_ylim(0, 105)
    ax.set_xlabel("dia")
    ax.set_ylabel("ocupação (%)")
    ax.set_title("(b) um contêiner da área afetada")
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    save(fig, "fig_falha")


# ------------------------------------------------------------------ distribuição na coleta
def fig_hist_coleta():
    fig, ax = plt.subplots(figsize=(6.3, 2.4))
    bins = np.linspace(0, 1, 21)
    for pol, rt in [("A", "ortools"), ("B", "nn2opt"), ("C", "ortools"), ("D", "ortools")]:
        vals = []
        for s in range(1001, 1006):
            sim = Simulation(ScenarioConfig.from_dict({"seed": s, "geo": {"kind": "osm", "n_containers": 100},
                                                       "policy": {"name": pol, "routing": rt}}))
            sim.run()
            vals += sim.coll_fill
        h, _ = np.histogram(vals, bins=bins)
        ax.stairs(100 * h / h.sum(), 100 * bins, color=COL[pol], label=f"{pol} (n = {len(vals)})",
                  lw=1.5, ls={"A": "-", "B": ":", "C": "-", "D": "--"}[pol])
    ax.axvline(50, color=MUTED, lw=0.7, ls=":")
    ax.set_xlabel("ocupação verdadeira no momento da coleta (%)")
    ax.set_ylabel("coletas (%)")
    ax.legend(frameon=False, ncol=4, loc="upper left")
    ax.set_title("Distribuição da ocupação na coleta ($N$ = 100; sementes 1001–1005; 28 dias)")
    save(fig, "fig_hist_coleta")


# ------------------------------------------------------------------ E1
def fig_e1():
    d = pd.read_csv(RES / "descritivas.csv")
    d = d[d.exp == "E1"]
    fig, axs = plt.subplots(2, 3, figsize=(6.3, 4.0))
    for j, n in enumerate((20, 100, 500)):
        for i, (m, lab) in enumerate((("km_per_day", "km/dia"), ("overflow_pct", "transbordamento (% vol.)"))):
            ax = axs[i, j]
            for k, pol in enumerate(ORDER):
                g = d[(d.condition == f"N{n}") & (d.policy == pol) & (d.metric == m)]
                if len(g):
                    ci_dot(ax, k, g["mean"].iloc[0], g.ci_lo.iloc[0], g.ci_hi.iloc[0], COL[pol], MRK[pol])
            ax.set_xticks(range(5), ORDER, fontsize=7.5)
            ax.set_xlim(-0.6, 4.6)
            if i == 0:
                ax.set_title(f"$N$ = {n}")
            if j == 0:
                ax.set_ylabel(lab)
            hi = d[(d.condition == f"N{n}") & (d.metric == m)].ci_hi.max()
            ax.set_ylim(0, hi * 1.12)
            comma(ax, "y")
    fig.tight_layout()
    save(fig, "fig_e1")


def fig_e2():
    p = pd.read_csv(RES / "e2_fronteira.csv")
    fig, ax = plt.subplots(figsize=(6.3, 3.4))
    for pol in ["A", "B-OR", "C", "D"]:
        g = p[p.policy == pol].sort_values("ov_mean")
        ax.plot(g.ov_mean, g.km_mean, color=COL[pol], lw=1.2, zorder=2)
        for _, r in g.iterrows():
            ax.errorbar(r.ov_mean, r.km_mean, xerr=[[r.ov_mean - r.ov_lo], [r.ov_hi - r.ov_mean]],
                        yerr=[[r.km_mean - r.km_lo], [r.km_hi - r.km_mean]], fmt=MRK[pol], color=COL[pol],
                        ms=5, capsize=2, elinewidth=0.9, mec="white", mew=0.5, zorder=3)
        for _, r in (g.iloc[[0, -1]] if pol == "A" else g.iloc[[-1]]).iterrows():
            ax.annotate(f"{r.level:g}".replace(".", ","), (r.ov_mean, r.km_mean), xytext=(4, 3),
                        textcoords="offset points", fontsize=6.5, color=MUTED)
    ax.axvline(1.0, color=MUTED, lw=0.7, ls=":")
    ax.set_xlabel("transbordamento (% do volume gerado)")
    ax.set_ylabel("distância (km/dia)")
    ax.set_xlim(left=0)
    ax.text(1.05, ax.get_ylim()[1] * 0.985, "1%", fontsize=7, color=MUTED, va="top")
    from matplotlib.lines import Line2D
    ax.legend([Line2D([], [], color=COL[k], marker=MRK[k], ls="-") for k in ["A", "B-OR", "C", "D"]],
              ["A (alvo de ocupação γ)", "B-OR (limiar θ)", "C (limiar θ)", "D (limiar θ)"],
              frameon=False, loc="upper right")
    comma(ax)
    save(fig, "fig_e2")


def fig_e3():
    d = pd.read_csv(RES / "descritivas.csv")
    d = d[(d.exp == "E3") & (d.metric == "overflow_pct")]
    conds = list(dict.fromkeys(pd.read_csv(RES / "comparacoes.csv").query("exp=='E3'").condition))
    conds = ["base"] + [c for c in conds if c != "base"]
    fig, ax = plt.subplots(figsize=(6.3, 4.4))
    y = np.arange(len(conds))[::-1]
    for k, pol in enumerate(["A", "B-OR", "C", "D"]):
        for yy, c in zip(y, conds):
            g = d[(d.condition == c) & (d.policy == pol)]
            if len(g):
                m, lo, hi = g["mean"].iloc[0], g.ci_lo.iloc[0], g.ci_hi.iloc[0]
                ax.errorbar(m, yy + (k - 1.5) * 0.17, xerr=[[m - lo], [hi - m]], fmt=MRK[pol], color=COL[pol],
                            ms=4.5, capsize=1.5, elinewidth=0.9, mec="white", mew=0.4,
                            label=pol if yy == y[0] else None)
    ax.set_yticks(y, [cond_plain(c) for c in conds], fontsize=7.5)
    ax.set_xlabel("transbordamento (% do volume gerado), média e IC 95%")
    ax.legend(frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), handletextpad=0.3)
    ax.set_xlim(left=0)
    comma(ax, "x")
    save(fig, "fig_e3")


def fig_e4():
    c = pd.read_csv(RES / "comparacoes.csv")
    c = c[(c.exp == "E4") & (c.ref == "A")]
    conds = list(dict.fromkeys(c.condition))
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 3.3), sharey=True)
    y = np.arange(len(conds))[::-1]
    for ax, metric, lab in ((axs[0], "km_per_day", "Δ km/dia vs. A (%)"),
                            (axs[1], "overflow_pct", "Δ transbordamento vs. A (p.p.)")):
        for k, pol in enumerate(["B-OR", "C", "D"]):
            for yy, cond in zip(y, conds):
                r = c[(c.condition == cond) & (c.alt == pol) & (c.metric == metric)]
                if not len(r):
                    continue
                r = r.iloc[0]
                if metric == "km_per_day":
                    m, lo, hi = 100 * r["diff"] / r.mean_ref, 100 * r.ci_lo / r.mean_ref, 100 * r.ci_hi / r.mean_ref
                else:
                    m, lo, hi = r["diff"], r.ci_lo, r.ci_hi
                ax.errorbar(m, yy + (k - 1) * 0.2, xerr=[[m - lo], [hi - m]], fmt=MRK[pol], color=COL[pol],
                            ms=4.5, capsize=1.5, elinewidth=0.9, mec="white", mew=0.4,
                            label=pol if yy == y[0] else None)
        ax.axvline(0, color=INK, lw=0.8)
        ax.set_xlabel(lab)
        comma(ax, "x")
    axs[0].set_yticks(y, [cond_plain(c) for c in conds], fontsize=7.5)
    h, lb = axs[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.legend(h, lb, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.0), handletextpad=0.3)
    save(fig, "fig_e4")


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["cenario", "sensor", "series", "mapa_rotas", "falha", "hist_coleta",
                             "e1", "e2", "e3", "e4"]
    for w in which:
        try:
            globals()[f"fig_{w}"]()
        except FileNotFoundError as e:
            print("pulado", w, e)
