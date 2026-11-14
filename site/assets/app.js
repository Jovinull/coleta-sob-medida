"use strict";
// Site do projeto: gráficos em SVG sem dependências, lidos de data/resultados.json.
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const NS = "http://www.w3.org/2000/svg";
const nf = (x, d = 1) => x == null || Number.isNaN(x) ? "—"
  : Number(x).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const sg = (x, d = 1) => { const z = Math.abs(x) < .5 * 10 ** -d; return (z ? "" : x > 0 ? "+" : "−") + nf(z ? 0 : Math.abs(x), d); };
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const isDark = () => {
  const t = document.documentElement.dataset.theme;
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
};

const POL = {
  "A": { v: "--pA", m: "square", nome: "Periódica fixa", d: "Cada contêiner tem uma frequência própria, calculada pelas taxas médias verdadeiras (referência otimista). Rotas OR-Tools. Não usa telemetria." },
  "B": { v: "--pB", m: "tdown", nome: "Limiar", d: "Coleta todo contêiner com ocupação estimada ≥ 75%. Rota por vizinho mais próximo + 2-opt, como em muitos protótipos." },
  "B-OR": { v: "--pBOR", m: "tup", nome: "Limiar + OR-Tools", d: "A mesma seleção de B, com rotas do OR-Tools. Isola o efeito do roteirizador." },
  "C": { v: "--pC", m: "circle", nome: "Dinâmica", d: "Obrigatórios ≥ 75% e opcionais ≥ 50% com prêmio de 1 m de rota por litro: o solver decide se vale o desvio." },
  "D": { v: "--pD", m: "diamond", nome: "Preditiva", d: "Como C, mas projeta a ocupação pela taxa estimada: torna obrigatório quem passaria de 95% até o fim do turno seguinte." },
};
const pc = p => cssv(POL[p].v);

function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function marker(g, shape, x, y, r, fill) {
  const ring = cssv("--surface");
  const a = { fill, stroke: ring, "stroke-width": 2 };
  if (shape === "square") return el("rect", { x: x - r, y: y - r, width: 2 * r, height: 2 * r, rx: 1.5, ...a }, g);
  if (shape === "circle") return el("circle", { cx: x, cy: y, r: r + .6, ...a }, g);
  const pts = shape === "diamond" ? [[0, -1.35], [1.25, 0], [0, 1.35], [-1.25, 0]]
    : shape === "tup" ? [[0, -1.3], [1.25, .9], [-1.25, .9]] : [[0, 1.3], [1.25, -.9], [-1.25, -.9]];
  return el("polygon", { points: pts.map(([u, v]) => `${x + u * r},${y + v * r}`).join(" "), ...a }, g);
}
function legendHTML(pols) {
  return pols.map(p => {
    const s = `<svg width="16" height="16" viewBox="0 0 16 16"></svg>`;
    return `<span data-p="${p}">${s}<b>${p}</b>&nbsp;${POL[p].nome}</span>`;
  }).join("");
}
function paintLegend(box, pols) {
  box.innerHTML = legendHTML(pols);
  $$("span", box).forEach(sp => { const p = sp.dataset.p; marker($("svg", sp), POL[p].m, 8, 8, 5.5, pc(p)); });
}

