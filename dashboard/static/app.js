"use strict";
// Painel operacional — sem dependências externas.
const $ = (s, r = document) => r.querySelector(s);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = (x, d = 1) => (x === null || x === undefined || Number.isNaN(x)) ? "—"
  : Number(x).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const fillColor = f => f < 0 ? css("--s") : f < 0.5 ? css("--g") : f < 0.75 ? css("--y") : f < 0.95 ? css("--o") : css("--r");
const VCOL = ["#3a5bd9", "#9b3ad9", "#d93a8f", "#1b9fb0", "#7a5c2e", "#4b8b2b", "#c25e00", "#555"];

let ROADS = null;
async function getJSON(u) { const r = await fetch(u); if (!r.ok) throw new Error(await r.text()); return r.json(); }

// ------------------------------------------------------------------ mapa
class MapView {
  constructor(canvas) {
    this.c = canvas; this.ctx = canvas.getContext("2d");
    this.view = null; this.drag = null; this.bg = null;
    canvas.addEventListener("wheel", e => { e.preventDefault(); this.zoom(e.deltaY < 0 ? 1.25 : 0.8, e.offsetX, e.offsetY); }, { passive: false });
    canvas.addEventListener("mousedown", e => this.drag = [e.offsetX, e.offsetY]);
    window.addEventListener("mouseup", () => this.drag = null);
    canvas.addEventListener("mousemove", e => {
      if (!this.drag) return;
      this.view.ox += e.offsetX - this.drag[0]; this.view.oy += e.offsetY - this.drag[1];
      this.drag = [e.offsetX, e.offsetY]; this.bg = null; this.onchange && this.onchange();
    });
    new ResizeObserver(() => { this.resize(); this.onchange && this.onchange(); }).observe(canvas);
  }
  resize() {
    const r = this.c.getBoundingClientRect(), d = devicePixelRatio || 1;
    this.c.width = r.width * d; this.c.height = r.height * d; this.ctx.setTransform(d, 0, 0, d, 0, 0);
    this.w = r.width; this.h = r.height; this.bg = null;
  }
  fit(pts) {
    let a = Infinity, b = -Infinity, c = Infinity, d = -Infinity;
    for (const [la, lo] of pts) { a = Math.min(a, la); b = Math.max(b, la); c = Math.min(c, lo); d = Math.max(d, lo); }
    const kx = Math.cos((a + b) / 2 * Math.PI / 180);
    const s = 0.92 * Math.min(this.w / ((d - c) * kx || 1e-6), this.h / ((b - a) || 1e-6));
    this.view = { s, kx, lo0: (c + d) / 2, la0: (a + b) / 2, ox: this.w / 2, oy: this.h / 2 };
    this.bg = null;
  }
  zoom(f, x, y) { const v = this.view; v.ox = x - (x - v.ox) * f; v.oy = y - (y - v.oy) * f; v.s *= f; this.bg = null; this.onchange && this.onchange(); }
  P(la, lo) { const v = this.view; return [v.ox + (lo - v.lo0) * v.kx * v.s, v.oy - (la - v.la0) * v.s]; }
  drawBackground() {
    if (this.bg) { this.ctx.putImageData(this.bg, 0, 0); return; }
    const g = this.ctx; g.clearRect(0, 0, this.w, this.h);
    if (!ROADS) return;
    g.strokeStyle = css("--road"); g.lineWidth = 0.7; g.beginPath();
    const S = ROADS.segments;
    for (let i = 0; i < S.length; i += 4) { const [x1, y1] = this.P(S[i], S[i + 1]), [x2, y2] = this.P(S[i + 2], S[i + 3]); g.moveTo(x1, y1); g.lineTo(x2, y2); }
    g.stroke();
    const rings = ROADS.boundary.type === "MultiPolygon" ? ROADS.boundary.coordinates.flat() : ROADS.boundary.coordinates;
    g.strokeStyle = css("--muted"); g.setLineDash([4, 3]); g.lineWidth = 1; g.beginPath();
    for (const ring of rings) ring.forEach(([lo, la], k) => { const [x, y] = this.P(la, lo); k ? g.lineTo(x, y) : g.moveTo(x, y); });
    g.stroke(); g.setLineDash([]);
    const d = devicePixelRatio || 1; this.bg = g.getImageData(0, 0, this.w * d, this.h * d);
  }
  drawScene(st, mode, highlight) {
    if (!this.view) return;
    this.drawBackground();
    const g = this.ctx;
    (st.caminhos || []).forEach((poly, k) => {
      g.strokeStyle = VCOL[k % VCOL.length]; g.globalAlpha = 0.55; g.lineWidth = 2.2; g.beginPath();
      poly.forEach(([la, lo], i) => { const [x, y] = this.P(la, lo); i ? g.lineTo(x, y) : g.moveTo(x, y); });
      g.stroke(); g.globalAlpha = 1;
    });
    for (const c of st.contentores) {
      const [x, y] = this.P(c.lat, c.lon);
      const f = mode === "real" ? c.real : (c.desatualizado ? -1 : c.estimado);
      const r = c.id === highlight ? 7 : 4.5;
      g.beginPath(); g.arc(x, y, r, 0, 2 * Math.PI);
      if (f < 0) { g.strokeStyle = css("--s"); g.lineWidth = 2; g.stroke(); }
      else { g.fillStyle = fillColor(f); g.fill(); g.strokeStyle = "rgba(0,0,0,.35)"; g.lineWidth = 0.8; g.stroke(); }
      if (c.estado === "offline") { g.strokeStyle = css("--r"); g.lineWidth = 1.5; g.beginPath(); g.moveTo(x - 5, y - 5); g.lineTo(x + 5, y + 5); g.moveTo(x + 5, y - 5); g.lineTo(x - 5, y + 5); g.stroke(); }
    }
    if (st.deposito) { const [x, y] = this.P(...st.deposito); g.fillStyle = css("--ink"); g.save(); g.translate(x, y); g.rotate(Math.PI / 4); g.fillRect(-6, -6, 12, 12); g.restore(); }
    for (const v of st.veiculos || []) {
      if (v.done) continue;
      const [x, y] = this.P(v.lat, v.lon); g.fillStyle = VCOL[v.vid % VCOL.length];
      g.fillRect(x - 6, y - 6, 12, 12); g.strokeStyle = "#fff"; g.lineWidth = 1.5; g.strokeRect(x - 6, y - 6, 12, 12);
    }
  }
}

