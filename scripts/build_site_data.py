"""Extrai dos resultados derivados os números exibidos no site (site/data/resultados.json).

Não calcula nada novo: só reorganiza experiments/results/*.csv|json, que já
contêm médias, IC 95% e testes produzidos por experiments/analysis.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "experiments" / "results"
RAW = ROOT / "experiments" / "raw"
OUT = ROOT / "site" / "data" / "resultados.json"

import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
from experiments.labels import plain  # noqa: E402


def r(x, k=3):
    return None if pd.isna(x) else round(float(x), k)


def main() -> None:
    d = pd.read_csv(RES / "descritivas.csv")
    c = pd.read_csv(RES / "comparacoes.csv")
    out: dict = {}

    def stat(exp, cond, pol, metric):
        row = d[(d.exp == exp) & (d.condition == cond) & (d.policy == pol) & (d.metric == metric)]
        if row.empty:
            return None
        row = row.iloc[0]
        return {"m": r(row["mean"]), "lo": r(row.ci_lo), "hi": r(row.ci_hi), "n": int(row.n)}

    # E1 -----------------------------------------------------------------
    e1 = []
    for cond in ["N20", "N100", "N500"]:
        for p in ["A", "B", "B-OR", "C", "D"]:
            e1.append({
                "N": int(cond[1:]), "policy": p,
                "km": stat("E1", cond, p, "km_per_day"),
                "ov": stat("E1", cond, p, "overflow_pct"),
                "fill": stat("E1", cond, p, "mean_fill_at_collection"),
                "below50": stat("E1", cond, p, "pct_collections_below_50"),
            })
    out["E1"] = e1
    comp = c[(c.exp == "E1")]
    out["E1_comp"] = [
        {"N": int(x.condition[1:]), "metric": x.metric, "ref": x.ref, "alt": x.alt,
         "diff": r(x.diff), "lo": r(x.ci_lo), "hi": r(x.ci_hi), "rel": r(x.rel_pct, 2),
         "p_holm": float(f"{x.p_holm:.3g}")}
        for x in comp.itertuples() if x.metric in ("km_per_day", "overflow_pct")
    ]

    # E2 -----------------------------------------------------------------
    f = pd.read_csv(RES / "e2_fronteira.csv")
    out["E2"] = [
        {"policy": x.policy, "level": r(x.level, 2), "ov": r(x.ov_mean), "km": r(x.km_mean, 2),
         "ov_lo": r(x.ov_lo), "ov_hi": r(x.ov_hi), "km_lo": r(x.km_lo, 2), "km_hi": r(x.km_hi, 2)}
        for x in f.itertuples()
    ]
    e2c = c[c.exp == "E2"]
    out["E2_comp"] = [
        {"family": x.family, "ref": x.ref, "alt": x.alt, "rel": r(x.rel_pct, 2),
         "p_holm": float(f"{x.p_holm:.3g}")} for x in e2c.itertuples()
    ]

    # E3 / E4: diferenças em relação à condição-base (mesma política) -----
    for exp in ("E3", "E4"):
        rows = []
        conds = [k for k in d[d.exp == exp].condition.unique() if k != "base"]
        for cond in conds:
            for p in ["A", "B-OR", "C", "D"]:
                ov = stat(exp, cond, p, "overflow_pct")
                km = stat(exp, cond, p, "km_per_day")
                if ov is None:
                    continue
                base_ov = stat(exp, "base", p, "overflow_pct")
                base_km = stat(exp, "base", p, "km_per_day")
                g = c[(c.exp == exp) & (c.condition == cond) & (c.ref == p) & (c.alt == p)
                      & (c.metric == "overflow_pct")]
                gk = c[(c.exp == exp) & (c.condition == cond) & (c.ref == p) & (c.alt == p)
                       & (c.metric == "km_per_day")]
                rows.append({
                    "cond": cond, "label": plain(cond), "policy": p, "ov": ov, "km": km,
                    "d_ov": r(ov["m"] - base_ov["m"]), "d_km_pct": r(100 * (km["m"] / base_km["m"] - 1), 2),
                    "d_ov_lo": r(g.ci_lo.iloc[0]) if len(g) else None,
                    "d_ov_hi": r(g.ci_hi.iloc[0]) if len(g) else None,
                    "p_holm": float(f"{g.p_holm.iloc[0]:.3g}") if len(g) else None,
                    "p_holm_km": float(f"{gk.p_holm.iloc[0]:.3g}") if len(gk) else None,
                })
        out[exp] = rows
        out[exp + "_base"] = {p: {"ov": stat(exp, "base", p, "overflow_pct"),
                                  "km": stat(exp, "base", p, "km_per_day")}
                              for p in ["A", "B-OR", "C", "D"] if stat(exp, "base", p, "km_per_day")}

    # E5 -----------------------------------------------------------------
    out["E5"] = [
        {"policy": p, "cond": k, "km": stat("E5", k, p, "km_per_day"),
         "ov": stat("E5", k, p, "overflow_pct"), "solver_s": stat("E5", k, p, "solver_s_mean")}
        for k in ("greedy_descent", "gls") for p in ("A", "C", "D")
    ]

    # E6 e verificação ----------------------------------------------------
    e6 = json.loads((RES / "E6_mqtt.json").read_text())
    t1 = pd.DataFrame(e6["T1"])
    out["E6"] = {
        "broker": e6["broker"].replace("mosquitto version", "Mosquitto").strip(),
        "paho": e6["paho"],
        "T1": [{"qos": int(q), "deliv_min": r(g.delivered_pct.min(), 2),
                "lat_med": r(g.lat_ms_median.mean(), 2), "lat_p99": r(g.lat_ms_p99.mean(), 2),
                "rate": r(g.rate_msgs_s.mean(), 0), "published": int(g.published.iloc[0]),
                "reps": int(len(g))} for q, g in t1.groupby("qos")],
        "T2": e6["T2"], "T3": e6["T3"], "T4": e6["T4"], "T5": e6["T5"],
    }
    rep = json.loads((RES / "reprodutibilidade.json").read_text())
    out["repro"] = {"n": rep["n"], "identical": rep["identical"]}

    runs, fails, resid = 0, 0, 0.0
    for e in ("E1", "E2", "E3", "E4", "E5"):
        for line in (RAW / f"{e}.jsonl").read_text().splitlines():
            if line.strip():
                runs += 1
                rec = json.loads(line)
                fails += int(rec.get("status", "ok") != "ok")
                resid = max(resid, abs((rec.get("metrics") or {}).get("mass_balance_residual_l") or 0.0))
    out["totais"] = {"execucoes": runs, "falhas": fails,
                     "residuo_max_l": float(f"{resid:.2g}")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1024:.1f} KiB, {runs} execuções, {fails} falhas")


if __name__ == "__main__":
    main()