// ------------------------------------------------------------ tooltip
const tip = $("#tip");
function showTip(html, ev) {
  tip.innerHTML = html; tip.classList.add("on");
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
  if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
const hideTip = () => tip.classList.remove("on");

// ------------------------------------------------------------ escalas
const lin = (d0, d1, r0, r1) => v => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
const logS = (d0, d1, r0, r1) => v => r0 + (Math.log10(v) - Math.log10(d0)) / (Math.log10(d1) - Math.log10(d0)) * (r1 - r0);
function niceTicks(a, b, n = 5) {
  const step0 = (b - a) / n, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(s => s >= step0);
  // estende o domínio para fora, até múltiplos do passo, para nenhum dado ficar fora do eixo
  const lo = Math.floor(a / step + 1e-9) * step, hi = Math.ceil(b / step - 1e-9) * step;
  const out = []; for (let v = lo; v <= hi + step * 1e-6; v += step) out.push(+v.toFixed(10));
  return out;
}

function frame(host, H, m) {
  host.innerHTML = "";
  const W = Math.max(300, host.clientWidth);
  const svg = el("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img" });
  host.appendChild(svg);
  return { svg, W, H, x0: m.l, x1: W - m.r, y0: H - m.b, y1: m.t };
}
function axes(f, xs, ys, xt, yt, xfmt, yfmt, xlab, ylab) {
  const g = el("g", {}, f.svg);
  yt.forEach(v => {
    el("line", { x1: f.x0, x2: f.x1, y1: ys(v), y2: ys(v), class: "gridl" }, g);
    const t = el("text", { x: f.x0 - 8, y: ys(v) + 4, "text-anchor": "end" }, g); t.textContent = yfmt(v);
  });
  xt.forEach(v => {
    el("line", { x1: xs(v), x2: xs(v), y1: f.y0, y2: f.y0 + 5, stroke: cssv("--muted") }, g);
    const t = el("text", { x: xs(v), y: f.y0 + 18, "text-anchor": "middle" }, g); t.textContent = xfmt(v);
  });
  el("line", { x1: f.x0, x2: f.x1, y1: f.y0, y2: f.y0, stroke: cssv("--muted") }, g);
  const xl = el("text", { x: (f.x0 + f.x1) / 2, y: f.H - 4, "text-anchor": "middle" }, g); xl.textContent = xlab;
  const yl = el("text", { x: 14, y: (f.y0 + f.y1) / 2, transform: `rotate(-90 14 ${(f.y0 + f.y1) / 2})`, "text-anchor": "middle" }, g); yl.textContent = ylab;
}

// ------------------------------------------------------------ E1
let DATA = null, e1N = 100;
function drawE1() {
  const host = $("#e1-svg"); const rows = DATA.E1.filter(r => r.N === e1N);
  const f = frame(host, 380, { l: 62, r: 70, t: 16, b: 46 });
  const kx = rows.flatMap(r => [r.km.lo, r.km.hi]), oy = rows.flatMap(r => [r.ov.lo, r.ov.hi]);
  const xa = Math.min(...kx), xb = Math.max(...kx), pad = (xb - xa) * .12;
  const xt = niceTicks(xa - pad, xb + pad, 5), yt = niceTicks(0, Math.max(...oy) * 1.12, 5);
  const xs = lin(xt[0], xt[xt.length - 1], f.x0, f.x1), ys = lin(0, yt[yt.length - 1], f.y0, f.y1);
  axes(f, xs, ys, xt, yt, v => nf(v, 0), v => nf(v, 0) + "%", "km por dia (média, IC 95%)", "transbordamento (% do volume)");
  const g = el("g", {}, f.svg);
  rows.forEach(r => {
    const c = pc(r.policy), x = xs(r.km.m), y = ys(r.ov.m);
    el("line", { x1: xs(r.km.lo), x2: xs(r.km.hi), y1: y, y2: y, stroke: c, "stroke-width": 2, "stroke-linecap": "round" }, g);
    el("line", { x1: x, x2: x, y1: ys(r.ov.lo), y2: ys(r.ov.hi), stroke: c, "stroke-width": 2, "stroke-linecap": "round" }, g);
    marker(g, POL[r.policy].m, x, y, 6.5, c);
    const t = el("text", { x: x + 11, y: y - 9, class: "lbl" }, g); t.textContent = r.policy;
    const hit = el("circle", { cx: x, cy: y, r: 20, fill: "transparent", style: "cursor:pointer" }, g);
    const html = `<b>${r.policy} · ${POL[r.policy].nome}</b>${nf(r.km.m)} km/dia <span class="muted">[${nf(r.km.lo)}; ${nf(r.km.hi)}]</span><br>
      ${nf(r.ov.m, 2)}% transbordado <span class="muted">[${nf(r.ov.lo, 2)}; ${nf(r.ov.hi, 2)}]</span><br>
      ocupação na coleta: ${nf(100 * r.fill.m, 0)}%<br>coletas abaixo de 50%: ${nf(r.below50.m, 0)}%`;
    hit.addEventListener("mousemove", e => showTip(html, e)); hit.addEventListener("mouseleave", hideTip);
  });
  // tabela
  const comp = DATA.E1_comp.filter(c => c.N === e1N && c.ref === "A");
  const rel = (p, m) => { const c = comp.find(c => c.alt === p && c.metric === m); return c ? c : null; };
  $("#e1-tab").innerHTML = `<div class="tablewrap"><table><tr><th>Política</th><th class="n">km/dia</th><th class="n">IC 95%</th><th class="n">vs A</th><th class="n">Transb. %</th><th class="n">IC 95%</th><th class="n">vs A (p.p.)</th><th class="n">p (Holm)</th></tr>` +
    rows.map(r => { const k = rel(r.policy, "km_per_day"), o = rel(r.policy, "overflow_pct");
      return `<tr><td><b>${r.policy}</b> ${POL[r.policy].nome}</td><td class="n">${nf(r.km.m)}</td><td class="n">${nf(r.km.lo)}–${nf(r.km.hi)}</td><td class="n">${k ? sg(k.rel) + "%" : "—"}</td>
      <td class="n">${nf(r.ov.m, 2)}</td><td class="n">${nf(r.ov.lo, 2)}–${nf(r.ov.hi, 2)}</td><td class="n">${o ? sg(o.diff, 2) : "—"}</td><td class="n">${o ? (o.p_holm < .001 ? "< 0,001" : nf(o.p_holm, 3)) : "—"}</td></tr>`; }).join("") + `</table></div>`;
}