// ------------------------------------------------------------------ abas
document.querySelectorAll("nav button").forEach(b => b.onclick = () => {
  document.querySelectorAll("nav button").forEach(x => x.classList.toggle("active", x === b));
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.id === "tab-" + b.dataset.tab));
  if (b.dataset.tab === "replay") initReplay();
  if (b.dataset.tab === "results") initResults();
  window.dispatchEvent(new Event("resize"));
});

const kpi = (v, l) => `<div class="kpi"><b>${v}</b><span>${l}</span></div>`;
const hhmm = t => { const d = Math.floor(t / 86400), h = (t % 86400) / 3600; return `dia ${d + 1} · ${String(Math.floor(h)).padStart(2, "0")}:${String(Math.round((h % 1) * 60)).padStart(2, "0")}`; };

// ------------------------------------------------------------------ ao vivo
const live = { map: null, st: null, filter: "todos", sel: new URLSearchParams(location.search).get("sel"), mode: "estimado", fitted: false };
function liveFilter(c) {
  const f = live.mode === "real" ? c.real : c.estimado;
  switch (live.filter) {
    case "alerta": return c.alerta; case "cheio": return !c.desatualizado && f >= 0.75;
    case "desatualizado": return c.desatualizado; case "offline": return c.estado === "offline"; default: return true;
  }
}
function renderLive() {
  const st = live.st; if (!st) return;
  if (!live.fitted && live.map.w) { live.map.fit([...st.contentores.map(c => [c.lat, c.lon]), st.deposito]); live.fitted = true; }
  const shown = { ...st, contentores: st.contentores.filter(liveFilter) };
  live.map.drawScene(shown, live.mode, live.sel);
  $("#clock-live").textContent = `${hhmm(st.t)} · política ${st.politica}`;
  const k = st.kpi, on = st.contentores.filter(c => c.estado === "online").length;
  $("#kpis-live").innerHTML = kpi(fmt(k.km, 1), "km percorridos") + kpi(k.visitas, "coletas") +
    kpi(fmt(k.transbordo_m3, 2), "m³ transbordados") + kpi(`${on}/${st.contentores.length}`, "dispositivos online") +
    kpi(k.msgs_recebidas.toLocaleString("pt-BR"), "mensagens recebidas") + kpi(`${k.duplicadas} / ${k.rejeitadas}`, "duplicadas / rejeitadas");
  const rows = shown.contentores.slice().sort((a, b) => (b[live.mode] ?? 0) - (a[live.mode] ?? 0));
  $("#list-live").innerHTML = rows.map(c => {
    const f = live.mode === "real" ? c.real : (c.desatualizado ? -1 : c.estimado);
    return `<div class="row ${c.id === live.sel ? "sel" : ""}" data-id="${c.id}"><span>${c.id}</span>
      <div class="bar"><i style="width:${Math.max(0, Math.min(1, f)) * 100}%;background:${fillColor(f)}"></i></div>
      <span>${f < 0 ? "s/ dado" : fmt(100 * f, 0) + "%"}</span></div>`;
  }).join("");
  $("#list-live").querySelectorAll(".row").forEach(r => r.onclick = () => { live.sel = r.dataset.id; loadHistory(); renderLive(); });
}
async function loadHistory() {
  if (!live.sel) return;
  try {
    const h = await getJSON(`/api/history/${live.sel}`);
    $("#detail-live").innerHTML = `<b>${live.sel}</b> <span class="muted">· ocupação recebida via MQTT (válidas) e coletas</span><canvas id="spark"></canvas>`;
    const cv = $("#spark"), r = cv.getBoundingClientRect(), d = devicePixelRatio || 1;
    cv.width = r.width * d; cv.height = r.height * d; const g = cv.getContext("2d"); g.scale(d, d);
    const pts = h.telemetria.filter(x => x[2] && x[1] !== null); if (!pts.length) return;
    const t0 = pts[0][0], t1 = pts[pts.length - 1][0] || t0 + 1, W = r.width, Hh = r.height;
    const X = t => 30 + (t - t0) / (t1 - t0 || 1) * (W - 38), Y = v => Hh - 14 - v / 100 * (Hh - 24);
    g.strokeStyle = css("--line"); g.fillStyle = css("--muted"); g.font = "10px system-ui";
    [0, 50, 100].forEach(v => { g.beginPath(); g.moveTo(30, Y(v)); g.lineTo(W - 6, Y(v)); g.stroke(); g.fillText(v + "%", 2, Y(v) + 3); });
    g.strokeStyle = css("--r"); g.setLineDash([3, 3]); g.beginPath(); g.moveTo(30, Y(75)); g.lineTo(W - 6, Y(75)); g.stroke(); g.setLineDash([]);
    g.strokeStyle = css("--accent"); g.lineWidth = 1.4; g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1]))); g.stroke();
    g.fillStyle = css("--ink"); h.coletas.forEach(([t]) => { if (t >= t0 && t <= t1) g.fillRect(X(t) - 1, Hh - 12, 2, 8); });
  } catch (e) { $("#detail-live").innerHTML = `<p class="muted">${e.message}</p>`; }
}
async function pollLive() {
  try { live.st = await getJSON("/api/state"); renderLive(); } catch (e) { $("#clock-live").textContent = "sem simulação ao vivo — execute: python -m wastesim.live"; }
  try {
    const ev = await getJSON("/api/events?limit=25");
    $("#events-live").innerHTML = ev.map(([dev, ts, tipo, det]) => `<div><b>${dev}</b> ${tipo.replace("_", " ")} <span class="muted">${hhmm(ts)} ${det !== "{}" ? det : ""}</span></div>`).join("") || '<span class="muted">nenhum evento</span>';
  } catch (e) { }
  setTimeout(pollLive, 1000);
}
$("#filters").onclick = e => { if (!e.target.dataset.f) return; live.filter = e.target.dataset.f; document.querySelectorAll("#filters button").forEach(b => b.classList.toggle("active", b === e.target)); renderLive(); };
document.querySelectorAll('input[name=view]').forEach(r => r.onchange = () => { live.mode = r.value; renderLive(); });

