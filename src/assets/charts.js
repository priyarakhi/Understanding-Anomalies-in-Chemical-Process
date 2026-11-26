(function () {
  "use strict";
  const C = window.CD, root = document.getElementById("root");
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const pad = (x) => String(x).padStart(2, "0");
  const clock = (sec) => `${pad(Math.floor(sec / 3600))}:${pad(Math.floor((sec % 3600) / 60))}:${pad(Math.round(sec) % 60)}`;
  const hhmm = (sec) => `${pad(Math.floor(sec / 3600))}:${pad(Math.floor((sec % 3600) / 60))}`;
  const GRP = (s) => (s[0] === "T" ? "T" : s === "PY23" ? "P" : s.startsWith("PDI") ? "D" : "F");
  const GC = { T: "#c0392b", F: "#2b6cb0", D: "#8e44ad", P: "#1e8449" };
  const fmt = (s, v) => (v == null ? "–" : s[0] === "T" ? v.toFixed(2) + " °C" : s === "PY23" ? v.toFixed(1) + " mbar" : s === "PDI702" ? v.toFixed(2) + " mbar" : v.toFixed(3));
  const tip = document.createElement("div"); tip.className = "tip"; document.body.appendChild(tip);
  const showTip = (ev, html) => { tip.innerHTML = html; tip.style.opacity = 1; const w = tip.offsetWidth; tip.style.left = Math.min(ev.clientX + 14, window.innerWidth - w - 8) + "px"; tip.style.top = Math.max(4, ev.clientY - 10 - tip.offsetHeight) + "px"; };
  const hideTip = () => (tip.style.opacity = 0);
  const SH = { pert: "rgba(230,126,34,.25)", ev: "rgba(192,57,43,.13)", spike: "rgba(142,68,173,.25)" };

  // ------------------------------------------------------------------ line chart (min/max per pixel keeps spikes)
  function decimate(sr, x0, x1, nb) {
    const i0 = Math.max(0, Math.ceil((x0 - sr.t0) / sr.step)), i1 = Math.min(sr.y.length - 1, Math.floor((x1 - sr.t0) / sr.step)), out = [];
    if (i1 < i0) return out;
    const n = i1 - i0 + 1;
    if (n <= nb * 2) { for (let i = i0; i <= i1; i++) out.push([sr.t0 + i * sr.step, sr.y[i]]); return out; }
    const per = n / nb;
    for (let b = 0; b < nb; b++) {
      const a = i0 + Math.floor(b * per), z = Math.min(i1, i0 + Math.floor((b + 1) * per) - 1);
      let mi = a, ma = a;
      for (let i = a; i <= z; i++) { if (sr.y[i] < sr.y[mi]) mi = i; if (sr.y[i] > sr.y[ma]) ma = i; }
      const p = [mi, ma].sort((u, v) => u - v);
      out.push([sr.t0 + p[0] * sr.step, sr.y[p[0]]]); if (p[1] !== p[0]) out.push([sr.t0 + p[1] * sr.step, sr.y[p[1]]]);
    }
    return out;
  }
  const niceStep = (span, target, list) => list.find((u) => span / u <= target) || list[list.length - 1];
  function chart(el, cfg) {
    const W = Math.max(320, Math.round(el.clientWidth || 700)), H = cfg.height || 140, L = cfg.left || 150, R = 14, T = cfg.top || 8, B = cfg.noX ? 4 : 24;
    const [x0, x1] = cfg.xr, pw = W - L - R, ph = H - T - B;
    const pts = cfg.series.map((sr) => decimate(sr, x0, x1, Math.round(pw)));
    let lo = Infinity, hi = -Infinity;
    pts.forEach((p) => p.forEach(([, y]) => { if (y < lo) lo = y; if (y > hi) hi = y; }));
    if (cfg.band) { lo = Math.min(lo, cfg.band.lo); hi = Math.max(hi, cfg.band.hi); }
    if (cfg.ymin != null) lo = Math.min(lo, cfg.ymin);
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    const py = (hi - lo) * 0.1 || Math.abs(hi) * 0.01 || 1; lo -= py; hi += py;
    const X = (x) => L + pw * (x - x0) / Math.max(1e-9, x1 - x0), Y = (y) => T + ph - ph * (y - lo) / Math.max(1e-12, hi - lo);
    let g = `<svg class="chart" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">`;
    g += `<rect x="${L}" y="${T}" width="${pw}" height="${ph}" rx="6" fill="${cfg.bg || "#fbfcfe"}"/>`;
    (cfg.shade || []).forEach((s) => { const a = Math.max(x0, s.a), b = Math.min(x1, s.b); if (b < a) return;
      g += `<rect x="${X(a).toFixed(1)}" y="${T}" width="${Math.max(1.5, X(b) - X(a)).toFixed(1)}" height="${ph}" fill="${s.fill}"/>`; });
    if (cfg.band) g += `<rect x="${L}" y="${Y(cfg.band.hi).toFixed(1)}" width="${pw}" height="${Math.max(1, Y(cfg.band.lo) - Y(cfg.band.hi)).toFixed(1)}" fill="${cfg.band.fill || "rgba(43,108,176,.12)"}"/>`;
    const ys = niceStep(hi - lo, 4, [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]);
    for (let v = Math.ceil(lo / ys) * ys; v <= hi; v += ys) g += `<line x1="${L}" x2="${L + pw}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="#edf0f4"/><text class="ax" x="${L - 6}" y="${(Y(v) + 3.5).toFixed(1)}" text-anchor="end">${+v.toFixed(3)}</text>`;
    if (!cfg.noX) {
      const m = cfg.minutes, xs = m ? niceStep(x1 - x0, 9, [5, 10, 15, 20, 30, 60]) : niceStep(x1 - x0, 9, [30, 60, 120, 300, 600, 900, 1800, 3600]);
      for (let v = Math.ceil(x0 / xs) * xs; v <= x1; v += xs) g += `<text class="ax" x="${X(v).toFixed(1)}" y="${H - 7}" text-anchor="middle">${m ? v + " min" : xs < 60 ? clock(v) : hhmm(v)}</text>`;
    }
    pts.forEach((p, k) => { const sr = cfg.series[k]; if (p.length) g += `<polyline fill="none" stroke="${sr.color}" stroke-width="${sr.width || 1.4}" ${sr.dash ? `stroke-dasharray="${sr.dash}"` : ""} stroke-linejoin="round" points="${p.map(([x, y]) => X(x).toFixed(1) + "," + Y(y).toFixed(1)).join(" ")}"/>`; });
    if (cfg.ylab) g += `<text class="yl" x="2" y="${T + 14}">${esc(cfg.ylab)}</text>`;
    if (cfg.ysub) g += `<text class="ys" x="2" y="${T + 30}">${esc(cfg.ysub)}</text>`;
    (cfg.notes || []).forEach((n) => { if (n.x < x0 || n.x > x1) return; const x = X(n.x), y = n.y != null ? Y(n.y) : T + 14;
      g += `${n.y != null ? `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5" fill="${n.color}" stroke="#fff" stroke-width="2"/>` : ""}
        <g transform="translate(${(x + (n.dx || 8)).toFixed(1)},${(n.ty != null ? T + n.ty : y - 8).toFixed(1)})"><text class="note" style="fill:${n.color}" ${n.anchor ? `text-anchor="${n.anchor}"` : ""}>${n.text.split("\n").map((t, i) => `<tspan x="0" dy="${i ? 15 : 0}">${esc(t)}</tspan>`).join("")}</text></g>`; });
    g += `<line class="cross" x1="0" x2="0" y1="${T}" y2="${T + ph}" style="display:none"/></svg>`;
    el.innerHTML = g;
    const svg = el.querySelector("svg"), cross = svg.querySelector(".cross");
    const toX = (ev) => { const r = svg.getBoundingClientRect(); return x0 + ((ev.clientX - r.left) * W / r.width - L) / pw * (x1 - x0); };
    if (cfg.onhover) { svg.addEventListener("mousemove", (ev) => cfg.onhover(Math.max(x0, Math.min(x1, toX(ev))), ev)); svg.addEventListener("mouseleave", () => cfg.onhover(null)); }
    return { setCross(x) { if (x == null || x < x0 || x > x1) { cross.style.display = "none"; return; } cross.style.display = ""; cross.setAttribute("x1", X(x)); cross.setAttribute("x2", X(x)); } };
  }
  function evShade(events) {
    const out = [];
    (events || []).forEach((e) => {
      if (e.kind === "spike") { out.push({ a: e.b, b: e.e, fill: SH.spike }); return; }
      if (e.pb != null) out.push({ a: e.pb, b: e.pe, fill: SH.pert });
      out.push({ a: e.b, b: e.e, fill: SH.ev });
    });
    return out;
  }

  // ------------------------------------------------------------------ 1 all recordings as bars
  function recordings() {
    const rows = C.rows, W = Math.max(500, root.clientWidth), L = 220, R = 20, rh = 30, T = 8, H = T + rows.length * rh + 30;
    const mx = Math.max(...rows.map((r) => r.minutes)), X = (m) => L + (W - L - R) * m / (Math.ceil(mx / 30) * 30);
    let g = `<svg class="chart" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">`;
    for (let m = 0; m <= Math.ceil(mx / 30) * 30; m += 30) g += `<line x1="${X(m)}" x2="${X(m)}" y1="${T}" y2="${H - 24}" stroke="#edf0f4"/><text class="ax" x="${X(m)}" y="${H - 8}" text-anchor="middle">${m === 0 ? "0" : m + " min"}</text>`;
    let lastOp = null;
    rows.forEach((r, i) => {
      const y = T + i * rh;
      if (r.op !== lastOp && i) g += `<line x1="8" x2="${W - R}" y1="${y - 1}" y2="${y - 1}" stroke="#e2e8f0"/>`;
      if (r.op !== lastOp) g += `<text class="opl" x="8" y="${y + 19}">${r.op}</text><text class="ax" x="8" y="${y + 19 + rh}">≈ ${r.p} mbar</text>`;
      lastOp = r.op;
      g += `<text class="rl" x="${L - 10}" y="${y + 19}" text-anchor="end">${esc(r.kind)}</text>`;
      g += `<g class="bar" data-i="${i}"><rect x="${L}" y="${y + 6}" width="${(X(r.minutes) - L).toFixed(1)}" height="18" rx="5" fill="${r.type === "normal" ? "#9dc0e6" : "#f0b3ac"}"/>`;
      r.marks.forEach(([a, b, k]) => { g += `<rect x="${X(a).toFixed(1)}" y="${y + (k === "spike" ? 18 : 6)}" width="${Math.max(2, X(b) - X(a)).toFixed(1)}" height="${k === "spike" ? 6 : 18}" fill="${k === "spike" ? "#8e44ad" : "#c0392b"}" opacity="${k === "spike" ? 0.75 : 0.85}"/>`; });
      g += `<text class="bl" x="${(X(r.minutes) + 6).toFixed(1)}" y="${y + 19}">${r.minutes} min</text></g>`;
    });
    root.innerHTML = g + `</svg>`;
    root.querySelectorAll(".bar").forEach((b) => {
      const r = rows[+b.dataset.i];
      b.addEventListener("mousemove", (ev) => showTip(ev, `<b>${r.op} · ${esc(r.kind)}</b><br>${r.file}<br>${r.start} – ${r.end} (clock time) · ${r.rows.toLocaleString("en")} rows<br>${r.n ? r.n + " annotated anomalies" : "no anomalies (normal run)"}`));
      b.addEventListener("mouseleave", hideTip);
    });
  }

  // ------------------------------------------------------------------ 2 one series with callouts (worked example and small figures)
  function single() {
    root.innerHTML = C.panels.map((_, i) => `<div id="p${i}"></div>`).join("");
    C.panels.forEach((p, i) => {
      const series = p.series.map((s) => ({ t0: s.t0, step: s.step, y: s.y, color: s.color, width: s.width }));
      chart(document.getElementById("p" + i), { xr: C.xr, height: p.height, series, shade: p.shade, notes: p.notes, band: p.band, ylab: p.ylab, ysub: p.ysub, minutes: C.minutes, noX: p.noX, left: C.left || 150, top: p.top,
        onhover: p.hover === false ? null : (x, ev) => {
          if (x == null) return hideTip();
          showTip(ev, `<b>${C.minutes ? "minute " + x.toFixed(1) : clock(x)}</b><br>` + p.series.map((s) => { const i2 = Math.round((x - s.t0) / s.step); return `${esc(s.name || p.ylab)}: ${s.y[i2] == null ? "–" : fmt(p.sensor || p.ylab, s.y[i2])}`; }).join("<br>"));
        } });
    });
  }

  // ------------------------------------------------------------------ 3 explorer: stacked sensors + matching CSV row
  function explorer() {
    const R = C.run, ss = C.sensors, n = R.n, each = Math.max(70, Math.floor(C.chartH / ss.length));
    root.innerHTML = ss.map((s) => `<div id="e-${s}"></div>`).join("") + `<div class="rowhead">The matching row of the file <span id="rinfo"></span></div><div class="rowbox" id="rowbox"></div>`;
    const apis = ss.map((s, k) => chart(document.getElementById("e-" + s), {
      xr: C.xr, height: each + (k === ss.length - 1 ? 24 : 4), noX: k < ss.length - 1, left: 190,
      series: [{ t0: R.t0, step: R.step, y: R.v[s], color: GC[GRP(s)], width: 1.4 }], shade: evShade(R.events), ylab: s, ysub: C.names[s],
      onhover: (x, ev) => hover(x, ev),
    }));
    function hover(x, ev) {
      apis.forEach((a) => a.setCross(x));
      if (x == null) { hideTip(); return; }
      const i = Math.max(0, Math.min(n - 1, Math.round((x - R.t0) / R.step)));
      row(i);
      showTip(ev, `<b>${clock(R.t0 + i * R.step)}</b><br>` + ss.map((s) => `${s} ${esc(C.names[s])}: <b>${fmt(s, R.v[s][i])}</b>`).join("<br>"));
    }
    function row(i) {
      const cols = ["Time"].concat(C.all), vals = [clock(R.t0 + i * R.step)].concat(C.all.map((s) => String(R.v[s][i])));
      const w = cols.map((c, k) => Math.max(c.length, vals[k].length));
      document.getElementById("rinfo").textContent = `(line ${(i * R.step + 2).toLocaleString("en")} of ${C.file})`;
      document.getElementById("rowbox").innerHTML = `<span class="h">${cols.map((c, k) => c.padEnd(w[k])).join("  ")}</span>\n${vals.map((v, k) => `<span class="${k ? (ss.includes(C.all[k - 1]) ? "v on" : "v") : "tm"}">${v.padEnd(w[k])}</span>`).join("  ")}`;
    }
    const mid = Math.round(((C.xr[0] + C.xr[1]) / 2 - R.t0) / R.step); row(Math.max(0, Math.min(n - 1, mid)));
  }

  // ------------------------------------------------------------------ 4 operating points: pressure vs temperature + column profile
  function ops() {
    const O = C.ops, W = Math.max(700, root.clientWidth), H = 350, half = Math.floor(W / 2) - 10;
    const P = O.map((o) => o.p), pmin = 250, pmax = 750;
    const allT = O.flatMap((o) => Object.values(o.t)), tmin = Math.floor(Math.min(...allT) / 5) * 5 - 2, tmax = Math.ceil(Math.max(...allT) / 5) * 5 + 2;
    const shade = (i) => { const u = (O[i].p - 280) / 440; const a = [158, 202, 225], b = [8, 48, 107]; return `rgb(${a.map((c, k) => Math.round(c + (b[k] - c) * u)).join(",")})`; };
    // left: pressure (x) vs column-top temperature (y)
    const L1 = 56, R1 = 16, T1 = 36, B1 = 40, w1 = half - L1 - R1, h1 = H - T1 - B1;
    const t5 = O.map((o) => o.t.T705), y5min = Math.floor(Math.min(...t5) / 5) * 5 - 3, y5max = Math.ceil(Math.max(...t5) / 5) * 5 + 3;
    const X1 = (p) => L1 + w1 * (p - pmin) / (pmax - pmin), Y1 = (t) => T1 + h1 - h1 * (t - y5min) / (y5max - y5min);
    let g = `<svg class="chart" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">`;
    g += `<text class="yl" x="${L1 - 50}" y="16">Higher pressure → higher temperature</text>`;
    g += `<rect x="${L1}" y="${T1}" width="${w1}" height="${h1}" rx="6" fill="#fbfcfe"/>`;
    for (let p = 300; p <= 700; p += 100) g += `<line x1="${X1(p)}" x2="${X1(p)}" y1="${T1}" y2="${T1 + h1}" stroke="#edf0f4"/><text class="ax" x="${X1(p)}" y="${T1 + h1 + 16}" text-anchor="middle">${p}</text>`;
    for (let t = Math.ceil(y5min / 5) * 5; t <= y5max; t += 5) g += `<line x1="${L1}" x2="${L1 + w1}" y1="${Y1(t)}" y2="${Y1(t)}" stroke="#edf0f4"/><text class="ax" x="${L1 - 6}" y="${Y1(t) + 4}" text-anchor="end">${t}</text>`;
    g += `<text class="ax" x="${L1 + w1 / 2}" y="${H - 6}" text-anchor="middle">plant pressure PY23 (mbar)</text><text class="ax" transform="translate(14,${T1 + h1 / 2}) rotate(-90)" text-anchor="middle">column-top temperature T705 (°C)</text>`;
    const srt = O.map((o, i) => i).sort((a, b) => O[a].p - O[b].p);
    g += `<polyline fill="none" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="5 4" points="${srt.map((i) => X1(O[i].p).toFixed(1) + "," + Y1(O[i].t.T705).toFixed(1)).join(" ")}"/>`;
    O.forEach((o, i) => {
      const dy = o.op === "OP22" ? -14 : o.op === "OP18" ? 22 : -12;
      g += `<g class="opd" data-i="${i}" style="cursor:pointer"><circle cx="${X1(o.p).toFixed(1)}" cy="${Y1(o.t.T705).toFixed(1)}" r="8" fill="${shade(i)}" stroke="#fff" stroke-width="2"/>
        <text x="${(X1(o.p) + (o.op === "OP31" ? -12 : 12)).toFixed(1)}" y="${(Y1(o.t.T705) + dy).toFixed(1)}" text-anchor="${o.op === "OP31" ? "end" : "start"}" style="font-size:12.5px;font-weight:700;fill:#1b1f24">${o.op}</text></g>`;
    });
    // right: temperature profile up the column
    const S = ["T703", "T709", "T711", "T712", "T705"], LAB = ["boiler T703", "below C001 · T709", "C001/C002 · T711", "C002/C003 · T712", "column top · T705"];
    const x0 = half + 20, L2 = x0 + 128, R2 = 16, T2 = 36, B2 = 40, w2 = W - L2 - R2, h2 = H - T2 - B2;
    const X2 = (t) => L2 + w2 * (t - tmin) / (tmax - tmin), Y2 = (k) => T2 + h2 - h2 * k / (S.length - 1);
    g += `<text class="yl" x="${x0}" y="16">Temperature, boiler → column top</text>`;
    g += `<rect x="${L2}" y="${T2}" width="${w2}" height="${h2}" rx="6" fill="#fbfcfe"/>`;
    for (let t = Math.ceil(tmin / 10) * 10; t <= tmax; t += 10) g += `<line x1="${X2(t)}" x2="${X2(t)}" y1="${T2}" y2="${T2 + h2}" stroke="#edf0f4"/><text class="ax" x="${X2(t)}" y="${T2 + h2 + 16}" text-anchor="middle">${t}</text>`;
    S.forEach((s, k) => { g += `<line x1="${L2}" x2="${L2 + w2}" y1="${Y2(k)}" y2="${Y2(k)}" stroke="#edf0f4"/><text class="ax" x="${L2 - 8}" y="${Y2(k) + 4}" text-anchor="end">${LAB[k]}</text>`; });
    g += `<text class="ax" x="${L2 + w2 / 2}" y="${H - 6}" text-anchor="middle">temperature (°C), typical value in the normal runs</text>`;
    O.forEach((o, i) => {
      g += `<g class="opl" data-i="${i}" style="cursor:pointer"><polyline fill="none" stroke="${shade(i)}" stroke-width="2.6" stroke-linejoin="round" points="${S.map((s, k) => X2(o.t[s]).toFixed(1) + "," + Y2(k).toFixed(1)).join(" ")}"/>
        ${S.map((s, k) => `<circle cx="${X2(o.t[s]).toFixed(1)}" cy="${Y2(k).toFixed(1)}" r="3.5" fill="${shade(i)}"/>`).join("")}
</g>`;
    });
    O.forEach((o, i) => { const lx = x0 + 232 + (i % 6) * 58; g += `<g class="opl" data-i="${i}" style="cursor:pointer"><rect x="${lx}" y="6" width="12" height="12" rx="3" fill="${shade(i)}"/><text x="${lx + 16}" y="16" style="font-size:12px;font-weight:700;fill:#334155">${o.op}</text></g>`; });
    root.innerHTML = g + `</svg>`;
    const svg = root.querySelector("svg"); let pinned = null;
    const hi = (i) => { svg.querySelectorAll(".opd, .opl").forEach((el) => { el.style.opacity = i == null || +el.dataset.i === i ? 1 : 0.18; }); };
    svg.querySelectorAll(".opd, .opl").forEach((el) => {
      const i = +el.dataset.i, o = O[i];
      el.addEventListener("mousemove", (ev) => { if (pinned == null) hi(i); showTip(ev, `<b>${o.op}</b> · plant pressure ${o.p} mbar<br>` + S.map((s) => `${s} ${esc(C.names[s])}: ${o.t[s]} °C`).join("<br>")); });
      el.addEventListener("mouseleave", () => { hideTip(); if (pinned == null) hi(null); });
      el.addEventListener("click", () => { pinned = pinned === i ? null : i; hi(pinned); });
    });
  }

  // ------------------------------------------------------------------ 5 Question 1: grid + zoom view
  function q1() {
    const O = C.order, NM = C.names;
    const SYM = { rise: "↑", fall: "↓", swing: "⇅", spikes: "⚡", pattern: "∿", none: "", "n/a": "" };
    const WORD = { rise: "rises", fall: "falls", swing: "swings up and down", spikes: "jumps more often (short spikes)", pattern: "changes its pattern", none: "no clear change", "n/a": "not judged" };
    const REC = { yes: "back to normal", partly: "came back part of the way", no: "not back within 10 min after the end", "n/a": "" };
    const unit = (s) => (s[0] === "T" ? " °C" : s === "PY23" || s === "PDI702" ? " mbar" : "");
    const dig = (s) => (s[0] === "T" ? 2 : s === "PY23" ? 1 : 3);
    let sel = "OP18OP018TA001A002";
    const head = `<tr><th></th><th colspan="5" class="gh">Temperatures</th><th colspan="2" class="gh">Pressure</th><th colspan="4" class="gh">Flows and buffer vessel</th></tr>
      <tr><th class="an">Anomaly</th>${O.map((s) => `<th class="sh" title="${esc(NM[s])}">${s}</th>`).join("")}</tr>`;
    function cell(r, s) {
      const x = r.sensors[s], ann = r.annotated.includes(s), k = x.kind;
      const cls = ["c", k === "none" || k === "n/a" ? "empty" : "rec-" + (x.recovery || "na"), ann ? "ann" : "", k].join(" ");
      return `<td class="${cls}" data-k="${r.key}" data-s="${s}">${SYM[k] || ""}${x.reviewed ? '<i class="rv"></i>' : ""}</td>`;
    }
    let body = "";
    C.groups.forEach((g) => {
      body += `<tr class="grp"><td colspan="12">${esc(g.title)} <span>· ${esc(g.where)}</span></td></tr>`;
      g.keys.forEach((k) => {
        const r = C.rows[k];
        body += `<tr class="ar ${k === sel ? "sel" : ""} ${r.special ? "spec" : ""}" data-k="${k}"><td class="an"><b>${r.op} · ${r.id}</b>${r.cls === "Anomaly" ? ' <span class="se">side effect</span>' : ""}</td>` +
          (r.special && !O.some((s) => r.sensors[s].kind === "spikes") ? `<td colspan="11" class="note">${esc(r.special)}</td>` : O.map((s) => cell(r, s)).join("")) + `</tr>`;
      });
    });
    root.innerHTML = `<div class="q1"><div class="q1g"><table class="grid">${head}${body}</table></div><div class="q1d" id="det"></div></div>`;
    root.querySelectorAll("tr.ar").forEach((tr) => tr.addEventListener("click", () => { sel = tr.dataset.k; root.querySelectorAll("tr.ar").forEach((x) => x.classList.toggle("sel", x === tr)); detail(); }));
    root.querySelectorAll("td.c").forEach((td) => {
      td.addEventListener("mousemove", (ev) => {
        const r = C.rows[td.dataset.k], s = td.dataset.s, x = r.sensors[s];
        let t = `<b>${r.op} ${r.id} · ${s}</b> ${esc(NM[s])}<br>${WORD[x.kind]}`;
        if (x.size != null && x.kind !== "spikes" && x.kind !== "pattern") t += ` by ${Math.abs(x.size).toFixed(dig(s))}${unit(s)}`;
        if (x.delay != null && x.kind !== "none") t += `, ${x.delay} s after the onset`;
        if (x.recovery && REC[x.recovery]) t += `<br>${REC[x.recovery]}`;
        if (r.annotated.includes(s)) t += `<br><i>named by the experts in the annotation file</i>`;
        if (x.note) t += `<br>${esc(x.note)}`;
        if (x.reviewed) t += `<br><i>corrected after looking at the plot</i>`;
        showTip(ev, t);
      });
      td.addEventListener("mouseleave", hideTip);
    });
    function detail() {
      const r = C.rows[sel], d = C.data[sel], el = document.getElementById("det");
      const hdr = `<div class="dh"><b>${r.op} · ${r.id}</b> <span class="small">${r.cat !== "none" ? r.cat : "no category"} · ${r.cls === "Anomaly" ? "side effect" : "deliberate"}</span></div><div class="dw">${esc(r.what)}</div>
        <div class="small">${r.pb ? `Disturbance ${clock(r.pb)} – ${clock(r.pe)} · ` : ""}marked anomalous ${r.first} – ${r.last} · experts named: ${esc(r.annotated.join(", "))}</div>`;
      if (!d) { el.innerHTML = hdr + `<p class="dnote">${esc(r.special || "")}</p>`; return; }
      const react = O.filter((s) => !["none", "n/a"].includes(r.sensors[s].kind));
      const show = react.concat(r.annotated.filter((s) => O.includes(s) && !react.includes(s)));
      el.innerHTML = hdr + `<div class="dl"><span><i class="k1"></i>before</span><span><i class="k2"></i>disturbance</span><span><i class="k3"></i>marked anomalous</span><span><i class="k4"></i>level carried forward ± tolerance</span></div><div id="strip"></div>` +
        `<div class="dsub">${react.length} of 11 sensors react${show.length > react.length ? "; the annotated sensor without a clear change is shown too" : ""}:</div>` +
        show.map((s) => `<div class="sl" id="lab-${s}"></div><div id="ch-${s}"></div>`).join("") + (react.length ? "" : `<p class="dnote">No sensor shows a clear change with this method.</p>`);
      const xr = [d.t0, d.t0 + (d.v[O[0]].length - 1) * d.step];
      const sh = [{ a: d.t_on - 300, b: d.t_on, fill: "rgba(100,116,139,.14)" }];
      if (r.pb) sh.push({ a: r.pb, b: r.pe, fill: "rgba(230,126,34,.24)" });
      sh.push({ a: r.b, b: r.e, fill: "rgba(192,57,43,.12)" });
      // overview strip of the whole recording with a box around the zoomed part
      const st = d.strip, sr = { t0: st.t0, step: st.step, y: st.y, color: "#94a3b8", width: 1 };
      chart(document.getElementById("strip"), { xr: [st.t0, st.t0 + (st.y.length - 1) * st.step], height: 64, left: 132, series: [sr], ylab: "whole run", ysub: st.s,
        shade: [{ a: xr[0], b: xr[1], fill: "rgba(31,78,121,.12)" }, ...(r.pb ? [{ a: r.pb, b: r.pe, fill: "rgba(230,126,34,.5)" }] : []), { a: r.b, b: r.e, fill: "rgba(192,57,43,.35)" }] });
      show.forEach((s, i) => {
        const x = r.sensors[s], ys = d.v[s], last = i === show.length - 1;
        const series = [{ t0: d.t0, step: d.step, y: ys, color: { T: "#c0392b", F: "#2b6cb0", D: "#8e44ad", P: "#1e8449" }[s[0] === "T" ? "T" : s === "PY23" ? "P" : s.startsWith("PDI") ? "D" : "F"], width: 1.5 }];
        if (x.line) {
          const L = (t) => x.line[0] + x.line[1] * (t - d.t_on), ts = [d.t0, xr[1]];
          [0, 1, -1].forEach((m) => series.push({ t0: ts[0], step: ts[1] - ts[0], y: ts.map((t) => L(t) + m * x.tol), color: m ? "#9ec5ea" : "#2b6cb0", width: m ? 1 : 1.2, dash: m ? "3 3" : "6 4" }));
        }
        chart(document.getElementById("ch-" + s), { xr, height: last ? 112 : 88, noX: !last, left: 132, series, shade: sh, ylab: s, ysub: NM[s].length > 15 ? NM[s].slice(0, 14) + "…" : NM[s],
          onhover: (t, ev) => { if (t == null) return hideTip(); const j = Math.round((t - d.t0) / d.step); showTip(ev, `<b>${clock(d.t0 + j * d.step)}</b><br>${s}: ${ys[j] == null ? "–" : ys[j].toFixed(dig(s))}${unit(s)} (15-s median)`); } });
        let lab = `<b>${s}</b> ${SYM[x.kind] || ""} ${WORD[x.kind]}`;
        if (x.size != null && !["spikes", "pattern", "none"].includes(x.kind)) lab += ` by ${Math.abs(x.size).toFixed(dig(s))}${unit(s)}`;
        if (x.delay != null && x.kind !== "none") lab += `, ${x.delay} s after the onset`;
        if (x.recovery === "yes") lab += ` <span class="ok">✓ ${x.t_back ? "back at " + clock(x.t_back) : "back to normal"}</span>`;
        else if (x.recovery === "partly") lab += ` <span class="pt">~ came back part of the way</span>`;
        else if (x.recovery === "no") lab += ` <span class="no">✗ not back within 10 min after the end</span>`;
        if (r.annotated.includes(s)) lab += ` <span class="tag">annotated</span>`;
        if (x.note) lab += ` <span class="small">· ${esc(x.note)}</span>`;
        if (x.reviewed) lab += ` <span class="small">(corrected after looking at the plot)</span>`;
        document.getElementById("lab-" + s).innerHTML = lab;
      });
    }
    detail();
  }

  // ------------------------------------------------------------------ 6 Question 1, beginner view: pick an anomaly, watch it, see how often each sensor reacts
  function q1b() {
    const O = C.order, NM = C.names, R = C.rows;
    const GRPC = (s) => ({ T: "#c0392b", F: "#2b6cb0", D: "#8e44ad", P: "#1e8449" })[s[0] === "T" ? "T" : s === "PY23" ? "P" : s.startsWith("PDI") ? "D" : "F"];
    const unit = (s) => (s[0] === "T" ? " °C" : s === "PY23" || s === "PDI702" ? " mbar" : "");
    const dig = (s) => (s[0] === "T" ? 1 : s === "PY23" ? 0 : 2);
    const ICON = {
      gas: `<path class="ic" d="M8 30h24M14 30V14h12v16"/><circle class="icr" cx="20" cy="9" r="2.5"/><circle class="icr" cx="25" cy="5" r="1.8"/>`,
      sample: `<path class="ic" d="M6 26l14-14 4 4-14 14H6z"/><path class="ic" d="M22 10l4-4 4 4-4 4"/><path class="icr" d="M8 34c0-2 2-4 2-4s2 2 2 4a2 2 0 0 1-4 0z"/>`,
      air: `<path class="ic" d="M4 20h28"/><path class="icr" d="M6 13c4 0 4-4 8-4M14 29c4 0 4 4 8 4M20 13c3 0 3-3 6-3"/>`,
      leak: `<path class="ic" d="M4 18h10l8-6v12l-8-6"/><path class="ic" d="M22 18h10"/><circle class="icr" cx="18" cy="28" r="1.6"/><circle class="icr" cx="22" cy="32" r="1.3"/>`,
      cool: `<path class="ic" d="M18 4v28M6 11l24 14M6 25l24-14"/><path class="icr" d="M4 34L32 4"/>`,
      dial: `<path class="ic" d="M8 8v24M18 8v24M28 8v24"/><circle class="icr" cx="8" cy="14" r="3"/><circle class="icr" cx="18" cy="24" r="3"/><circle class="icr" cx="28" cy="12" r="3"/>`,
    };
    const S = { g: 1, k: "OP18OP018TA001A002", anim: null };
    root.innerHTML = `<div class="qb">
      <div class="step"><span class="no">1</span>Choose a kind of disturbance</div><div class="kinds" id="kinds"></div>
      <div class="step"><span class="no">2</span>Choose one anomaly</div><div class="achips" id="achips"></div>
      <div class="story" id="story"></div>
      <div class="step" id="bstep"><span class="no">3</span>Which sensors react most often? <span class="sub">Click a bar to list the anomalies.</span></div>
      <div id="bars"></div><div id="blist" class="achips"></div></div>`;
    function kinds() {
      document.getElementById("kinds").innerHTML = C.groups.map((g, i) => `<div class="kind ${i === S.g ? "on" : ""}" data-g="${i}"><svg viewBox="0 0 36 36">${ICON[g.icon]}</svg><div class="t">${esc(g.title)}</div><div class="n">${g.keys.length} ${g.keys.length === 1 ? "anomaly" : "anomalies"}</div></div>`).join("");
      document.querySelectorAll(".kind").forEach((k) => k.addEventListener("click", () => { S.g = +k.dataset.g; S.k = C.groups[S.g].keys.find((x) => !R[x].special) || C.groups[S.g].keys[0]; kinds(); chips(); story(); }));
    }
    function chips() {
      const g = C.groups[S.g];
      document.getElementById("achips").innerHTML = g.keys.map((k) => { const r = R[k]; return `<span class="chip ${k === S.k ? "on" : ""} ${r.special ? "spec" : ""}" data-k="${k}">${r.op} · ${r.id}${r.cls === "Anomaly" ? " (side effect)" : ""}</span>`; }).join("");
      document.querySelectorAll("#achips .chip").forEach((c) => c.addEventListener("click", () => { S.k = c.dataset.k; chips(); story(); }));
    }
    const KW = { rise: "rises", fall: "falls", swing: "swings up and down", spikes: "shows short spikes", pattern: "changes its rhythm" };
    const PL = { rise: "rise", fall: "fall", swing: "swing up and down", spikes: "spike", pattern: "change their rhythm" };
    const SG = { rise: "rises", fall: "falls", swing: "swings up and down", spikes: "spikes", pattern: "changes its rhythm" };
    const ONE = { temperatures: "1 temperature", pressures: "1 pressure", "flows and buffer vessel": "1 flow signal" };
    function sentence(s, x) {
      let a = x.reviewed && x.note ? x.note[0].toUpperCase() + x.note.slice(1) : KW[x.kind][0].toUpperCase() + KW[x.kind].slice(1);
      if (!x.reviewed && x.size != null && ["rise", "fall"].includes(x.kind)) a += ` by ${Math.abs(x.size).toFixed(dig(s))}${unit(s)}`;
      if (!x.reviewed && x.kind === "pattern" && x.note) a += ": " + x.note;
      const when = x.delay != null ? `<span class="when">starts ${x.delay < 90 ? x.delay + " s" : (x.delay / 60).toFixed(1) + " min"} after the onset</span>` : "";
      const rec = x.recovery === "yes" ? `<span class="rok">✓ back to normal${x.t_back ? " at " + clock(x.t_back).slice(0, 5) : ""}</span>` : x.recovery === "partly" ? `<span class="rpt">~ comes back only part of the way</span>` : x.recovery === "no" ? `<span class="rno">✗ stays different (not back within 10 min)</span>` : "";
      return { a, when, rec };
    }
    function story() {
      if (S.anim) cancelAnimationFrame(S.anim);
      const r = R[S.k], d = C.data[S.k], el = document.getElementById("story");
      const head = `<div class="sh"><b>${r.op} · ${r.id}</b> — ${esc(r.what)}</div><div class="small">${r.pb ? `Disturbance applied ${clock(r.pb)} – ${clock(r.pe)} · ` : ""}marked anomalous by the experts ${r.first} – ${r.last}</div>`;
      if (!d) { el.innerHTML = head + `<div class="special">${esc(r.special || "")}</div>`; return; }
      const react = O.filter((s) => !["none", "n/a"].includes(r.sensors[s].kind)), quiet = O.filter((s) => !react.includes(s));
      // the three answers for this anomaly
      const named = r.annotated.filter((s) => O.includes(s));
      const grp = { temperatures: ["T703", "T709", "T711", "T712", "T705"], pressures: ["PY23", "PDI701"], "flows and buffer vessel": ["FT704", "FT703", "PDI702", "FYI702"] };
      const what = Object.entries(grp).map(([n, ss]) => { const ks = ss.filter((s) => react.includes(s)).map((s) => r.sensors[s].kind); if (!ks.length) return null;
        const top = ks.sort((a, b) => ks.filter((v) => v === b).length - ks.filter((v) => v === a).length)[0]; return ks.length === 1 ? `${ONE[n]} ${SG[top]}` : `${n} ${PL[top]}`; }).filter(Boolean).join(" · ") || "no clear change";
      const nr = (q) => react.filter((s) => r.sensors[s].recovery === q).length;
      const nna = react.length - nr("yes") - nr("partly") - nr("no");
      const recTxt = react.length === 0 ? "–" : nr("yes") === react.length ? "all back to normal" : [nr("yes") ? nr("yes") + " back to normal" : "", nr("partly") ? nr("partly") + " part of the way" : "", nr("no") ? nr("no") + " stay different" : "", nna ? nna + " with spikes (nothing to recover)" : ""].filter(Boolean).join(", ");
      const xr = [d.t_on - 300, Math.min(d.t0 + (d.v[O[0]].length - 1) * d.step, d.t_end + 600)];
      const H = Math.max(72, Math.min(150, Math.floor(760 / Math.max(1, react.length))));
      el.innerHTML = head + `<div class="ans3"><div><span>Which sensors?</span><b>${react.length} of 11 react</b><i>the experts named ${named.length ? named.join(", ") : "none of the 11"}</i></div>
          <div><span>What changes?</span><b>${esc(what)}</b></div><div><span>Do they recover?</span><b>${recTxt}</b></div></div>
        <div class="zrow"><div class="zl"><button class="play" id="play">▶ Play again</button></div><div class="zs" id="zs"></div></div>
        ${react.map((s) => `<div class="srow" id="r-${s}"><div class="sent"><div class="sn"><i style="background:${GRPC(s)}"></i><b>${s}</b> ${esc(NM[s])}${r.annotated.includes(s) ? ' <span class="named">named by the experts</span>' : ""}</div><div class="sa"></div><div class="sw2"></div><div class="sr2"></div></div><div class="sc" id="c-${s}"></div></div>`).join("")}
        <div class="quiet">${quiet.length ? `<b>No clear change:</b> ${quiet.map((s) => `${s} <span>${esc(NM[s])}</span>`).join(" · ")}` : "<b>Every one of the 11 sensors reacts.</b>"}</div>`;
      // zone strip aligned with the charts
      const zs = document.getElementById("zs"), W = zs.clientWidth, L = 70, Rr = 14, pw = W - L - Rr, X = (t) => L + pw * (t - xr[0]) / (xr[1] - xr[0]);
      const zones = [["before", xr[0], d.t_on, "#e2e8f0", "#475569"], ["during", d.t_on, r.e, "#f8d7d2", "#a32d2d"], ["after", r.e, xr[1], "#eef7f0", "#1e7b34"]];
      zs.innerHTML = `<svg width="${W}" height="30">${zones.map(([n, a, b, bg, fg]) => `<g class="zone" data-z="${n}"><rect x="${X(a).toFixed(1)}" y="4" width="${Math.max(2, X(b) - X(a)).toFixed(1)}" height="22" rx="5" fill="${bg}"/><text x="${((X(a) + X(b)) / 2).toFixed(1)}" y="19" text-anchor="middle" style="font-size:11.5px;font-weight:800;letter-spacing:.06em;fill:${fg}">${n.toUpperCase()}</text></g>`).join("")}<line id="zc" x1="0" x2="0" y1="2" y2="28" stroke="#1b1f24" stroke-width="2" style="display:none"/></svg>`;
      const sh = [{ a: xr[0], b: d.t_on, fill: "rgba(100,116,139,.12)" }];
      if (r.pb) sh.push({ a: r.pb, b: r.pe, fill: "rgba(230,126,34,.22)" });
      sh.push({ a: d.t_on, b: r.e, fill: "rgba(192,57,43,.08)" });
      const apis = react.map((s, i) => chart(document.getElementById("c-" + s), { xr, height: H + (i === react.length - 1 ? 22 : 0), noX: i < react.length - 1, left: L, series: [{ t0: d.t0, step: d.step, y: d.v[s], color: GRPC(s), width: 1.7 }], shade: sh, ylab: s,
        onhover: (t, ev) => { if (t == null) { hideTip(); return; } stop(); apis.forEach((a) => a.setCross(t)); setZone(t); showTip(ev, `<b>${clock(t)}</b><br>` + react.map((q) => { const j = Math.round((t - d.t0) / d.step); return `${q}: ${d.v[q][j] == null ? "–" : d.v[q][j].toFixed(dig(q) + 1)}${unit(q)}`; }).join("<br>")); } }));
      const sents = {}; react.forEach((s) => (sents[s] = sentence(s, r.sensors[s])));
      function setZone(t) { const zc = document.getElementById("zc"); zc.style.display = ""; zc.setAttribute("x1", X(t)); zc.setAttribute("x2", X(t));
        document.querySelectorAll(".zone").forEach((z) => z.classList.toggle("now", (z.dataset.z === "before" && t < d.t_on) || (z.dataset.z === "during" && t >= d.t_on && t <= r.e) || (z.dataset.z === "after" && t > r.e))); }
      function reveal(t, all) {
        react.forEach((s) => { const x = r.sensors[s], row = document.getElementById("r-" + s), st = sents[s];
          const on = all || x.delay == null || t >= d.t_on + x.delay;
          row.classList.toggle("lit", on && !all);
          row.querySelector(".sa").innerHTML = on ? st.a : `<span class="wait">waiting…</span>`;
          row.querySelector(".sw2").innerHTML = on ? st.when : "";
          const recOn = all || (x.recovery === "yes" && x.t_back && t >= x.t_back) || t >= xr[1] - 5;
          row.querySelector(".sr2").innerHTML = recOn ? st.rec : ""; });
      }
      function stop() { if (S.anim) { cancelAnimationFrame(S.anim); S.anim = null; reveal(0, true); } }
      function play() {
        stop(); const t0 = performance.now(), dur = 9000;
        const step = (now) => { const u = Math.min(1, (now - t0) / dur), t = xr[0] + u * (xr[1] - xr[0]);
          apis.forEach((a) => a.setCross(t)); setZone(t); reveal(t, false);
          if (u < 1) S.anim = requestAnimationFrame(step); else { S.anim = null; reveal(0, true); } };
        S.anim = requestAnimationFrame(step);
      }
      document.getElementById("play").addEventListener("click", play);
      play();
    }
    function bars() {
      const B = C.bars.slice().sort((a, b) => b.n - a.n), max = C.judged;
      document.getElementById("bars").innerHTML = `<div class="bars">${B.map((b) => `<div class="brow" data-s="${b.s}"><div class="bl"><i style="background:${GRPC(b.s)}"></i><b>${b.s}</b> ${esc(NM[b.s])}</div>
          <div class="bt"><div class="bg" style="width:0" data-w="${(100 * b.n / max).toFixed(1)}">${["yes", "partly", "no"].map((q) => b.rec[q] ? `<span class="q-${q}" style="flex:${b.rec[q]}"></span>` : "").join("")}${b.n - b.rec.yes - b.rec.partly - b.rec.no > 0 ? `<span class="q-na" style="flex:${b.n - b.rec.yes - b.rec.partly - b.rec.no}"></span>` : ""}</div></div>
          <div class="bn"><b>${b.n}</b> of ${max}<span>experts named it ${b.named}×</span></div></div>`).join("")}</div>
        <div class="blg"><span><i class="q-yes"></i>back to normal</span><span><i class="q-partly"></i>part of the way</span><span><i class="q-no"></i>stays different</span><span><i class="q-na"></i>spikes / rhythm (no recovery to judge)</span><span>out of the ${max} anomalies that can be judged</span></div>`;
      requestAnimationFrame(() => setTimeout(() => document.querySelectorAll(".bg").forEach((g) => (g.style.width = g.dataset.w + "%")), 60));
      document.querySelectorAll(".brow").forEach((row) => row.addEventListener("click", () => {
        document.querySelectorAll(".brow").forEach((x) => x.classList.toggle("on", x === row));
        const b = C.bars.find((x) => x.s === row.dataset.s);
        document.getElementById("blist").innerHTML = `<span class="small"><b>${b.s}</b> reacts in:</span> ` + b.keys.map((k) => `<span class="chip" data-k="${k}">${R[k].op} · ${R[k].id}</span>`).join("");
        document.querySelectorAll("#blist .chip").forEach((c) => c.addEventListener("click", () => {
          S.k = c.dataset.k; S.g = C.groups.findIndex((g) => g.keys.includes(S.k)); kinds(); chips(); story();
          document.querySelector(".qb").scrollIntoView({ behavior: "smooth" });
        }));
      }));
    }
    kinds(); chips(); story(); bars();
    window.__q1 = { S, story };
  }

  ({ recordings, single, explorer, ops, q1, q1b })[C.type]();
})();