// ------------------------------------------------------------ E2
function drawE2() {
  const host = $("#e2-svg"); const pols = ["A", "B-OR", "C", "D"];
  const f = frame(host, 400, { l: 62, r: 54, t: 16, b: 46 });
  const xs = logS(0.1, 15, f.x0, f.x1);
  const yt = niceTicks(85, 165, 5), ys = lin(yt[0], yt[yt.length - 1], f.y0, f.y1);
  axes(f, xs, ys, [0.1, 0.2, 0.5, 1, 2, 5, 10], yt, v => nf(v, v < 1 ? 1 : 0) + "%", v => nf(v, 0), "transbordamento (% do volume, escala log)", "km por dia");
  el("line", { x1: xs(1), x2: xs(1), y1: f.y1, y2: f.y0, stroke: cssv("--ink-2"), "stroke-dasharray": "4 4", "stroke-width": 1.2 }, f.svg);
  const ref = el("text", { x: xs(1) + 6, y: f.y1 + 12, class: "lbl" }, f.svg); ref.textContent = "1%";
  const pts = [];
  pols.forEach(p => {
    const rows = DATA.E2.filter(r => r.policy === p).sort((a, b) => a.ov - b.ov), c = pc(p);
    el("path", { d: rows.map((r, i) => (i ? "L" : "M") + xs(r.ov) + "," + ys(r.km)).join(""), fill: "none", stroke: c, "stroke-width": 2, "stroke-linejoin": "round" }, f.svg);
    rows.forEach(r => { marker(f.svg, POL[p].m, xs(r.ov), ys(r.km), 4.8, c); pts.push({ p, r, x: xs(r.ov), y: ys(r.km) }); });
    const last = rows[rows.length - 1];
    const t = el("text", { x: xs(last.ov) + 9, y: ys(last.km) + 4, class: "lbl" }, f.svg); t.textContent = p;
  });
  const hov = el("circle", { r: 9, fill: "none", stroke: cssv("--ink"), "stroke-width": 1.5, opacity: 0 }, f.svg);
  const ov = el("rect", { x: f.x0, y: f.y1, width: f.x1 - f.x0, height: f.y0 - f.y1, fill: "transparent" }, f.svg);
  ov.addEventListener("mousemove", e => {
    const b = f.svg.getBoundingClientRect(), sx = f.W / b.width, mx = (e.clientX - b.left) * sx, my = (e.clientY - b.top) * sx;
    let best = null, bd = 1e9; pts.forEach(q => { const d = Math.hypot(q.x - mx, q.y - my); if (d < bd) { bd = d; best = q; } });
    if (!best || bd > 40) { hideTip(); hov.setAttribute("opacity", 0); return; }
    hov.setAttribute("cx", best.x); hov.setAttribute("cy", best.y); hov.setAttribute("opacity", 1);
    showTip(`<b>${best.p} · ${POL[best.p].nome}</b>parâmetro: ${nf(best.r.level, 2)}<br>${nf(best.r.km)} km/dia <span class="muted">[${nf(best.r.km_lo)}; ${nf(best.r.km_hi)}]</span><br>${nf(best.r.ov, 2)}% transbordado <span class="muted">[${nf(best.r.ov_lo, 2)}; ${nf(best.r.ov_hi, 2)}]</span>`, e);
  });
  ov.addEventListener("mouseleave", () => { hideTip(); hov.setAttribute("opacity", 0); });
  $("#e2-tab").innerHTML = `<div class="tablewrap"><table><tr><th>Política</th><th class="n">parâmetro</th><th class="n">km/dia</th><th class="n">transbordamento %</th></tr>` +
    DATA.E2.map(r => `<tr><td>${r.policy}</td><td class="n">${nf(r.level, 2)}</td><td class="n">${nf(r.km)}</td><td class="n">${nf(r.ov, 2)}</td></tr>`).join("") + `</table></div>`;
}