// ------------------------------------------------------------------ replay
const rp = { data: null, maps: [], k: 0, playing: false };
async function initReplay() {
  if (rp.data) return;
  try { rp.data = await getJSON("/api/replay"); } catch (e) { $("#rp-note").textContent = "experiments/results/replay.json ainda não foi gerado (python -m experiments.replay)."; return; }
  const D = rp.data;
  rp.maps = [new MapView($("#map-rp0")), new MapView($("#map-rp1"))];
  rp.maps.forEach(m => { m.resize(); m.fit([...D.containers.map(c => [c.lat, c.lon]), D.depot]); m.onchange = drawReplay; });
  D.runs.forEach((r, i) => $(`#rp-title-${i}`).textContent = `Política ${r.policy} — ${r.label}`);
  $("#rp-slider").max = D.frames_t.length - 1;
  $("#rp-slider").oninput = e => { rp.k = +e.target.value; drawReplay(); };
  $("#rp-play").onclick = () => { rp.playing = !rp.playing; $("#rp-play").textContent = rp.playing ? "❚❚ Pausar" : "▶ Reproduzir"; if (rp.playing) stepReplay(); };
  $("#rp-note").textContent = D.note;
  rp.k = Math.min(+(new URLSearchParams(location.search).get("k") || 0), D.frames_t.length - 1);
  drawReplay();
}
function drawReplay() {
  const D = rp.data, k = rp.k, t = D.frames_t[k], day = Math.floor(t / 86400);
  D.runs.forEach((r, i) => {
    const st = {
      deposito: D.depot,
      contentores: D.containers.map((c, j) => ({ ...c, real: r.fill[k][j], estimado: r.fill[k][j], desatualizado: false })),
      veiculos: (r.trucks[k] || []).map(([la, lo, vid]) => ({ lat: la, lon: lo, vid, done: false })),
      caminhos: r.paths[String(day)] || []
    };
    rp.maps[i].drawScene(st, "real");
    const q = r.kpi[k];
    $(`#rp-kpi-${i}`).innerHTML = kpi(fmt(q[0], 0), "km acumulados") + kpi(q[1], "coletas") + kpi(fmt(q[2], 1), "m³ transbordados") + kpi(q[3], "cheios agora");
  });
  $("#rp-slider").value = k; $("#rp-time").textContent = hhmm(t);
}
function stepReplay() {
  if (!rp.playing) return;
  rp.k = (rp.k + 1) % rp.data.frames_t.length; drawReplay();
  setTimeout(stepReplay, 400 / +$("#rp-speed").value);
}

