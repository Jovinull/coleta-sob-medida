"""Animações (GIF e MP4) geradas a partir de execuções gravadas.

    python -m experiments.animations [A B C D E]

A  enchimento de contêineres ao longo do tempo (replay.json, política A e D)
B  telemetria MQTT recebida pela plataforma (live/plataforma.db de uma execução
   real do modo live, via broker Mosquitto)
C  veículos coletando na malha de Aracaju (replay.json, política D)
D  comparação sincronizada A × D (replay.json)
E  interrupção regional de comunicação (trace_falha.npz, política C)

Saída: animations/*.gif e animations/*.mp4. Nenhum quadro é ilustrativo: todos
os valores vêm dos arquivos indicados.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "experiments/results"
OUT = ROOT / "animations"
INK, MUTED, ROAD = "#0b0b0b", "#52514e", "#d3d6da"
VC = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def fill_color(f):
    f = np.asarray(f)
    c = np.empty((f.size, 4))
    c[:] = matplotlib.colors.to_rgba("#2e9e5b")
    c[f >= 0.5] = matplotlib.colors.to_rgba("#e0b020")
    c[f >= 0.75] = matplotlib.colors.to_rgba("#ec7a1c")
    c[f >= 0.95] = matplotlib.colors.to_rgba("#d23b3b")
    c[f < 0] = matplotlib.colors.to_rgba("#ffffff")
    return c


def base_map(ax, bbox=None):
    z = json.loads((ROOT / "data/aracaju/roads.json").read_text())
    s = np.array(z["segments"]).reshape(-1, 4)
    ax.add_collection(LineCollection(np.stack([s[:, [1, 0]], s[:, [3, 2]]], 1), colors=ROAD, linewidths=0.25))
    b = z["boundary"]
    rings = [r for p in b["coordinates"] for r in p] if b["type"] == "MultiPolygon" else b["coordinates"]
    for r in rings:
        r = np.array(r)
        ax.plot(r[:, 0], r[:, 1], color=MUTED, lw=0.5, ls=(0, (3, 2)))
    ax.set_aspect(1 / np.cos(np.radians(-10.95)))
    ax.set_xticks([]), ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    if bbox:
        ax.set_xlim(bbox[0], bbox[1]), ax.set_ylim(bbox[2], bbox[3])


def hhmm(t):
    d, h = int(t // 86400), (t % 86400) / 3600
    return f"dia {d + 1} · {int(h):02d}:{int(round((h % 1) * 60)):02d}"


def save(anim, name, fps):
    OUT.mkdir(exist_ok=True)
    anim.save(OUT / f"{name}.gif", writer=PillowWriter(fps=fps), dpi=80)
    anim.save(OUT / f"{name}.mp4", writer=FFMpegWriter(fps=fps, bitrate=1600), dpi=110)
    print("animação", name)


# --------------------------------------------------------------------------
def anim_A():
    R = json.loads((RES / "replay.json").read_text())
    t = np.array(R["frames_t"])
    A = np.array(R["runs"][0]["fill"])
    idx = np.argsort(A.mean(0))[[-1, -5, -20, -40, -60, 10]]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    lines = [ax.plot([], [], lw=1.5, label=R["containers"][i]["id"])[0] for i in idx]
    ax.axhline(75, color=MUTED, ls=":", lw=0.8)
    ax.text(t[0] / 86400 + 0.05, 77, "limiar 75%", fontsize=7, color=MUTED)
    ax.set_xlim(t[0] / 86400, t[-1] / 86400), ax.set_ylim(0, 105)
    ax.set_xlabel("dia"), ax.set_ylabel("ocupação verdadeira (%)")
    ax.legend(ncol=3, fontsize=7, frameon=False, loc="upper left")
    ttl = ax.set_title("")
    fig.tight_layout()

    def upd(k):
        for ln, i in zip(lines, idx):
            ln.set_data(t[:k + 1] / 86400, 100 * A[:k + 1, i])
        ttl.set_text(f"Enchimento de 6 contêineres — política A (periódica) — {hhmm(t[k])}")
        return lines

    save(FuncAnimation(fig, upd, frames=range(0, len(t), 2), blit=False), "A_enchimento", 12)
    plt.close(fig)


def anim_B():
    db = ROOT / "live/plataforma.db"
    st = json.loads((ROOT / "live/state.json").read_text())
    pos = {c["id"]: (c["lon"], c["lat"]) for c in st["contentores"]}
    con = sqlite3.connect(db)
    tel = con.execute("SELECT dev, ts, recebido_em, ocupacao, valida, resultado FROM telemetria ORDER BY ts").fetchall()
    ev = con.execute("SELECT dev, ts, tipo FROM eventos ORDER BY ts").fetchall()
    ts = np.array([r[1] for r in tel])
    t0, t1 = ts.min(), ts.max()
    frames = np.arange(t0, t1, 3600)
    xs = np.array([p[0] for p in pos.values()])
    ys = np.array([p[1] for p in pos.values()])
    bbox = (xs.min() - 0.01, xs.max() + 0.01, ys.min() - 0.01, ys.max() + 0.01)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1]))
    base_map(ax, bbox)
    ids = list(pos)
    sc = ax.scatter(xs, ys, s=14, c="#9aa4ae", zorder=3)
    pulse = ax.scatter([], [], s=60, facecolors="none", edgecolors="#2a78d6", lw=1.2, zorder=4)
    alert = ax.scatter([], [], s=90, marker="*", c="#d23b3b", zorder=5)
    last = {}
    ax2.set_xlim(t0 / 86400 + 1, t1 / 86400 + 1)
    ax2.set_xlabel("dia (tempo simulado)"), ax2.set_ylabel("mensagens recebidas (acumulado)")
    cum, = ax2.plot([], [], color="#2a78d6", lw=1.6, label="telemetria aplicada")
    inv, = ax2.plot([], [], color="#d23b3b", lw=1.2, label="leitura inválida")
    ax2.set_ylim(0, len(tel) * 1.05)
    ax2.legend(frameon=False, fontsize=8, loc="upper left")
    ttl = fig.suptitle("")
    txt = ax2.text(0.02, 0.62, "", transform=ax2.transAxes, fontsize=7.5, family="monospace", va="top")
    tsd = ts / 86400 + 1
    applied = np.cumsum([r[5] == "applied" for r in tel])
    invalid = np.cumsum([r[5] == "invalid" for r in tel])
    fig.tight_layout(rect=(0, 0, 1, 0.9))

    def upd(t):
        k = np.searchsorted(ts, t + 3600)
        j = np.searchsorted(ts, t)
        for r in tel[:k]:
            if r[4]:
                last[r[0]] = r[3]
        sc.set_color(fill_color([last.get(i, -100) / 100 for i in ids]))
        sc.set_edgecolor("#52514e")
        recent = [pos[r[0]] for r in tel[j:k]]
        pulse.set_offsets(np.array(recent) if recent else np.empty((0, 2)))
        al = [pos[e[0]] for e in ev if t <= e[1] < t + 3600 and e[2] == "limiar_excedido"]
        alert.set_offsets(np.array(al) if al else np.empty((0, 2)))
        cum.set_data(tsd[:k], applied[:k])
        inv.set_data(tsd[:k], invalid[:k])
        log = [f"{e[0]} {e[2].replace('_', ' ')} {hhmm(e[1])}" for e in ev if e[1] < t + 3600][-6:]
        txt.set_text("Últimos eventos MQTT:\n" + "\n".join(log))
        ttl.set_text(f"Telemetria via broker Mosquitto (MQTT 3.1.1) — {hhmm(t)} — {k} mensagens recebidas\n"
                     f"círculos azuis: mensagens recebidas nesta hora · estrela: evento de limiar")
        return sc, pulse, alert, cum, inv, txt

    save(FuncAnimation(fig, upd, frames=frames, blit=False), "B_telemetria_mqtt", 8)
    plt.close(fig)


def _replay_map(ax, R, run, bbox):
    base_map(ax, bbox)
    lat = np.array([c["lat"] for c in R["containers"]])
    lon = np.array([c["lon"] for c in R["containers"]])
    sc = ax.scatter(lon, lat, s=16, c="#2e9e5b", edgecolors="#52514e", linewidths=0.3, zorder=3)
    ax.scatter(*R["depot"][::-1], marker="D", s=40, c=INK, zorder=5)
    paths = [ax.plot([], [], color=VC[k], lw=1.3, alpha=0.75, zorder=2)[0] for k in range(4)]
    trucks = ax.scatter([], [], marker="s", s=45, c="#3a5bd9", edgecolors="white", zorder=6)
    return sc, paths, trucks


def _replay_update(R, run, k, sc, paths, trucks):
    t = R["frames_t"][k]
    day = str(int(t // 86400))
    sc.set_facecolor(fill_color(run["fill"][k]))
    pp = run["paths"].get(day, [])
    for j, ln in enumerate(paths):
        if j < len(pp):
            p = np.array(pp[j])
            ln.set_data(p[:, 1], p[:, 0])
        else:
            ln.set_data([], [])
    tr = run["trucks"][k]
    trucks.set_offsets(np.array([[b, a] for a, b, _ in tr]) if tr else np.empty((0, 2)))
    trucks.set_color([VC[v % 4] for _, _, v in tr] if tr else "#3a5bd9")


def _bbox(R):
    lat = np.array([c["lat"] for c in R["containers"]] + [R["depot"][0]])
    lon = np.array([c["lon"] for c in R["containers"]] + [R["depot"][1]])
    return lon.min() - 0.008, lon.max() + 0.008, lat.min() - 0.008, lat.max() + 0.008


def anim_C():
    R = json.loads((RES / "replay.json").read_text())
    run = R["runs"][1]
    fig, ax = plt.subplots(figsize=(5, 7))
    art = _replay_map(ax, R, run, _bbox(R))
    ttl = ax.set_title("")
    fig.tight_layout()

    def upd(k):
        _replay_update(R, run, k, *art)
        q = run["kpi"][k]
        ttl.set_text(f"Política D (preditiva) — {hhmm(R['frames_t'][k])}\n"
                     f"{q[0]:.0f} km · {q[1]} coletas · {q[2]:.1f} m³ transbordados")
        return art

    save(FuncAnimation(fig, upd, frames=range(len(R["frames_t"]))), "C_coleta_veiculos", 8)
    plt.close(fig)


def anim_D():
    R = json.loads((RES / "replay.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(9, 6.6))
    bb = _bbox(R)
    arts = [_replay_map(ax, R, run, bb) for ax, run in zip(axs, R["runs"])]
    ttls = [ax.set_title("") for ax in axs]
    sup = fig.suptitle("")
    fig.text(0.5, 0.01, f"Mesma semente ({R['seed']}) e mesma demanda nas duas políticas; cores: ocupação verdadeira "
             "(verde < 50%, amarelo 50–75%, laranja 75–95%, vermelho ≥ 95%). Posições hipotéticas; malha © OpenStreetMap.",
             ha="center", fontsize=7, color=MUTED, wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 0.9))

    def upd(k):
        for run, art, tt in zip(R["runs"], arts, ttls):
            _replay_update(R, run, k, *art)
            q = run["kpi"][k]
            tt.set_text(f"{run['policy']} — {run['label']}\n{q[0]:.0f} km · {q[1]} coletas · "
                        f"{q[2]:.1f} m³ transb. · {q[3]} cheios")
        sup.set_text(f"Comparação sincronizada — {hhmm(R['frames_t'][k])}")
        return arts

    save(FuncAnimation(fig, upd, frames=range(len(R["frames_t"]))), "D_comparacao_A_D", 8)
    plt.close(fig)


def anim_E():
    z = np.load(RES / "trace_falha.npz")
    t, fill, est, stale, aff, ll = z["t"], z["fill"], z["est"], z["stale"], z["affected"], z["latlon"]
    o0, o1 = z["outage"]
    keep = np.nonzero((t >= o0 - 2 * 86400) & (t <= o1 + 2 * 86400))[0]
    lat, lon = ll[1:, 0], ll[1:, 1]
    bb = (lon.min() - 0.008, lon.max() + 0.008, lat.min() - 0.008, lat.max() + 0.008)
    fig, axs = plt.subplots(1, 2, figsize=(9, 6.2))
    scs = []
    for ax, title in zip(axs, ("estado verdadeiro (simulador)", "estado visto pela plataforma")):
        base_map(ax, bb)
        scs.append(ax.scatter(lon, lat, s=18, edgecolors="#52514e", linewidths=0.4, zorder=3))
        ax.set_title(title)
    ring = axs[1].scatter(lon[aff], lat[aff], s=60, facecolors="none", edgecolors="#d23b3b", lw=0.0, zorder=4)
    sup = fig.suptitle("")
    fig.text(0.5, 0.01, "Política C; interrupção regional de 48 h em 50% dos dispositivos (dias 10–11). "
             "Círculos brancos: sem dado há mais de 24 h. Contorno vermelho: dispositivos na área sem conectividade.",
             ha="center", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))

    def upd(k):
        scs[0].set_facecolor(fill_color(fill[k]))
        e = est[k].copy()
        scs[1].set_facecolor(fill_color(np.where(stale[k], -1, e)))
        on = o0 <= t[k] < o1
        ring.set_linewidth(1.0 if on else 0.0)
        q = z["kpi"][k]
        sup.set_text(f"{hhmm(t[k])} — {'INTERRUPÇÃO ATIVA' if on else 'rede normal'} — "
                     f"{int(stale[k].sum())} contêineres sem dado recente — {q[2]:.1f} m³ transbordados (acum.)")
        return scs

    save(FuncAnimation(fig, upd, frames=keep[::1]), "E_falha_comunicacao", 8)
    plt.close(fig)


if __name__ == "__main__":
    for w in sys.argv[1:] or ["A", "B", "C", "D", "E"]:
        globals()[f"anim_{w}"]()