// ------------------------------------------------------------ mapas de calor
const E3_GROUPS = [
  ["Comunicação", ["perda_5%", "perda_20%", "perda_50%", "interrupcao_48h", "interrupcao_48h_sem_fallback"]],
  ["Sensores", ["falha_perm_10%", "falha_perm_30%", "falha_perm_30%_sem_fallback", "congelado_10%"]],
  ["Ruído de medição", ["ruido_0", "ruido_3x", "ruido_6x"]],
  ["Período de amostragem (base: 1 h)", ["amostra_15min", "amostra_6h", "amostra_24h"]],
];
const E4_GROUPS = [
  ["Demanda", ["demanda_0.7", "demanda_1.3", "alta_variabilidade", "mudanca_regime_30%x1.6", "surto_geral_x1.3"]],
  ["Operação", ["frota_reduzida", "layout_agrupado", "velocidade_15", "velocidade_30"]],
];
function divColor(t) { // t em [-1, 1]
  const pole = t < 0 ? "var(--div-neg)" : "var(--div-pos)";
  return `color-mix(in oklab, ${pole} ${Math.round(Math.abs(t) * 100)}%, var(--div-mid))`;
}
function seqColor(t) { // t em [0, 1], 5 paradas
  t = Math.max(0, Math.min(1, t)); const i = Math.min(3, Math.floor(t * 4)), u = t * 4 - i;
  return `color-mix(in oklab, var(--seq-${i + 1}) ${Math.round(u * 100)}%, var(--seq-${i}))`;
}
let e3M = "ov", e4M = "ov";
function drawE3() {
  const pols = ["B-OR", "C", "D"];
  const get = (c, p) => DATA.E3.find(r => r.cond === c && r.policy === p);
  const lim = e3M === "ov" ? 16 : 16;
  let h = `<table class="heat"><tr><th></th>${pols.map(p => `<th>${p}</th>`).join("")}</tr>`;
  E3_GROUPS.forEach(([gname, conds]) => {
    h += `<tr class="grp"><th colspan="${pols.length + 1}">${gname}</th></tr>`;
    conds.forEach(c => {
      const lab = get(c, "D")?.label ?? c;
      h += `<tr><th class="rowh">${lab}</th>` + pols.map(p => {
        const r = get(c, p); if (!r) return "<td>—</td>";
        const v = e3M === "ov" ? r.d_ov : r.d_km_pct, pv = e3M === "ov" ? r.p_holm : r.p_holm_km;
        const t = Math.sign(v) * Math.min(1, Math.sqrt(Math.abs(v) / lim));
        const ink = Math.abs(t) > .55 ? "#fff" : "var(--ink)";
        const ns = pv == null || pv >= .05;
        const tipH = `<b>${p} · ${lab}</b>transbordamento: ${nf(r.ov.m, 2)}% (base ${nf(DATA.E3_base[p].ov.m, 2)}%)<br>variação: ${sg(r.d_ov, 2)} p.p. ${r.p_holm != null ? `· p<sub>Holm</sub> ${r.p_holm < .001 ? "< 0,001" : nf(r.p_holm, 3)}` : ""}<br>distância: ${nf(r.km.m)} km/dia (${sg(r.d_km_pct, 1)}%)`;
        return `<td class="${ns ? "ns" : ""}" style="background:${divColor(t)};color:${ink}" data-tip="${encodeURIComponent(tipH)}">${sg(v, e3M === "ov" ? 2 : 1)}${ns ? "" : ""}</td>`;
      }).join("") + "</tr>";
    });
  });
  $("#e3-heat").innerHTML = h + "</table>";
  $("#e3-scale").innerHTML = `<span>${e3M === "ov" ? "melhora" : "menos km"}</span><span class="bar" style="background:linear-gradient(90deg, var(--div-neg), var(--div-mid), var(--div-pos))"></span><span>${e3M === "ov" ? "piora" : "mais km"}</span><span style="margin-left:12px">valores em ${e3M === "ov" ? "pontos percentuais" : "% de distância"} em relação à base · <i>itálico</i> = não significativo</span>`;
  bindHeatTips("#e3-heat");
}
function drawE4() {
  const pols = ["A", "B-OR", "C", "D"];
  const get = (c, p) => c === "base" ? { ov: DATA.E4_base[p].ov, km: DATA.E4_base[p].km, label: "base" } : DATA.E4.find(r => r.cond === c && r.policy === p);
  const vals = DATA.E4.map(r => e4M === "ov" ? r.ov.m : r.km.m);
  const kmMin = Math.min(...vals), kmMax = Math.max(...vals);
  const tOf = v => e4M === "ov" ? (Math.log10(Math.max(v, .3)) - Math.log10(.3)) / (Math.log10(40) - Math.log10(.3)) : (v - kmMin) / (kmMax - kmMin);
  const dark = isDark();
  let h = `<table class="heat"><tr><th></th>${pols.map(p => `<th>${p}</th>`).join("")}</tr>`;
  [["Referência", ["base"]], ...E4_GROUPS].forEach(([gname, conds]) => {
    h += `<tr class="grp"><th colspan="${pols.length + 1}">${gname}</th></tr>`;
    conds.forEach(c => {
      const lab = c === "base" ? "cenário-base" : get(c, "A")?.label ?? c;
      h += `<tr><th class="rowh">${lab}</th>` + pols.map(p => {
        const r = get(c, p); if (!r) return "<td>—</td>";
        const v = e4M === "ov" ? r.ov.m : r.km.m, t = tOf(v);
        const ink = (dark ? t < .5 : t > .5) ? (dark ? "var(--ink)" : "#fff") : (dark ? "#0b0b0b" : "var(--ink)");
        const tipH = `<b>${p} · ${lab}</b>transbordamento: ${nf(r.ov.m, 2)}% <span class="muted">[${nf(r.ov.lo, 2)}; ${nf(r.ov.hi, 2)}]</span><br>distância: ${nf(r.km.m)} km/dia <span class="muted">[${nf(r.km.lo)}; ${nf(r.km.hi)}]</span>`;
        return `<td style="background:${seqColor(t)};color:${ink}" data-tip="${encodeURIComponent(tipH)}">${nf(v, e4M === "ov" ? 2 : 1)}</td>`;
      }).join("") + "</tr>";
    });
  });
  $("#e4-heat").innerHTML = h + "</table>";
  $("#e4-scale").innerHTML = e4M === "ov"
    ? `<span>0,3%</span><span class="bar" style="background:linear-gradient(90deg, var(--seq-0), var(--seq-1), var(--seq-2), var(--seq-3), var(--seq-4))"></span><span>40% (escala log)</span>`
    : `<span>${nf(kmMin, 0)} km</span><span class="bar" style="background:linear-gradient(90deg, var(--seq-0), var(--seq-1), var(--seq-2), var(--seq-3), var(--seq-4))"></span><span>${nf(kmMax, 0)} km/dia</span>`;
  bindHeatTips("#e4-heat");
}
function bindHeatTips(sel) {
  $$(`${sel} td[data-tip]`).forEach(td => {
    td.addEventListener("mousemove", e => showTip(decodeURIComponent(td.dataset.tip), e));
    td.addEventListener("mouseleave", hideTip);
  });
}