// ------------------------------------------------------------------ resultados
let resultsDone = false;
async function initResults() {
  if (resultsDone) return; resultsDone = true;
  let R; try { R = await getJSON("/api/results"); } catch (e) { $("#results-body").innerHTML = `<p class="muted">${e.message}</p>`; return; }
  let html = `<div class="card"><h3>E1 — comparação principal (média e IC 95% sobre ${R.E1_seeds} sementes)</h3><table><tr><th>N</th><th>Política</th><th>km/dia</th><th>transbordamento (% vol.)</th><th>ocupação média na coleta</th><th>coletas &lt; 50%</th><th>visitas/dia</th></tr>`;
  for (const r of R.E1) html += `<tr><td>${r.N}</td><td>${r.policy}</td><td>${fmt(r.km_mean)} <span class="muted">[${fmt(r.km_lo)}; ${fmt(r.km_hi)}]</span></td><td>${fmt(r.ov_mean, 2)} <span class="muted">[${fmt(r.ov_lo, 2)}; ${fmt(r.ov_hi, 2)}]</span></td><td>${fmt(100 * r.fill_mean, 0)}%</td><td>${fmt(r.below50, 1)}%</td><td>${fmt(r.visits, 1)}</td></tr>`;
  html += `</table></div><div class="card"><h3>E2 — fronteira distância × transbordamento (N = 100)</h3><canvas id="frontier"></canvas><p class="muted">Cada ponto: média de ${R.E2_seeds} sementes para um nível do parâmetro da política; barras: IC 95%.</p></div>`;
  $("#results-body").innerHTML = html;
  const cv = $("#frontier"), r = cv.getBoundingClientRect(), d = devicePixelRatio || 1;
  cv.width = r.width * d; cv.height = r.height * d; const g = cv.getContext("2d"); g.scale(d, d);
  const P = R.E2, xs = P.flatMap(p => [p.ov_lo, p.ov_hi]), ys = P.flatMap(p => [p.km_lo, p.km_hi]);
  const x0 = 0, x1 = Math.max(...xs) * 1.05, y0 = 0, y1 = Math.max(...ys) * 1.05, W = r.width, H = r.height;
  const X = v => 60 + (v - x0) / (x1 - x0) * (W - 80), Y = v => H - 40 - (v - y0) / (y1 - y0) * (H - 60);
  g.strokeStyle = css("--line"); g.fillStyle = css("--muted"); g.font = "11px system-ui";
  for (let i = 0; i <= 5; i++) { const xv = x0 + i * (x1 - x0) / 5, yv = y0 + i * (y1 - y0) / 5;
    g.beginPath(); g.moveTo(X(xv), Y(y0)); g.lineTo(X(xv), Y(y1)); g.moveTo(X(x0), Y(yv)); g.lineTo(X(x1), Y(yv)); g.stroke();
    g.fillText(fmt(xv, 1) + "%", X(xv) - 12, H - 22); g.fillText(fmt(yv, 0), 20, Y(yv) + 4); }
  g.fillText("transbordamento (% do volume gerado)", W / 2 - 90, H - 6); g.save(); g.translate(12, H / 2 + 20); g.rotate(-Math.PI / 2); g.fillText("km/dia", 0, 0); g.restore();
  const cols = { A: "#555", "B-OR": "#e0b020", C: "#1b7f79", D: "#3a5bd9" };
  const pols = [...new Set(P.map(p => p.policy))];
  pols.forEach((pol, i) => {
    const pts = P.filter(p => p.policy === pol).sort((a, b) => a.ov_mean - b.ov_mean);
    g.strokeStyle = g.fillStyle = cols[pol] || "#999"; g.lineWidth = 1.6; g.beginPath();
    pts.forEach((p, k) => k ? g.lineTo(X(p.ov_mean), Y(p.km_mean)) : g.moveTo(X(p.ov_mean), Y(p.km_mean))); g.stroke();
    pts.forEach(p => { g.lineWidth = 1; g.beginPath(); g.moveTo(X(p.ov_lo), Y(p.km_mean)); g.lineTo(X(p.ov_hi), Y(p.km_mean)); g.moveTo(X(p.ov_mean), Y(p.km_lo)); g.lineTo(X(p.ov_mean), Y(p.km_hi)); g.stroke(); g.beginPath(); g.arc(X(p.ov_mean), Y(p.km_mean), 3.5, 0, 7); g.fill(); });
    g.fillRect(W - 120, 20 + 16 * i, 10, 10); g.fillText("Política " + pol, W - 105, 29 + 16 * i);
  });
}

// ------------------------------------------------------------------ início
(async () => {
  live.map = new MapView($("#map-live")); live.map.resize(); live.map.onchange = renderLive;
  try { ROADS = await getJSON("/api/roads"); } catch (e) { }
  pollLive();
  if (live.sel) setTimeout(loadHistory, 1500);
  const tab = new URLSearchParams(location.search).get("tab");
  if (tab) document.querySelector(`nav button[data-tab=${tab}]`)?.click();
})();
