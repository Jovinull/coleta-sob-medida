"""Análise estatística dos experimentos (protocolo: docs/protocolo-experimental.md).

    python -m experiments.analysis

Lê experiments/raw/*.jsonl e escreve:
* experiments/results/descritivas.csv       — média, dp, mediana, IQR, IC95 por condição/política
* experiments/results/comparacoes.csv       — comparações pareadas (Wilcoxon + Holm + bootstrap)
* experiments/results/e2_fronteira.csv, e2_km_ao_nivel.csv
* experiments/results/dashboard.json        — resumo para o painel
* paper/resultados/*.tex                    — tabelas e macros para o artigo
Nenhum resultado é removido; execuções com status "error" são contadas e relatadas.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "experiments/raw"
RES = ROOT / "experiments/results"
TEX = ROOT / "paper/resultados"
B = 10_000
RNG = np.random.default_rng(20261114)
PRIMARY = ["km_per_day", "overflow_pct"]
LABEL = {"km_per_day": "km/dia", "overflow_pct": "transbordamento (\\% vol.)",
         "mean_fill_at_collection": "ocupação média na coleta",
         "pct_collections_below_50": "coletas com ocupação < 50\\%"}
ORDER = ["A", "B", "B-OR", "C", "D"]


# ------------------------------------------------------------------ dados
def load(exp: str) -> pd.DataFrame:
    rows = []
    f = RAW / f"{exp}.jsonl"
    if not f.exists():
        return pd.DataFrame()
    seen = {}
    for line in f.read_text().splitlines():
        d = json.loads(line)
        key = (d["condition"], d["policy"], d["seed"])
        seen[key] = d            # a última execução válida prevalece (retomada)
    for (c, p, s), d in seen.items():
        row = {}
        if d["status"] == "ok":
            row.update({k: v for k, v in d["metrics"].items() if not isinstance(v, (dict, list))})
            row["policy_name"] = row.pop("policy", None)
        row.update(exp=exp, condition=c, policy=p, seed=s, status=d["status"])
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ estatística
def boot_ci(x: np.ndarray, b: int = B) -> tuple[float, float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 2:
        return (np.nan, np.nan)
    idx = RNG.integers(0, x.size, size=(b, x.size))
    m = x[idx].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def rank_biserial(d: np.ndarray) -> float:
    """Correlação bisserial de postos pareada (fórmula da diferença simples, Kerby 2014)."""
    d = d[d != 0]
    if d.size == 0:
        return 0.0
    r = rankdata(np.abs(d))
    return float((r[d > 0].sum() - r[d < 0].sum()) / r.sum())


def paired(df: pd.DataFrame, metric: str, ref: str, alt: str, cond_ref=None, cond_alt=None,
           cond=None) -> dict:
    """Diferença pareada alt − ref (por semente)."""
    a = df[(df.policy == ref) & (df.condition == (cond_ref or cond))].set_index("seed")[metric]
    b = df[(df.policy == alt) & (df.condition == (cond_alt or cond))].set_index("seed")[metric]
    j = a.index.intersection(b.index)
    a, b = a.loc[j].astype(float), b.loc[j].astype(float)
    ok = np.isfinite(a.values) & np.isfinite(b.values)
    a, b = a.values[ok], b.values[ok]
    d = b - a
    lo, hi = boot_ci(d)
    if d.size < 2 or np.all(d == 0):
        p = 1.0
    else:
        p = float(wilcoxon(b, a, zero_method="wilcox", alternative="two-sided").pvalue)
    return dict(metric=metric, ref=ref, alt=alt, n=int(d.size), mean_ref=float(a.mean()) if a.size else np.nan,
                mean_alt=float(b.mean()) if b.size else np.nan, diff=float(d.mean()) if d.size else np.nan,
                ci_lo=lo, ci_hi=hi, rel_pct=float(100 * d.mean() / a.mean()) if a.size and a.mean() else np.nan,
                p=p, r_rb=rank_biserial(d), wins=int((d < 0).sum()), losses=int((d > 0).sum()))


def holm(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    m = p.size
    order = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, (m - k) * p[i])
        adj[i] = min(1.0, run)
    return adj


def describe(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    out = []
    for (exp, c, p), g in df[df.status == "ok"].groupby(["exp", "condition", "policy"]):
        for m in metrics:
            if m not in g:
                continue
            x = g[m].astype(float).values
            x = x[np.isfinite(x)]
            if not x.size:
                continue
            lo, hi = boot_ci(x)
            q1, q3 = np.percentile(x, [25, 75])
            out.append(dict(exp=exp, condition=c, policy=p, metric=m, n=x.size, mean=x.mean(),
                            sd=x.std(ddof=1) if x.size > 1 else 0, median=np.median(x), q1=q1, q3=q3,
                            ci_lo=lo, ci_hi=hi))
    return pd.DataFrame(out)


# ------------------------------------------------------------------ formatação LaTeX
def f(x, d=1):
    if x is None or not np.isfinite(x):
        return "---"
    s = f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.replace("-", "$-$") if s.startswith("-") else s


def fp(p):
    if not np.isfinite(p):
        return "---"
    return "$<$0,001" if p < 0.001 else f(p, 3)


_DIG = dict(zip("0123456789", ["Zero", "Um", "Dois", "Tres", "Quatro", "Cinco", "Seis", "Sete", "Oito", "Nove"]))


def mname(name: str) -> str:
    """Nomes de macro LaTeX não aceitam dígitos: N20 → NVinte etc."""
    for k, v in (("N500", "NQuinhentos"), ("N100", "NCem"), ("N20", "NVinte")):
        name = name.replace(k, v)
    return "".join(_DIG.get(ch, ch) for ch in name if ch.isalnum())


def macro(name: str, value: str) -> str:
    return f"\\newcommand{{\\{mname(name)}}}{{{value}}}\n"


# ------------------------------------------------------------------ experimentos
SECONDARY = ["visits_per_day", "km_per_m3", "overflow_events", "full_h_per_container_day",
             "mean_fill_at_collection", "pct_collections_below_50", "mean_wait_h",
             "vehicle_utilization", "recourse_trips", "unserved_planned", "dropped_mandatory",
             "solver_s_mean", "solver_s_max", "selected_per_day", "telemetry_availability",
             "pred_mae", "persist_mae", "pred_bias", "mass_balance_residual_l", "wall_s"]

COMP_E1 = [("A", "B"), ("A", "B-OR"), ("A", "C"), ("A", "D"), ("C", "D"), ("B-OR", "C"), ("B", "B-OR")]


def analyse_e1(df, comps):
    for metric in PRIMARY + ["mean_fill_at_collection", "pct_collections_below_50"]:
        fam = []
        for cond in sorted(df.condition.unique(), key=lambda c: int(c[1:])):
            for ref, alt in COMP_E1:
                r = paired(df, metric, ref, alt, cond=cond)
                fam.append(dict(exp="E1", family=f"E1/{metric}", condition=cond, **r))
        adj = holm([x["p"] for x in fam])
        for x, a in zip(fam, adj):
            x["p_holm"] = a
        comps.extend(fam)


def frontier(df):
    """E2: pontos (transbordamento, km) por política e nível; km ao nível de 1% e 2%."""
    pts = []
    df = df[df.status == "ok"].copy()
    df["level"] = df.condition.str.split("=").str[1].astype(float)
    for (pol, lev), g in df.groupby(["policy", "level"]):
        ov, km = g.overflow_pct.values, g.km_per_day.values
        pts.append(dict(policy=pol, level=lev, ov_mean=ov.mean(), km_mean=km.mean(),
                        ov_lo=boot_ci(ov)[0], ov_hi=boot_ci(ov)[1], km_lo=boot_ci(km)[0],
                        km_hi=boot_ci(km)[1], n=len(g), fill_mean=g.mean_fill_at_collection.mean(),
                        below50=g.pct_collections_below_50.mean()))
    at = []
    for target in (1.0, 2.0):
        for (pol, seed), g in df.groupby(["policy", "seed"]):
            g = g.sort_values("overflow_pct")
            x, y = g.overflow_pct.values, g.km_per_day.values
            val = float(np.interp(target, x, y)) if x.min() <= target <= x.max() else np.nan
            at.append(dict(policy=pol, seed=seed, target=target, km_at=val))
    return pd.DataFrame(pts), pd.DataFrame(at)


def analyse_e2(at, comps):
    for target in (1.0, 2.0):
        fam = []
        sub = at[at.target == target].rename(columns={"km_at": "km_at_target"})
        sub = sub.assign(condition=f"ov={target}")
        for ref, alt in [("A", "B-OR"), ("A", "C"), ("A", "D"), ("C", "D")]:
            r = paired(sub, "km_at_target", ref, alt, cond=f"ov={target}")
            fam.append(dict(exp="E2", family=f"E2/km@{target}%", condition=f"ov={target}", **r))
        adj = holm([x["p"] for x in fam])
        for x, a in zip(fam, adj):
            x["p_holm"] = a
        comps.extend(fam)


def analyse_e3(df, comps):
    """Uma família de Holm por métrica (protocolo): degradação vs. base e contra A."""
    conds = [c for c in df.condition.unique() if c != "base" and not c.endswith("sem_fallback")]
    for metric in PRIMARY:
        fam = []
        for pol in ["B-OR", "C", "D"]:
            for c in conds:
                r = paired(df, metric, pol, pol, cond_ref="base", cond_alt=c)
                fam.append(dict(exp="E3", family=f"E3/{metric}", kind="degradacao", condition=c, **r))
            for c in ("falha_perm_30%", "interrupcao_48h"):
                r = paired(df, metric, pol, pol, cond_ref=c, cond_alt=c + "_sem_fallback")
                fam.append(dict(exp="E3", family=f"E3/{metric}", kind="degradacao",
                                condition=c + "_sem_fallback", **r))
        for c in ["base"] + conds:
            for pol in ["B-OR", "C", "D"]:
                r = paired(df, metric, "A", pol, cond=c)
                fam.append(dict(exp="E3", family=f"E3/{metric}", kind="vsA", condition=c, **r))
        adj = holm([x["p"] for x in fam])
        for x, a in zip(fam, adj):
            x["p_holm"] = a
        comps.extend(fam)


def analyse_e4(df, comps):
    for metric in PRIMARY:
        fam = []
        for c in df.condition.unique():
            for ref, alt in [("A", "B-OR"), ("A", "C"), ("A", "D"), ("C", "D")]:
                r = paired(df, metric, ref, alt, cond=c)
                fam.append(dict(exp="E4", family=f"E4/{metric}", condition=c, **r))
        adj = holm([x["p"] for x in fam])
        for x, a in zip(fam, adj):
            x["p_holm"] = a
        comps.extend(fam)


def analyse_e5(df, comps):
    for metric in PRIMARY + ["solver_s_mean"]:
        fam = []
        for pol in ["A", "C", "D"]:
            r = paired(df, metric, pol, pol, cond_ref="greedy_descent", cond_alt="gls")
            fam.append(dict(exp="E5", family=f"E5/{metric}", condition=pol, **r))
        adj = holm([x["p"] for x in fam])
        for x, a in zip(fam, adj):
            x["p_holm"] = a
        comps.extend(fam)


# ------------------------------------------------------------------ tabelas
def tab_e1(desc: pd.DataFrame) -> str:
    d = desc[desc.exp == "E1"]
    rows = []
    for cond in ["N20", "N100", "N500"]:
        for pol in ORDER:
            g = d[(d.condition == cond) & (d.policy == pol)].set_index("metric")
            if g.empty:
                continue
            def cell(m, k=1, scale=1.0):
                if m not in g.index:
                    return "---"
                return f"{f(scale * g.loc[m, 'mean'], k)} [{f(scale * g.loc[m, 'ci_lo'], k)}; {f(scale * g.loc[m, 'ci_hi'], k)}]"
            rows.append(f"{cond[1:] if pol == 'A' else ''} & \\pol{pol.replace('-', '')}{{}} & {cell('km_per_day')} & "
                        f"{cell('overflow_pct', 2)} & {f(100 * g.loc['mean_fill_at_collection', 'mean'], 0)} & "
                        f"{f(g.loc['pct_collections_below_50', 'mean'], 1)} & {f(g.loc['visits_per_day', 'mean'], 1)} & "
                        f"{f(g.loc['mean_wait_h', 'mean'], 1)} \\\\")
        rows.append("\\midrule")
    rows = rows[:-1]
    return ("\\begin{tabular}{@{}clcccccc@{}}\n\\toprule\n"
            "$N$ & Pol. & km/dia [IC 95\\%] & Transb. \\% [IC 95\\%] & Ocup. coleta (\\%) & Coletas $<$50\\% (\\%) & Visitas/dia & Espera (h) \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_comp(comps: pd.DataFrame, family_prefix: str, conds=None, pairs=None, cond_label=None) -> str:
    c = comps[comps.family.str.startswith(family_prefix)]
    if conds:
        c = c[c.condition.isin(conds)]
    if pairs:
        c = c[[(r, a) in pairs for r, a in zip(c.ref, c.alt)]]
    rows = []
    for _, r in c.iterrows():
        cl = cond_label(r.condition) if cond_label else r.condition
        rows.append(f"{cl} & \\pol{r.alt.replace('-', '')}{{}} $-$ \\pol{r.ref.replace('-', '')}{{}} & {f(r['diff'], 2)} & "
                    f"[{f(r.ci_lo, 2)}; {f(r.ci_hi, 2)}] & {f(r.rel_pct, 1)} & {f(r.r_rb, 2)} & {fp(r.p_holm)} \\\\")
    return "\n".join(rows)


def write_tex(desc, comps, e2pts, e2at, dfs):
    TEX.mkdir(parents=True, exist_ok=True)
    (TEX / "tab_e1.tex").write_text(tab_e1(desc))
    hdr = ("\\begin{tabular}{@{}llrcrrr@{}}\n\\toprule\nCOND & Comparação & Dif. média & IC 95\\% & Dif. (\\%) & $r_{rb}$ & $p$ (Holm) \\\\\n\\midrule\n")
    end = "\n\\bottomrule\n\\end{tabular}\n"
    lab = {"N20": "$N=20$", "N100": "$N=100$", "N500": "$N=500$"}
    for metric in PRIMARY:
        body = tab_comp(comps, f"E1/{metric}", cond_label=lambda c: lab[c])
        (TEX / f"tab_e1_comp_{metric}.tex").write_text(hdr.replace("COND", "Escala") + body + end)
    body = "\n".join(tab_comp(comps, f"E2/km@{t}%", cond_label=lambda c: f"{c.split('=')[1].replace('.', ',')}\\%")
                     for t in (1.0, 2.0))
    (TEX / "tab_e2_comp.tex").write_text(hdr.replace("COND", "Transb.") + body + end)
    for metric in PRIMARY:
        for fam, kind, fn in ((f"E3/{metric}", "vsA", f"tab_e3_vsA_{metric}"),
                              (f"E3/{metric}", "degradacao", f"tab_e3_deg_{metric}"),
                              (f"E4/{metric}", None, f"tab_e4_{metric}")):
            cc = comps if kind is None else comps[comps.get("kind", pd.Series(index=comps.index)).eq(kind)]
            body = tab_comp(cc, fam, cond_label=lambda c: c.replace("_", " ").replace("%", "\\%"))
            (TEX / f"{fn}.tex").write_text(hdr.replace("COND", "Condição") + body + end)
    # E3: tabela compacta de transbordamento e disponibilidade por condição
    if "E3" not in dfs:
        return
    d3 = desc[desc.exp == "E3"]
    conds = list(dict.fromkeys(dfs["E3"].condition))
    rows = []
    for c in conds:
        cells = []
        for pol in ["A", "B-OR", "C", "D"]:
            g = d3[(d3.condition == c) & (d3.policy == pol) & (d3.metric == "overflow_pct")]
            cells.append(f(g["mean"].iloc[0], 2) if len(g) else "---")
        av = d3[(d3.condition == c) & (d3.policy == "C") & (d3.metric == "telemetry_availability")]
        kmD = d3[(d3.condition == c) & (d3.policy == "D") & (d3.metric == "km_per_day")]
        rows.append(f"{c.replace('_', ' ').replace('%', '\\%')} & {f(100 * av['mean'].iloc[0], 1) if len(av) else '---'} & "
                    + " & ".join(cells) + f" & {f(kmD['mean'].iloc[0], 1) if len(kmD) else '---'} \\\\")
    (TEX / "tab_e3.tex").write_text(
        "\\begin{tabular}{@{}lrrrrrr@{}}\n\\toprule\n & Telemetria & \\multicolumn{4}{c}{Transbordamento (\\% do volume)} & km/dia \\\\\n"
        "\\cmidrule(lr){3-6}\nCondição & disponível (\\%) & \\polA{} & \\polBOR{} & \\polC{} & \\polD{} & \\polD{} \\\\\n\\midrule\n"
        + "\n".join(rows) + end)


def write_macros(desc, comps, e2at, dfs, e6):
    m = ""
    total = sum(len(d) for d in dfs.values())
    errors = sum(int((d.status != "ok").sum()) for d in dfs.values())
    m += macro("NExecTotal", f(total, 0)) + macro("NExecErros", str(errors))
    for e in ("E1", "E2", "E3", "E4", "E5"):
        m += macro(f"NExec{e}", f(len(dfs[e]), 0) if e in dfs else "---")
    allok = pd.concat([d[d.status == "ok"] for d in dfs.values()])
    m += macro("BalancoMaxResidual", f"{np.abs(allok.mass_balance_residual_l).max():.1e}".replace(".", ","))
    m += macro("CPUhoras", f(allok.wall_s.sum() / 3600, 1))

    def dsc(exp, cond, pol, metric, k=1, scale=1.0):
        g = desc[(desc.exp == exp) & (desc.condition == cond) & (desc.policy == pol) & (desc.metric == metric)]
        return f(scale * g["mean"].iloc[0], k) if len(g) else "---"

    for cond in ["N20", "N100", "N500"]:
        for pol in ORDER:
            tag = cond + pol.replace("-", "")
            m += macro(f"Km{tag}", dsc("E1", cond, pol, "km_per_day"))
            m += macro(f"Ov{tag}", dsc("E1", cond, pol, "overflow_pct", 2))
            m += macro(f"Fill{tag}", dsc("E1", cond, pol, "mean_fill_at_collection", 0, 100))
            m += macro(f"Below{tag}", dsc("E1", cond, pol, "pct_collections_below_50", 1))
            m += macro(f"Veh{tag}", dsc("E1", cond, pol, "n_vehicles", 0))
            m += macro(f"Solver{tag}", dsc("E1", cond, pol, "solver_s_mean", 2))
            m += macro(f"Pred{tag}", dsc("E1", cond, pol, "pred_mae", 3))
            m += macro(f"Persist{tag}", dsc("E1", cond, pol, "persist_mae", 3))
            m += macro(f"Avail{tag}", dsc("E1", cond, pol, "telemetry_availability", 1, 100))
    c = comps
    for _, r in c[c.exp == "E1"].iterrows():
        tag = r.condition + r.alt.replace("-", "") + "vs" + r.ref.replace("-", "") + \
              {"km_per_day": "Km", "overflow_pct": "Ov", "mean_fill_at_collection": "Fill",
               "pct_collections_below_50": "Below"}[r.metric]
        m += macro(f"Rel{tag}", f(r.rel_pct, 1)) + macro(f"Dif{tag}", f(r["diff"], 2))
        m += macro(f"P{tag}", fp(r.p_holm)) + macro(f"Lo{tag}", f(r.ci_lo, 2)) + macro(f"Hi{tag}", f(r.ci_hi, 2))
    for _, r in c[c.exp == "E2"].iterrows():
        t = "Um" if r.condition.endswith("1.0") else "Dois"
        tag = f"Front{t}{r.alt.replace('-', '')}vs{r.ref.replace('-', '')}"
        m += macro(f"Rel{tag}", f(r.rel_pct, 1)) + macro(f"N{tag}", str(r.n)) + macro(f"P{tag}", fp(r.p_holm))
        m += macro(f"Dif{tag}", f(r["diff"], 1))
    for t in (1.0, 2.0):
        for pol in ["A", "B-OR", "C", "D"]:
            x = e2at[(e2at.target == t) & (e2at.policy == pol)].km_at
            tt = "Um" if t == 1.0 else "Dois"
            m += macro(f"KmAt{tt}{pol.replace('-', '')}", f(np.nanmean(x), 1) if x.notna().any() else "---")
            m += macro(f"KmAtN{tt}{pol.replace('-', '')}", str(int(x.notna().sum())))
    for exp, fam, kind in (("E3", "E3vsA", "vsA"), ("E3", "E3degradacao", "degradacao"), ("E4", "E4", None)):
        sel = c[c.exp == exp]
        if kind is not None:
            sel = sel[sel["kind"] == kind]
        for _, r in sel.iterrows():
            cname = "".join(ch for ch in r.condition.title() if ch.isalnum())
            tag = f"{fam.replace('-', '')}{cname}{r.alt.replace('-', '')}vs{r.ref.replace('-', '')}{'Km' if r.metric == 'km_per_day' else 'Ov'}"
            tag = tag.replace("0", "Z").replace("1", "U").replace("2", "D").replace("3", "T").replace("4", "Q") \
                     .replace("5", "C").replace("6", "S").replace("7", "Se").replace("8", "O").replace("9", "N")
            m += macro(f"Rel{tag}", f(r.rel_pct, 1)) + macro(f"Dif{tag}", f(r["diff"], 2)) + macro(f"P{tag}", fp(r.p_holm))
    for _, r in c[c.exp == "E5"].iterrows():
        tag = f"Sol{r.condition}{ {'km_per_day': 'Km', 'overflow_pct': 'Ov', 'solver_s_mean': 'T'}[r.metric]}"
        m += macro(f"Rel{tag}", f(r.rel_pct, 1)) + macro(f"Dif{tag}", f(r["diff"], 2)) + macro(f"P{tag}", fp(r.p_holm))
        m += macro(f"Ref{tag}", f(r.mean_ref, 2)) + macro(f"Alt{tag}", f(r.mean_alt, 2))
    if e6:
        for i, t in enumerate(e6["T1"]):
            pass
        for q in (0, 1):
            rows = [t for t in e6["T1"] if t["qos"] == q]
            qq = "Zero" if q == 0 else "Um"
            m += macro(f"MqttDeliv{qq}", f(min(t["delivered_pct"] for t in rows), 2))
            m += macro(f"MqttLatMed{qq}", f(np.mean([t["lat_ms_median"] for t in rows]), 1))
            m += macro(f"MqttLatPNN{qq}", f(np.mean([t["lat_ms_p99"] for t in rows]), 1))
            m += macro(f"MqttRate{qq}", f(np.mean([t["rate_msgs_s"] for t in rows]), 0))
            m += macro(f"MqttPub{qq}", f(rows[0]["published"], 0))
        for t in e6["T3"]:
            qq = "Zero" if t["qos"] == 0 else "Um"
            m += macro(f"RestartLost{qq}", f(t["lost"], 0)) + macro(f"RestartPub{qq}", f(t["published_calls"], 0))
            m += macro(f"RestartDeliv{qq}", f(t["delivered_pct"], 2)) + macro(f"RestartDup{qq}", f(t["duplicates"], 0))
            m += macro(f"RestartRecon{qq}", str(t["devices_reconnected"])) + macro(f"RestartDur{qq}", f(t["broker_restart_s"], 1))
        m += macro("LwtDetected", str(e6["T4"]["offline_detected"])) + macro("LwtCrashed", str(e6["T4"]["crashed"]))
        m += macro("LwtTime", f(e6["T4"]["detection_s_max"], 2))
        m += macro("LwtRetained", str(e6["T4"]["retained_offline_seen_by_new_subscriber"]))
        m += macro("MalSent", str(e6["T5"]["sent"])) + macro("MalRejected", str(e6["T5"]["rejected"]))
        m += macro("EquivOk", "idênticas" if e6["T2"]["identical"] else "diferentes")
        m += macro("BrokerVersion", e6["broker"].replace("_", "\\_"))
        m += macro("PahoVersion", e6["paho"])
    return m


def main():
    RES.mkdir(parents=True, exist_ok=True)
    dfs = {e: load(e) for e in ("E1", "E2", "E3", "E4", "E5")}
    dfs = {k: v for k, v in dfs.items() if len(v)}
    for k, v in dfs.items():
        print(k, len(v), "execuções;", int((v.status != "ok").sum()), "falhas")
    metrics = PRIMARY + SECONDARY + ["n_vehicles"]
    desc = describe(pd.concat(dfs.values()), metrics)
    desc.to_csv(RES / "descritivas.csv", index=False)
    comps: list[dict] = []
    if "E1" in dfs:
        analyse_e1(dfs["E1"][dfs["E1"].status == "ok"], comps)
    e2pts = e2at = pd.DataFrame()
    if "E2" in dfs:
        e2pts, e2at = frontier(dfs["E2"])
        e2pts.to_csv(RES / "e2_fronteira.csv", index=False)
        e2at.to_csv(RES / "e2_km_ao_nivel.csv", index=False)
        analyse_e2(e2at, comps)
    if "E3" in dfs:
        analyse_e3(dfs["E3"][dfs["E3"].status == "ok"], comps)
    if "E4" in dfs:
        analyse_e4(dfs["E4"][dfs["E4"].status == "ok"], comps)
    if "E5" in dfs:
        analyse_e5(dfs["E5"][dfs["E5"].status == "ok"], comps)
    comps = pd.DataFrame(comps)
    comps.to_csv(RES / "comparacoes.csv", index=False)
    e6 = json.loads((RES / "E6_mqtt.json").read_text()) if (RES / "E6_mqtt.json").exists() else None
    write_tex(desc, comps, e2pts, e2at, dfs)
    import subprocess
    ntests = subprocess.run(["python", "-m", "pytest", "--collect-only", "-q"], cwd=ROOT,
                            capture_output=True, text=True).stdout
    ntests = [l for l in ntests.splitlines() if "tests collected" in l or "test collected" in l]
    m = write_macros(desc, comps, e2at, dfs, e6)
    # variantes com ponto decimal para o abstract em inglês
    import re as _re
    en = ""
    for name in ("NExecTotal", "RelNCemCvsAKm", "OvNCemC", "OvNCemA", "RelNCemDvsAKm", "OvNCemD", "RelFrontUmDvsA"):
        mm = _re.search(r"\\newcommand\{\\" + name + r"\}\{([^}]*)\}", m)
        if mm:
            v = mm.group(1).replace(".", "").replace(",", ".") if name != "NExecTotal" else mm.group(1).replace(".", ",")
            en += macro(name + "En", v)
    m += en
    m += macro("NTestes", ntests[0].split()[0] if ntests else "---")
    (TEX / "macros.tex").write_text("% gerado por experiments/analysis.py — não editar\n" + m)
    # painel
    dash = {"E1_seeds": 30, "E2_seeds": 20, "E1": [], "E2": e2pts.to_dict("records") if len(e2pts) else []}
    d1 = desc[desc.exp == "E1"]
    for cond in ["N20", "N100", "N500"]:
        for pol in ORDER:
            g = d1[(d1.condition == cond) & (d1.policy == pol)].set_index("metric")
            if g.empty:
                continue
            dash["E1"].append(dict(N=int(cond[1:]), policy=pol, km_mean=g.loc["km_per_day", "mean"],
                                   km_lo=g.loc["km_per_day", "ci_lo"], km_hi=g.loc["km_per_day", "ci_hi"],
                                   ov_mean=g.loc["overflow_pct", "mean"], ov_lo=g.loc["overflow_pct", "ci_lo"],
                                   ov_hi=g.loc["overflow_pct", "ci_hi"],
                                   fill_mean=g.loc["mean_fill_at_collection", "mean"],
                                   below50=g.loc["pct_collections_below_50", "mean"],
                                   visits=g.loc["visits_per_day", "mean"]))
    (RES / "dashboard.json").write_text(json.dumps(dash, default=float))
    print("ok:", len(comps), "comparações")


if __name__ == "__main__":
    main()