// ------------------------------------------------------------ blocos de texto
function fillStatic() {
  const D = DATA, e1 = D.E1.filter(r => r.N === 100), g = p => e1.find(r => r.policy === p);
  const cmp = (p, m) => D.E1_comp.find(c => c.N === 100 && c.ref === "A" && c.alt === p && c.metric === m);
  $("#kpis-e1").innerHTML = [
    ["good", sg(cmp("C", "km_per_day").rel) + "%", "distância de C (dinâmica) em relação a A"],
    ["bad", nf(g("C").ov.m, 2) + "%", `transbordamento de C, contra ${nf(g("A").ov.m, 2)}% em A`],
    ["good", sg(cmp("D", "km_per_day").rel) + "%", "distância de D (preditiva), sem diferença significativa de transbordamento"],
    ["good", sg(D.E2_comp.find(c => c.family === "E2/km@1.0%" && c.alt === "D" && c.ref === "A").rel) + "%", "distância de D no mesmo nível de serviço (1%)"],
  ].map(([k, b, s]) => `<div class="kpi ${k}"><b>${b}</b><span>${s}</span></div>`).join("");
  $("#fill-a").textContent = nf(100 * g("A").fill.m, 0) + "%"; $("#fill-b").textContent = nf(100 * g("B").fill.m, 0) + "%";

  const e2 = f => D.E2_comp.filter(c => c.family === f);
  const at1 = e2("E2/km@1.0%"), dc = at1.find(c => c.ref === "C");
  $("#e2-cards").innerHTML = ["B-OR", "C", "D"].map(p => {
    const c = at1.find(c => c.ref === "A" && c.alt === p);
    return `<div class="kpi good"><b>${sg(c.rel)}%</b><span>km/dia de ${p} para manter 1% de transbordamento, em relação a A (p<sub>Holm</sub> < 0,001)</span></div>`;
  }).join("");
  $("#e2-cards").insertAdjacentHTML("afterend", `<p class="muted small" style="margin-top:12px">D contra C no mesmo nível: ${sg(dc.rel)}% (p<sub>Holm</sub> = ${nf(dc.p_holm, 2)}, não significativo). Esses 9% a 10% são bem menores que os ~21% de C com os parâmetros padrão, que vinham acompanhados de mais transbordamento.</p>`);

  const E6 = D.E6, q1 = E6.T1.find(t => t.qos === 1);
  $("#e6-kpis").innerHTML = [
    [nf(q1.deliv_min, 0) + "%", `entrega com QoS 1 (${q1.reps} × ${nf(q1.published, 0)} mensagens, ~${nf(q1.rate, 0)} msg/s)`],
    [nf(q1.lat_med, 2) + " ms", `latência mediana local (p99 ${nf(q1.lat_p99, 2)} ms)`],
    [`${E6.T4.offline_detected}/${E6.T4.crashed}`, `quedas abruptas detectadas pelo LWT em até ${nf(E6.T4.detection_s_max, 1)} s`],
    [`${E6.T5.rejected}/${E6.T5.sent}`, "mensagens malformadas rejeitadas sem alterar o estado"],
  ].map(([b, s]) => `<div class="kpi"><b>${b}</b><span>${s}</span></div>`).join("");
  $("#e6-restart").innerHTML = `<div class="tablewrap"><table><tr><th>QoS</th><th class="n">publicadas</th><th class="n">perdidas</th><th class="n">entrega</th><th class="n">reconectados</th></tr>` +
    E6.T3.map(t => `<tr><td>${t.qos}</td><td class="n">${nf(t.published_calls, 0)}</td><td class="n">${nf(t.lost, 0)}</td><td class="n">${nf(t.delivered_pct, 2)}%</td><td class="n">${t.devices_reconnected}/100</td></tr>`).join("") + `</table></div>
    <p class="muted small" style="margin-top:8px">Reinício do broker: ~${nf(E6.T3[1].broker_restart_s, 1)} s. Duplicatas: ${E6.T3[1].duplicates}.</p>`;
  $("#e6-rcfail").textContent = nf(E6.T3[1].publish_rc_not_success, 0);
  const T2 = E6.T2, rowsEq = [["visitas", "visits", 0], ["transbordamentos", "overflow_events", 0], ["km", "km_total", 1], ["coletado (m³)", "collected_m3", 2], ["transbordado (m³)", "overflow_m3", 3]];
  $("#e6-eq").innerHTML = `<tr><th>Métrica</th><th class="n">lote</th><th class="n">lote quantizado</th><th class="n">live (broker)</th></tr>` +
    rowsEq.map(([l, k, d]) => `<tr><td>${l}</td><td class="n">${nf(T2.batch[k], d)}</td><td class="n">${nf(T2.batch_quantized[k], d)}</td><td class="n"><b>${nf(T2.live[k], d)}</b></td></tr>`).join("");

  $("#int-kpis").innerHTML = [
    [nf(D.totais.execucoes, 0), `execuções E1–E5, ${D.totais.falhas} com falha`],
    [`${D.repro.identical}/${D.repro.n}`, "reexecuções sorteadas idênticas às originais"],
    ["3,7 × 10⁻⁸ L", "maior resíduo do balanço de volume (gerado = coletado + transbordado + estoque)"],
    ["67", "testes automatizados · 99 fontes catalogadas, 63 citadas no artigo"],
  ].map(([b, s]) => `<div class="kpi"><b>${b}</b><span>${s}</span></div>`).join("");
}

function renderPolicies() {
  $("#politicas").innerHTML = Object.entries(POL).map(([k, p]) =>
    `<div class="card pol"><span class="sw" style="background:${pc(k)}"></span><span class="badge" style="background:${pc(k)}">${k}</span><h3>${p.nome}</h3><p>${p.d}</p></div>`).join("") +
    `<div class="card pol"><span class="sw" style="background:var(--line)"></span><span class="badge" style="background:var(--muted)">=</span><h3>Mesmas regras para todas</h3><p>Mesma frota, capacidade, jornada, velocidade e tempos de serviço. Frota dimensionada por ⌈Σμ / (0,7·Q)⌉. OR-Tools com descida gulosa determinística.</p></div>`;
}

function drawAll() {
  if (!DATA) return;
  renderPolicies(); paintLegend($("#e1-leg"), ["A", "B", "B-OR", "C", "D"]); paintLegend($("#e2-leg"), ["A", "B-OR", "C", "D"]);
  drawE1(); drawE2(); drawE3(); drawE4();
}

// ------------------------------------------------------------ interação geral
function segmented(id, fn) {
  $(id).addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    $$("button", $(id)).forEach(x => x.classList.toggle("on", x === b)); fn(b.dataset);
  });
}
segmented("#e1-n", d => { e1N = +d.n; drawE1(); });
segmented("#e3-m", d => { e3M = d.m; drawE3(); });
segmented("#e4-m", d => { e4M = d.m; drawE4(); });
$$("[data-table]").forEach(b => b.addEventListener("click", () => {
  const t = $("#" + b.dataset.table); t.hidden = !t.hidden; b.textContent = t.hidden ? "Ver tabela" : "Ocultar tabela";
}));
$$(".copy").forEach(b => b.addEventListener("click", async () => {
  const txt = b.parentElement.querySelector("pre").innerText.split("\n").filter(l => !l.trim().startsWith("#")).join("\n").trim();
  try { await navigator.clipboard.writeText(txt); b.textContent = "copiado"; } catch (e) { b.textContent = "selecione e copie"; }
  setTimeout(() => b.textContent = "copiar", 1600);
}));
$("#tema").addEventListener("click", () => {
  const next = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("tema", next); } catch (e) { }
  drawAll();
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", drawAll);
// lightbox
const lb = $("#lb");
$$("figure img").forEach(img => img.addEventListener("click", () => { $("img", lb).src = img.src; $("img", lb).alt = img.alt; lb.classList.add("on"); }));
lb.addEventListener("click", () => lb.classList.remove("on"));
addEventListener("keydown", e => { if (e.key === "Escape") lb.classList.remove("on"); });
// vídeos tocam quando visíveis
const vio = new IntersectionObserver(es => es.forEach(e => {
  const v = e.target; if (e.isIntersecting) { v.preload = "auto"; v.play().catch(() => { }); } else v.pause();
}), { threshold: .35 });
$$(".videos video").forEach(v => vio.observe(v));
// navegação ativa
const nio = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) $$("#nav a").forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id));
}), { rootMargin: "-45% 0px -50% 0px" });
$$("section[id]").forEach(s => nio.observe(s));
// contadores
const cio = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return; cio.unobserve(e.target);
  const n = +e.target.dataset.count, t0 = performance.now();
  if (matchMedia("(prefers-reduced-motion: reduce)").matches || n === 0) return;
  const step = t => { const k = Math.min(1, (t - t0) / 1200), v = Math.round(n * (1 - (1 - k) ** 3)); e.target.textContent = v.toLocaleString("pt-BR"); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}));
$$("[data-count]").forEach(x => cio.observe(x));

let rt; new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(() => { if (DATA) { drawE1(); drawE2(); } }, 120); }).observe($("#e1-svg"));

fetch("data/resultados.json").then(r => r.json()).then(d => { DATA = d; fillStatic(); drawAll(); })
  .catch(e => { $("#e1-svg").innerHTML = `<p class="muted">Não foi possível carregar os dados (${e.message}).</p>`; });
