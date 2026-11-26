(function () {
  "use strict";
  const D = window.PLANT_DATA;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const svg = $("plant"), stage = $("stage"), panel = $("panel"), pop = $("pop");
  const TEMPS = ["T703", "T709", "T711", "T712", "T705"];
  const GRP_COLOR = { T: "#c0392b", F: "#2b6cb0", D: "#8e44ad", P: "#1e8449" };
  const GRP_OF = (s) => (s[0] === "T" ? "T" : s === "PY23" ? "P" : s.startsWith("PDI") ? "D" : "F");
  const pad = (x) => String(x).padStart(2, "0");
  const clock = (sec) => `${pad(Math.floor(sec / 3600))}:${pad(Math.floor((sec % 3600) / 60))}:${pad(sec % 60)}`;
  function fmt(s, v) {
    if (v === null || v === undefined || Number.isNaN(v)) return "–";
    if (s[0] === "T") return v.toFixed(2) + " °C";
    if (s === "PY23") return v.toFixed(1) + " mbar";
    if (s === "PDI702") return v.toFixed(2) + " mbar";
    return v.toFixed(3);
  }

  // ------------------------------------------------------------------ state
  const S = { view: "process", step: 0, op: D.default_op, live: null, pbox: null, auto: false, stepT: 0, anom: null, place: null };
  const LIVE = () => S.view === "live" || S.view === "anom";

  // ------------------------------------------------------------------ flows + pumps
  const flows = {};
  svg.querySelectorAll(".flow").forEach((el) => { flows[el.id] = { el, off: 0, speed: 1 }; });
  const pumps = { P701: $("imp-P701"), P702: $("imp-P702") };
  const pumpBucket = { P701: -1, P702: -1 };
  function setPump(id, r) {          // r = relative flow (1 = median)
    const b = r < 0.05 ? 0 : r < 0.6 ? 1 : r < 1.4 ? 2 : 3;
    if (b === pumpBucket[id]) return;
    pumpBucket[id] = b;
    const el = pumps[id];
    if (b === 0) { el.style.animationPlayState = "paused"; return; }
    el.style.animationPlayState = "running";
    el.style.animationDuration = ["", "2.6s", "1.4s", "0.8s"][b];
  }
  function resetFlows(speed) {
    for (const k in flows) { flows[k].speed = speed; flows[k].el.style.strokeWidth = ""; }
    setPump("P701", 1); setPump("P702", 1);
  }
  let last = null;
  function tick(ts) {
    if (last === null) last = ts;
    const dt = Math.min(0.1, (ts - last) / 1000);
    last = ts;
    for (const k in flows) { const f = flows[k]; f.off -= f.speed * dt * 32; f.el.style.strokeDashoffset = f.off.toFixed(1); }
    if (LIVE()) liveTick(dt);
    if (S.view === "process" && S.auto) autoTick(dt);
    if (S.view === "row") rowTick(dt);
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  // ------------------------------------------------------------------ colours
  const defaultStops = {};
  ["C001-b", "C001-t", "C002-b", "C002-t", "C003-b", "C003-t"].forEach((id) => (defaultStops[id] = $(id).getAttribute("stop-color")));
  const defaultLiquid = $("liquid").getAttribute("fill");
  function cmap(v, lo, hi) {
    let x = (v - lo) / Math.max(1e-9, hi - lo);
    x = Math.max(0, Math.min(1, x));
    const A = [43, 108, 176], B = [246, 195, 67], C = [192, 57, 43];
    const [p, q, u] = x < 0.5 ? [A, B, x / 0.5] : [B, C, (x - 0.5) / 0.5];
    return `rgb(${p.map((c, k) => Math.round(c + (q[k] - c) * u)).join(",")})`;
  }
  function colourColumn(t, lo, hi) {      // t: {T703:..} or null for illustrative colours
    const set = (id, col) => $(id).setAttribute("stop-color", col);
    if (!t) {
      for (const id in defaultStops) set(id, defaultStops[id]);
      $("liquid").setAttribute("fill", defaultLiquid);
      $("liquid-wave").style.fill = defaultLiquid;
      return;
    }
    const c = {}; TEMPS.forEach((s) => (c[s] = cmap(t[s], lo, hi)));
    set("C001-b", c.T709); set("C001-t", c.T711); set("C002-b", c.T711); set("C002-t", c.T712);
    set("C003-b", c.T712); set("C003-t", c.T705);
    $("liquid").setAttribute("fill", c.T703); $("liquid-wave").style.fill = c.T703;
  }
  function setTags(values) {   // values: {sensor: number} or null
    D.sensors.forEach((s) => { const el = $("val-" + s); if (el) el.textContent = values ? fmt(s, values[s]) : ""; });
  }

  // ------------------------------------------------------------------ focus
  function focus(ids, activeFlows, opts = {}) {
    svg.querySelectorAll(".hl,.pulse").forEach((e) => e.classList.remove("hl", "pulse"));
    svg.classList.toggle("show-wallheaters", !!(ids && ids.some((i) => /^eq-H70[2468]$/.test(i))));
    if (!ids) { svg.classList.remove("focus"); return; }
    svg.classList.toggle("focus", !opts.nodim);
    ids.forEach((id) => { const el = $(id); if (el) { el.classList.add("hl"); if (opts.pulse) el.classList.add("pulse"); } });
    if (activeFlows) for (const k in flows) { const on = activeFlows.includes(k); flows[k].speed = on ? 1 : 0; if (on) flows[k].el.classList.add("hl"); }
  }

  // ------------------------------------------------------------------ sparkline
  function spark(vals, w, h, opt = {}) {
    let lo = Infinity, hi = -Infinity;
    vals.forEach((v) => { if (v < lo) lo = v; if (v > hi) hi = v; });
    if (hi - lo < 1e-9) hi = lo + 1;
    const n = vals.length, stepDraw = Math.max(1, Math.floor(n / 260));
    const X = (i) => 2 + (w - 4) * i / Math.max(1, n - 1), Y = (v) => h - 14 - (h - 26) * (v - lo) / (hi - lo);
    let pts = [];
    for (let i = 0; i < n; i += stepDraw) pts.push(X(i).toFixed(1) + "," + Y(vals[i]).toFixed(1));
    let shade = "";
    (opt.shade || []).forEach(([a, b, c]) => { shade += `<rect x="${X(a).toFixed(1)}" y="10" width="${Math.max(1, X(b) - X(a)).toFixed(1)}" height="${h - 24}" fill="${c || "rgba(192,57,43,.14)"}"/>`; });
    const cur = opt.cursor != null ? `<line x1="${X(opt.cursor).toFixed(1)}" x2="${X(opt.cursor).toFixed(1)}" y1="8" y2="${h - 12}" stroke="#111" stroke-width="1"/>` : "";
    return `<svg viewBox="0 0 ${w} ${h}" width="100%"><text x="2" y="8" font-size="9.5" fill="#5b6472">${esc(opt.title || "")}</text>${shade}
      <polyline fill="none" stroke="${opt.color || "#1f4e79"}" stroke-width="1.3" points="${pts.join(" ")}"/>${cur}
      <text x="2" y="${h - 2}" font-size="9.5" fill="#5b6472">min ${esc(opt.fmt ? opt.fmt(lo) : lo.toFixed(2))}</text>
      <text x="${w - 2}" y="${h - 2}" font-size="9.5" fill="#5b6472" text-anchor="end">max ${esc(opt.fmt ? opt.fmt(hi) : hi.toFixed(2))}</text></svg>`;
  }

  // ------------------------------------------------------------------ pop-up
  const anomsByEq = {};
  D.anomalies.forEach((a) => a.eq.forEach((e) => (anomsByEq[e] = anomsByEq[e] || []).push(a)));
  function goLiveButtons(list) {
    return list.map((a) => `<div style="margin:6px 0"><b>${esc(a.op)} ${esc(a.short)}</b> &middot; ${esc(a.what)}
      <div class="small">${a.pb ? "Disturbance " + clock(a.pb) + "–" + clock(a.pe) + " · " : ""}annotated in ${esc(a.sensors)}</div>
      <button class="golive" data-key="${esc(a.key)}">&#9654; See how it happened</button></div>`).join("");
  }
  function sensorPop(s) {
    const i = D.info.sensors[s], g = GRP_OF(s);
    let body = `<div class="band" style="background:${GRP_COLOR[g]}"></div><div class="kicker">Sensor &middot; ${esc(i.group)} &middot; unit: ${esc(i.unit)}</div>
      <h3>${s}</h3><p><b>${esc(i.readme)}</b></p><p>${esc(i.plain)}</p><p class="small"><b>Where:</b> ${esc(i.location)}</p>`;
    if (LIVE() && S.live) {
      const L = S.live, R = D.runs[L.key], v = R.v[s];
      body += `<div class="kicker" style="margin-top:8px">Now (${clock(R.t0 + L.idx * R.step)})</div><div class="big">${fmt(s, v[L.idx])}</div>` +
        spark(v, 300, 80, { cursor: L.idx, title: "whole recording " + R.label, fmt: (x) => fmt(s, x), shade: R.events.filter((e) => e.kind !== "spike").map((e) => [Math.round((e.b - R.t0) / R.step), Math.round((e.e - R.t0) / R.step)]) });
    } else {
      const op = S.op, rows = Object.keys(i.ops).map((o) => `<tr class="${o === op ? "cur" : ""}"><td>${o}</td><td>${i.ops[o].med}</td><td>${i.ops[o].lo} to ${i.ops[o].hi}</td></tr>`).join("");
      body += `<h4 style="margin:8px 0 2px">Typical values in the normal runs</h4><table class="mini"><tr><th>OP</th><th>Median</th><th>1st–99th pct.</th></tr>${rows}</table>`;
      const nk = D.ops[op].normal_runs[0], R = D.runs[nk];
      body += `<div style="margin-top:8px">${spark(R.v[s], 300, 78, { title: "normal run of " + op + " (" + R.minutes + " min)", fmt: (x) => fmt(s, x), color: GRP_COLOR[g] })}</div>`;
    }
    const an = D.anomalies.filter((a) => a.sensor_list.includes(s));
    if (an.length) body += `<p class="small" style="margin-top:8px"><b>Named in the annotations of:</b> ${[...new Set(an.map((a) => a.op))].join(", ")}</p>`;
    return body;
  }
  function equipPop(id) {
    const e = D.info.equipment[id];
    if (!e) return "";
    let body = `<div class="band" style="background:#475569"></div><div class="kicker">${esc(e.kind)}</div><h3>${esc(e.name)}</h3><p>${e.text}</p>`;
    if (e.sensors && e.sensors.length) {
      let chips = e.sensors.map((s) => {
        let val = "";
        if (LIVE() && S.live) { const R = D.runs[S.live.key]; val = " " + fmt(s, R.v[s][S.live.idx]); }
        else if (S.view === "ops") val = " " + fmt(s, D.ops[S.op].med[s]);
        return `<span class="chip" data-s="${s}">${s}${esc(val)}</span>`;
      }).join("");
      body += `<h4 style="margin:8px 0 2px">Sensors here (click)</h4><div class="chips">${chips}</div>`;
    }
    const an = anomsByEq["eq-" + id];
    if (an && an.length) body += `<h4 style="margin:10px 0 2px">Anomalies at this place</h4>${goLiveButtons(an)}`;
    return body;
  }
  function openPop(kind, id, anchor) {
    pop.innerHTML = `<button class="close" aria-label="Close">&times;</button>` + (kind === "sen" ? sensorPop(id) : equipPop(id));
    svg.querySelectorAll(".selected").forEach((e) => e.classList.remove("selected"));
    if (anchor) anchor.classList.add("selected");
    pop.classList.add("open");
    pop.scrollTop = 0;
    const sr = stage.getBoundingClientRect(), ar = anchor.getBoundingClientRect();
    const pw = pop.offsetWidth, ph = pop.offsetHeight;
    let left = ar.right - sr.left + 12;
    if (left + pw > sr.width - 6) left = ar.left - sr.left - pw - 12;
    if (left < 6) left = Math.max(6, Math.min(sr.width - pw - 6, ar.left - sr.left));
    let top = ar.top - sr.top - 10;
    top = Math.max(6, Math.min(top, sr.height - ph - 6));
    pop.style.left = left + "px"; pop.style.top = top + "px";
    pop.querySelector(".close").addEventListener("click", closePop);
    pop.querySelectorAll(".chip[data-s]").forEach((c) => c.addEventListener("click", (ev) => { ev.stopPropagation(); openPop("sen", c.dataset.s, $("sen-" + c.dataset.s)); }));
    bindGoLive(pop);
    pop.dataset.kind = kind; pop.dataset.id = id;
  }
  function closePop() {
    pop.classList.remove("open");
    pop.dataset.kind = "";
    svg.querySelectorAll(".selected").forEach((e) => e.classList.remove("selected"));
  }
  function bindGoLive(root) {
    root.querySelectorAll(".golive").forEach((b) => b.addEventListener("click", (ev) => {
      ev.stopPropagation(); closePop();
      if (b.dataset.key) { openAnomaly(b.dataset.key); return; }
      S.pending = { run: b.dataset.run, t: +b.dataset.t, trend: b.dataset.s || null };
      setView("live");
    }));
  }
  svg.querySelectorAll(".eq, .sen").forEach((g) => g.addEventListener("click", (ev) => {
    ev.stopPropagation();
    openPop(g.classList.contains("sen") ? "sen" : "eq", g.dataset.id, g);
  }));
  stage.addEventListener("click", (ev) => { if (!pop.contains(ev.target)) closePop(); });
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") closePop(); });

  // ------------------------------------------------------------------ modes
  document.querySelectorAll(".mode").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
  const cap = $("cap");
  function setCaption(html) { cap.innerHTML = html || ""; cap.classList.toggle("show", !!html); }
  function setView(v) {
    S.view = v;
    document.querySelectorAll(".mode").forEach((t) => t.classList.toggle("on", t.dataset.view === v));
    closePop();
    if (S.live) S.live.playing = false;
    if (v !== "process") S.auto = false;
    resetFlows(1); colourColumn(null); setTags(null); focus(null); setTracers([]); setCaption("");
    svg.classList.toggle("show-marks", v === "anom");
    panel.scrollTop = 0;
    ({ process: viewProcess, ops: viewOps, anom: viewAnom, live: viewLive, row: viewRow })[v]();
  }

  // ------------------------------------------------------------------ travelling dots on the active lines
  const NS = "http://www.w3.org/2000/svg";
  const tracerLayer = document.createElementNS(NS, "g"); svg.appendChild(tracerLayer);
  function setTracers(ids) {
    tracerLayer.innerHTML = "";
    ids.forEach((id, k) => {
      const f = flows[id]; if (!f) return;
      const len = f.el.getTotalLength(), dur = Math.max(1.6, len / 110);
      for (let n = 0; n < 2; n++) {
        const c = document.createElementNS(NS, "circle");
        c.setAttribute("r", "4.5"); c.setAttribute("class", "tracer"); c.setAttribute("fill", f.el.getAttribute("stroke"));
        const m = document.createElementNS(NS, "animateMotion");
        m.setAttribute("dur", dur.toFixed(2) + "s"); m.setAttribute("repeatCount", "indefinite"); m.setAttribute("begin", (-n * dur / 2 - k * 0.3).toFixed(2) + "s");
        const mp = document.createElementNS(NS, "mpath"); mp.setAttributeNS("http://www.w3.org/1999/xlink", "href", "#" + id); mp.setAttribute("href", "#" + id);
        m.appendChild(mp); c.appendChild(m); tracerLayer.appendChild(c);
      }
    });
  }

  // ================================================================== 1 THE PROCESS (animated, step by step)
  const STEP_S = 9;
  const CAPS = ["The whole plant at work", "Heat: the liquid boils in the reboiler", "Rise: vapour climbs through the column",
    "Condense: cooling water turns the vapour back into liquid", "Collect and split: reflux back to the column, distillate to the receiver",
    "Vacuum: the pump keeps the pressure low"];
  function viewProcess() {
    const st = D.steps[S.step];
    focus(st.highlight, st.highlight ? st.flows : null);
    setTracers(S.step === 0 ? ["flow-column", "flow-vapour", "flow-condensate", "flow-reflux", "flow-distillate", "flow-cool-in"] : st.flows);
    setCaption(S.step === 0 ? "" : `<span class="n">${S.step}/${D.steps.length - 1}</span>${esc(CAPS[S.step])}`);
    const list = D.steps.map((x, i) => i === 0 ? "" : `<div class="stp ${i === S.step ? "on" : ""} ${i < S.step ? "done" : ""}" data-i="${i}"><span class="num">${i}</span>${esc(x.short)}${i === S.step && S.auto ? `<i class="bar" style="animation-duration:${STEP_S}s"></i>` : ""}</div>`).join("");
    panel.innerHTML = `<div class="stplist">${list}</div>
      <div class="ctrls"><button class="btn ghost" id="prev" ${S.step <= 1 ? "disabled" : ""}>&larr;</button>
        <button class="btn big" id="auto">${S.auto ? "&#10074;&#10074; Pause" : S.step === 0 ? "&#9654; Play the process" : "&#9654; Play"}</button>
        <button class="btn ghost" id="next" ${S.step === D.steps.length - 1 ? "disabled" : ""}>&rarr;</button></div>
      <h3>${esc(st.title)}</h3>${st.text}
      ${st.data ? `<div class="datanote"><b>In the data</b><br>${st.data}</div>` : ""}`;
    panel.querySelectorAll(".stp").forEach((b) => b.addEventListener("click", () => { S.step = +b.dataset.i; S.stepT = 0; viewProcess(); }));
    $("prev").addEventListener("click", () => { if (S.step > 1) { S.step--; S.stepT = 0; viewProcess(); } });
    $("next").addEventListener("click", () => { if (S.step < D.steps.length - 1) { S.step++; S.stepT = 0; viewProcess(); } });
    $("auto").addEventListener("click", () => {
      S.auto = !S.auto;
      if (S.auto && (S.step === 0 || S.step === D.steps.length - 1)) S.step = 1;
      S.stepT = 0; viewProcess();
    });
  }
  function autoTick(dt) {
    S.stepT += dt;
    if (S.stepT < STEP_S) return;
    S.stepT = 0;
    if (S.step < D.steps.length - 1) S.step++; else { S.auto = false; S.step = 0; }
    closePop(); viewProcess();
  }

  // ================================================================== OPERATING POINTS
  function viewOps() {
    const O = D.ops[S.op];
    setTags(O.med);
    colourColumn(O.med, D.op_scale[0], D.op_scale[1]);
    setCaption(`<span class="n">${S.op}</span>typical values of its normal run${O.normal_runs.length > 1 ? "s" : ""}`);
    const maxP = Math.max(...D.op_order.map((o) => D.ops[o].med.PY23)), maxT = Math.max(...D.op_order.map((o) => D.ops[o].med.T705));
    const bars = (key, unit, digits, maxV) => D.op_order.map((o) => {
      const v = D.ops[o].med[key];
      return `<div class="row ${o === S.op ? "on" : ""}" data-op="${o}"><span class="lab">${o}</span><span class="bar" style="width:${(130 * v / maxV).toFixed(0)}px"></span><span class="num">${v.toFixed(digits)} ${unit}</span></div>`;
    }).join("");
    panel.innerHTML = `<h3>Six settings of the same plant</h3>
      <p>An operating point is one fixed combination of plant settings, such as pressure and heat input (README). Choose one: the tags show its <b>typical (median) values</b> from the normal run(s), and the column is coloured by temperature.</p>
      <div class="chips">${D.op_order.map((o) => `<span class="chip ${o === S.op ? "on" : ""}" data-op="${o}">${o}</span>`).join("")}</div>
      <h4>Pressure PY23 (median)</h4><div class="bars">${bars("PY23", "mbar", 0, maxP)}</div>
      <h4>Column-top temperature T705 (median)</h4><div class="bars">${bars("T705", "°C", 1, maxT)}</div>
      <div class="datanote">${O.note}</div>
      <div class="ctrl small" style="margin-top:10px"><span>${D.op_scale[0]} °C</span><div class="scale" style="flex:1"></div><span>${D.op_scale[1]} °C</span></div>
      <p class="small">Same colour scale for all operating points, so colours can be compared. Lower pressure means lower boiling temperatures, so a cooler column (background physics).</p>`;
    panel.querySelectorAll("[data-op]").forEach((c) => c.addEventListener("click", () => { S.op = c.dataset.op; viewOps(); }));
  }

  // ================================================================== FROM THE PLANT TO NUMBERS (used on the dataset page)
  const NAMES = D.rowdemo ? D.rowdemo.names : {};
  function viewRow() {
    const R = D.rowdemo, n = R.time.length;
    S.op = R.op;
    if (!S.row) {
      let lo = Infinity, hi = -Infinity;
      TEMPS.forEach((s) => R.v[s].forEach((v) => { if (v < lo) lo = v; if (v > hi) hi = v; }));
      S.row = { i: 0, playing: true, acc: 0, speed: 2, lo: lo - 1, hi: hi + 1 };
    }
    const f = R.focus;
    panel.innerHTML = `<h3>Every second becomes one row</h3>
      <p>The plant's computer reads all 11 sensors <b>once per second</b> and writes them as one new row of the file. Here the drawing replays <b>${esc(R.file)}</b> row by row: the clock is the file's <b>Time</b> column.</p>
      ${f ? `<p>Watch <b>${f}</b> (${esc(NAMES[f])}): the experts saw this anomaly in it.</p>` : ""}
      <div class="ctrl"><button class="btn" id="rplay"></button><button class="btn ghost" id="rrestart" title="Back to the start">&#10226; Restart</button><span class="clock" id="rclk"></span>
        <select id="rspd">${[[1, "real time"], [2, "2× faster"], [8, "8× faster"], [30, "30× faster"]].map(([v, t]) => `<option value="${v}" ${v === S.row.speed ? "selected" : ""}>${t}</option>`).join("")}</select></div>
      <input type="range" id="rprog" min="0" max="${n - 1}" step="1" value="${S.row.i}" aria-label="Position in the replay">
      <div class="small" id="rinfo"></div>
      <div id="rban" class="banner"></div>${R.marks ? `<div class="small" id="rchg" style="margin:4px 0"></div>` : ""}
      <h4>The row of this second</h4><table class="mini rowcard" id="rcard"></table>`;
    $("rplay").addEventListener("click", () => { if (S.row.i >= n - 1) S.row.i = 0; S.row.playing = !S.row.playing; renderRow(); });
    $("rrestart").addEventListener("click", () => { S.row.i = 0; S.row.acc = 0; S.row.playing = true; renderRow(); });
    $("rspd").addEventListener("change", (e) => { S.row.speed = +e.target.value; });
    $("rprog").addEventListener("input", (e) => { S.row.i = +e.target.value; renderRow(); });
    renderRow();
  }
  function renderRow() {
    const R = D.rowdemo, Q = S.row, i = Q.i, n = R.time.length, t = R.t0 + i, vals = {};
    D.sensors.forEach((s) => (vals[s] = R.v[s][i]));
    setTags(vals); colourColumn(vals, Q.lo, Q.hi);
    setPump("P701", setFlow("flow-reflux", vals.FT704, R.med.FT704));
    setPump("P702", setFlow("flow-distillate", vals.FT703, R.med.FT703));
    setFlow("flow-cool-in", vals.FYI702, R.med.FYI702); setFlow("flow-cool-out", vals.FYI702, R.med.FYI702);
    $("rplay").innerHTML = Q.playing ? "&#10074;&#10074; Pause" : "&#9654; Play";
    $("rclk").textContent = R.time[i];
    $("rprog").value = i;
    $("rinfo").textContent = `Replaying ${R.time[0]} → ${R.time[n - 1]} · now at ${R.time[i]} (line ${(R.first_line + i).toLocaleString("en")} of the file)`;
    const pert = R.events.filter((e) => e.k === "event" && e.pb != null && t >= e.pb && t <= e.pe);
    const mark = R.events.filter((e) => e.k === "event" && t >= e.b && t <= e.e);
    const spk = R.events.filter((e) => e.k === "spike" && t >= e.b && t <= e.e);
    const b = $("rban");
    if (pert.length) { b.className = "banner pert"; b.innerHTML = `<b>Disturbance being applied (${esc(pert[0].id)}):</b> ${esc(pert[0].what)}`; }
    else if (mark.length) { b.className = "banner alert"; b.innerHTML = `<b>Marked anomalous by the experts (${esc(mark[0].id)})</b>`; }
    else if (spk.length) { b.className = "banner alert"; b.innerHTML = `<b>A short marked spike (${esc(spk[0].id)}):</b> leaking sample valve`; }
    else { b.className = "banner"; b.textContent = R.kind === "normal" ? "Normal recording: nothing was disturbed." : "No annotated anomaly at this moment."; }
    const mk = (s, k) => (R.marks ? R.marks[s][k] : 0), arrow = (m) => (m > 0 ? " ↑" : m < 0 ? " ↓" : "");
    if (R.marks) {
      D.sensors.forEach((s) => { const g = $("sen-" + s); if (g) { g.classList.toggle("mk-up", mk(s, i) > 0); g.classList.toggle("mk-dn", mk(s, i) < 0); } });
      const ch = R.order.filter((s) => mk(s, i));
      $("rchg").innerHTML = ch.length ? `<b>Changed now</b> (compared with before the disturbance): ${ch.map((s) => `<span class="${mk(s, i) > 0 ? "up" : "dn"}">${s}${arrow(mk(s, i))}</span>`).join(" ")}` : (t < R.t_on ? "Before the disturbance: this is the reference." : "No sensor is clearly away from its level before the disturbance.");
    }
    $("rcard").innerHTML = R.order.map((s) => `<tr class="${s === R.focus ? "cur" : ""}"><td><b>${s}</b> <span class="small">${esc(NAMES[s])}</span></td><td class="${mk(s, i) > 0 ? "up" : mk(s, i) < 0 ? "dn" : ""}">${R.v[s][i]}${arrow(mk(s, i))}</td></tr>`).join("");
    const rows = []; for (let k = Math.max(0, i - 5); k <= i; k++) rows.push(k);
    const cols = ["line", "Time"].concat(R.order), w = cols.map((c) => Math.max(c.length, 8));
    $("rows").innerHTML = `<div class="fhead">${esc(R.file)} &middot; ${R.rows.toLocaleString("en")} rows, one per second &middot; the window shows the last rows read, newest at the bottom; first column = line number in the file</div><pre>` +
      `<span class="h">${cols.map((c, k) => c.padEnd(w[k])).join(" ")}</span>\n` +
      rows.map((k) => `<span class="${k === i ? "new" : ""}">${String(R.first_line + k).padEnd(w[0])} ${R.time[k].padEnd(w[1])} ${R.order.map((s, j) => { const m = mk(s, k), txt = (String(R.v[s][k]) + arrow(m)).padEnd(w[j + 2]); return m ? `<b class="${m > 0 ? "up" : "dn"}">${txt}</b>` : txt; }).join(" ")}</span>`).join("\n") + `</pre>`;
  }
  function rowTick(dt) {
    const Q = S.row; if (!Q || !Q.playing) return;
    Q.acc += dt * Q.speed;
    if (Q.acc >= 1) { const k = Math.floor(Q.acc); Q.acc -= k; Q.i = Math.min(D.rowdemo.time.length - 1, Q.i + k); if (Q.i >= D.rowdemo.time.length - 1) Q.playing = false; renderRow(); }
  }

  // ================================================================== 2 WHERE ANOMALIES HAPPENED
  const AN = {}; D.anomalies.forEach((a) => (AN[a.key] = a));
  const marksLayer = document.createElementNS(NS, "g"); marksLayer.setAttribute("class", "marks"); svg.appendChild(marksLayer);
  const places = [...new Set(D.anomaly_groups.map((g) => g.eq))];
  function drawMarks() {
    marksLayer.innerHTML = "";
    places.forEach((eq) => {
      const el = $(eq); if (!el) return;
      const bb = el.getBBox(), n = D.anomaly_groups.filter((g) => g.eq === eq).reduce((k, g) => k + g.items.length + g.side.length, 0);
      const g = document.createElementNS(NS, "g");
      g.setAttribute("class", "amark"); g.dataset.eq = eq;
      g.setAttribute("transform", `translate(${(bb.x + bb.width + (eq === "eq-H701" ? -8 : 2)).toFixed(1)},${(bb.y + (eq === "eq-H701" ? 4 : -2)).toFixed(1)})`);
      g.innerHTML = `<circle class="ring" r="13"/><circle class="dot" r="10"/><text y="4">${n}</text>`;
      g.addEventListener("click", (ev) => { ev.stopPropagation(); S.place = eq; S.anom = null; if (S.view !== "anom") setView("anom"); else viewAnom(); });
      marksLayer.appendChild(g);
    });
  }
  function viewAnom() {
    marksLayer.querySelectorAll(".amark").forEach((m) => m.classList.toggle("on", m.dataset.eq === S.place));
    if (S.anom) return anomalyDetail();
    focus(S.place ? [S.place] : places, [], { pulse: true });
    setCaption(S.place ? "" : `<span class="n">!</span>The red markers show where the process was disturbed. Click one.`);
    const groups = D.anomaly_groups.filter((g) => !S.place || g.eq === S.place);
    panel.innerHTML = `${S.place ? `<div class="crumbs"><span class="lk" id="all">&larr; all places</span></div>` : `<h3>Where the process was disturbed</h3>
      <p>In the six anomalous runs the operators disturbed the plant on purpose: they opened valves, injected gas, took samples, switched off the cooling or changed settings. Experts then marked when the process was anomalous.</p>`}
      ${groups.map((g) => `<div class="acard"><div class="t">${esc(g.title)}</div><div class="w">${esc(g.where)}</div><p>${esc(g.text)}</p>
        <div class="items">${g.items.map((it) => `<span class="aitem" data-key="${esc(it.key)}">${esc(it.label)}</span>`).join("")}
        ${g.side.length ? `<div class="w" style="margin-top:4px">side effects observed afterwards:</div>${g.side.map((k) => `<span class="aitem side" data-key="${esc(k)}">${esc(AN[k].op + " " + AN[k].id.slice(-4))}</span>`).join("")}` : ""}</div></div>`).join("")}
      <p class="small">Click an anomaly to see what was done, when, and to replay the real data of that moment on the drawing.</p>`;
    if ($("all")) $("all").addEventListener("click", () => { S.place = null; viewAnom(); });
    panel.querySelectorAll(".aitem").forEach((b) => b.addEventListener("click", () => openAnomaly(b.dataset.key)));
  }
  function openAnomaly(key) {
    S.anom = key; const g = D.anomaly_groups.find((x) => x.items.some((it) => it.key === key) || x.side.includes(key));
    S.place = g ? g.eq : null;
    if (S.view !== "anom") setView("anom"); else viewAnom();
  }
  function anomalyDetail() {
    const a = AN[S.anom], R = D.runs[a.run], g = D.anomaly_groups.find((x) => x.eq === S.place);
    focus((a.eq.length ? a.eq : [S.place]).concat(["sen-" + a.trend]), null, { pulse: true, nodim: true });
    const sp = a.cat === "recurrent" || a.cat === "permanent";
    const t0 = sp ? a.b - 60 : Math.min(a.b, a.pb == null ? a.b : a.pb) - 180;
    const t1 = sp ? t0 + 2400 : Math.max(a.e, a.pe == null ? a.e : a.pe) + 300;
    const i0 = Math.max(0, Math.round((t0 - R.t0) / R.step)), i1 = Math.min(R.n - 1, Math.round((t1 - R.t0) / R.step));
    let tmin = Infinity, tmax = -Infinity;
    TEMPS.forEach((s) => { tmin = Math.min(tmin, R.st[s].min); tmax = Math.max(tmax, R.st[s].max); });
    S.live = { key: a.run, idx: i0, playing: false, acc: 0, speedIdx: 1, trend: a.trend, last: -1, stopAt: i1, start: i0, tmin, tmax };
    const L = S.live, s = a.trend, rel = (t) => Math.round((t - R.t0) / R.step) - i0;
    const shade = [];
    if (a.pb != null) shade.push([rel(a.pb), rel(a.pe), "rgba(230,126,34,.28)"]);
    R.events.filter((e) => (e.kind === "spike" ? a.cat === "recurrent" : true) && e.e >= t0 && e.b <= t1 && (e.short.startsWith(a.id.slice(-4)))).forEach((e) => shade.push([rel(e.b), rel(e.e), "rgba(192,57,43,.18)"]));
    if (a.cat === "permanent") shade.push([0, i1 - i0, "rgba(192,57,43,.12)"]);
    L.trendHtml = (cur) => spark(R.v[s].slice(i0, i1 + 1), 300, 104, { cursor: cur - i0, shade, fmt: (x) => fmt(s, x), color: GRP_COLOR[GRP_OF(s)], title: `${s} · ${clock(R.t0 + i0 * R.step)} – ${clock(R.t0 + i1 * R.step)}` });
    const when = a.cat === "permanent" ? `the whole recording (${a.first} – ${a.last})` : a.n > 1 ? `${a.n} short intervals between ${a.first} and ${a.last}` : `${a.first} – ${a.last}`;
    panel.innerHTML = `<div class="crumbs"><span class="lk" id="back">&larr; ${esc(g ? g.title : "all places")}</span></div>
      <h3>${esc(a.op)} &middot; anomaly ${esc(a.id.slice(-4))}</h3>
      <div class="tags"><span class="tg">${a.cat || "no category"}</span><span class="tg ${a.cls === "Anomaly" ? "obs" : ""}">${a.cls === "Anomaly" ? "observed side effect" : "deliberate disturbance"}</span></div>
      <dl class="facts"><dt>What was done</dt><dd>${a.cls === "Anomaly" ? "Nothing documented: the experts observed this effect after the disturbance A001." : esc(a.what)}</dd>
        <dt>Where</dt><dd>${a.cls === "Anomaly" ? "not documented" : esc(a.equipment && a.equipment !== "None" ? a.equipment : g ? g.where : "–")}</dd>
        <dt>When</dt><dd>${a.pb != null ? `<span class="sw" style="background:#e67e22"></span>disturbance ${clock(a.pb)} – ${clock(a.pe)}<br>` : ""}<span class="sw" style="background:#c0392b"></span>marked anomalous: ${when}</dd>
        ${a.effect ? `<dt>What the experts saw</dt><dd>${esc(a.effect)} <span class="small">(in ${esc(a.sensors)})</span></dd>` : ""}</dl>
      <h4>Replay what happened <span class="small">real data, 60&times; faster</span></h4>
      <div class="ctrl"><button class="btn" id="play">&#9654; Replay</button><span class="clock" id="clock">--:--:--</span></div>
      <input type="range" id="slider" min="${i0}" max="${i1}" value="${i0}" step="1" aria-label="Time">
      <div id="banner" class="banner"></div><div id="trend"></div>
      <p class="small">The drawing shows the measured values of this moment: temperatures colour the column, the reflux, distillate and cooling-water lines move with the measured flows.</p>`;
    $("back").addEventListener("click", () => { S.anom = null; S.live.playing = false; resetFlows(1); colourColumn(null); setTags(null); viewAnom(); });
    $("play").addEventListener("click", () => { if (L.idx >= L.stopAt) L.idx = L.start; L.playing = !L.playing; $("play").innerHTML = L.playing ? "&#10074;&#10074; Pause" : "&#9654; Replay"; });
    $("slider").addEventListener("input", (e) => { L.idx = +e.target.value; renderLive(true); });
    setCaption(`<span class="n">!</span>${esc(a.op)} ${esc(a.id.slice(-4))}: ${esc(g ? g.title : "")}`);
    renderLive(true);
  }

  // ================================================================== LIVE
  function viewLive() {
    if (S.pending) { const p = S.pending; S.pending = null; loadRun(p.run, p.t, p.trend); }
    else if (!S.live || S.live.stopAt != null) loadRun(D.default_run, null); else buildLivePanel();
  }
  function loadRun(key, tSeek, trend) {
    const R = D.runs[key];
    let idx = 0;
    if (tSeek != null) idx = Math.max(0, Math.min(R.n - 1, Math.round((tSeek - R.t0) / R.step)));
    S.live = { key, idx, stopAt: null, playing: false, acc: 0, speedIdx: S.live ? S.live.speedIdx : 2, trend: trend || (R.op === "OP31" ? "FYI702" : (S.live ? S.live.trend : "PY23")), last: -1 };
    buildLivePanel();
  }
  function buildLivePanel() {
    const L = S.live, R = D.runs[L.key];
    let tmin = Infinity, tmax = -Infinity;
    TEMPS.forEach((s) => { tmin = Math.min(tmin, R.st[s].min); tmax = Math.max(tmax, R.st[s].max); });
    L.tmin = tmin; L.tmax = tmax;
    const evs = R.events.filter((e) => e.kind !== "spike");
    panel.scrollTop = 0;
    panel.innerHTML = `
      <div class="kicker">Replay of real recorded data</div>
      <select id="runsel" style="width:100%;margin:2px 0 6px">${D.run_order.map((k) => `<option value="${esc(k)}" ${k === L.key ? "selected" : ""}>${esc(D.runs[k].label)}</option>`).join("")}</select>
      <div class="ctrl"><span class="clock" id="clock">--:--:--</span><span class="small" id="elapsed"></span></div>
      <div class="ctrl" style="margin-top:6px"><button class="btn" id="play">&#9654; Play</button>
        <label class="small">Speed <select id="speed">${D.speeds.map((s, i) => `<option value="${i}" ${i === L.speedIdx ? "selected" : ""}>${s * R.step}&times; real time</option>`).join("")}</select></label></div>
      <input type="range" id="slider" min="0" max="${R.n - 1}" value="${L.idx}" step="1" aria-label="Time in the recording">
      <div class="track" id="track"></div>
      <div id="banner" class="banner"></div>
      ${evs.length ? `<h4>Jump to an annotated event</h4><div class="chips">${evs.map((e, k) => `<span class="chip" data-ev="${k}" title="${esc(e.what)}">${esc(e.short)}</span>`).join("")}</div>` : ""}
      <h4>Temperature profile up the column</h4><svg id="profile" viewBox="0 0 300 188" width="100%"></svg>
      <div class="ctrl small"><span>${tmin.toFixed(1)} °C</span><div class="scale" style="flex:1"></div><span>${tmax.toFixed(1)} °C</span></div>
      <h4>Whole recording of <select id="tsel">${D.sensors.map((s) => `<option ${s === L.trend ? "selected" : ""}>${s}</option>`).join("")}</select></h4>
      <div id="trend"></div>
      <p class="small">Click a sensor or part in the drawing for details. Reflux, distillate and cooling-water lines move with the measured flows; vapour, condensate and vacuum lines are not measured and move at a constant speed. Values every ${R.step} s.</p>`;
    // track
    const span = Math.max(1, (R.n - 1) * R.step), pct = (s) => (100 * (s - R.t0) / span).toFixed(3) + "%", wid = (a, b) => (100 * Math.max(R.step, b - a) / span).toFixed(3) + "%";
    let tr = "";
    R.events.forEach((e) => {
      if (e.kind === "spike") tr += `<span style="left:${pct(e.b)};width:${wid(e.b, e.e)};background:rgba(142,68,173,.55)"></span>`;
      else { if (e.pb != null) tr += `<span style="left:${pct(e.pb)};width:${wid(e.pb, e.pe)};background:rgba(230,126,34,.6)"></span>`;
        tr += `<span style="left:${pct(e.b)};width:${wid(e.b, e.e)};background:rgba(192,57,43,.45)"></span>`; }
    });
    $("track").innerHTML = tr;
    $("track").title = "red = annotated anomaly, orange = disturbance applied, purple = short spike intervals";
    // profile scaffold
    const PY = { T703: 162, T709: 128, T711: 94, T712: 60, T705: 26 };
    const PL = { T703: "T703 reboiler", T709: "T709 below C001", T711: "T711 C001/C002", T712: "T712 C002/C003", T705: "T705 column top" };
    L.px = (v) => 118 + 172 * (v - tmin) / Math.max(1e-9, tmax - tmin); L.PY = PY;
    let pg = "";
    TEMPS.forEach((s) => { pg += `<line x1="118" x2="290" y1="${PY[s]}" y2="${PY[s]}" stroke="#eef0f3"/><text x="2" y="${PY[s] + 4}" font-size="10.5" fill="#5b6472">${PL[s]}</text>`; });
    pg += `<polyline fill="none" stroke="#9aa3ae" stroke-dasharray="4 3" stroke-width="1.5" points="${TEMPS.map((s) => L.px(R.st[s].med).toFixed(1) + "," + PY[s]).join(" ")}"/>`;
    pg += `<polyline id="pnow" fill="none" stroke="#c0392b" stroke-width="2.4"/>` + TEMPS.map((s) => `<circle id="pd-${s}" r="4.2" fill="#c0392b"/>`).join("");
    pg += `<text x="2" y="184" font-size="10" fill="#5b6472">grey dashed: median of this recording · red: now</text>`;
    $("profile").innerHTML = pg;
    // events
    $("runsel").addEventListener("change", (e) => loadRun(e.target.value, null));
    $("play").addEventListener("click", () => { if (L.idx >= R.n - 1) L.idx = 0; L.playing = !L.playing; $("play").innerHTML = L.playing ? "&#10074;&#10074; Pause" : "&#9654; Play"; });
    $("speed").addEventListener("change", (e) => { L.speedIdx = +e.target.value; });
    $("slider").addEventListener("input", (e) => { L.idx = +e.target.value; renderLive(true); });
    $("tsel").addEventListener("change", (e) => { L.trend = e.target.value; drawTrend(); renderLive(true); });
    panel.querySelectorAll(".chip[data-ev]").forEach((c) => c.addEventListener("click", () => {
      const e = evs[+c.dataset.ev], start = Math.min(e.b, e.pb == null ? e.b : e.pb) - 120;
      L.idx = Math.max(0, Math.round((start - R.t0) / R.step)); renderLive(true);
    }));
    drawTrend();
    renderLive(true);
  }
  function drawTrend() {
    const L = S.live, R = D.runs[L.key], s = L.trend;
    const shade = R.events.filter((e) => e.kind !== "spike").map((e) => [Math.round((e.b - R.t0) / R.step), Math.round((e.e - R.t0) / R.step)]);
    L.trendHtml = (cur) => spark(R.v[s], 300, 96, { cursor: cur, shade, fmt: (x) => fmt(s, x), title: `${clock(R.t0)} – ${clock(R.t0 + (R.n - 1) * R.step)}` });
  }
  function setFlow(id, value, ref) {
    const f = flows[id]; if (!f) return 0;
    const r = ref > 1e-9 ? Math.max(0, value) / ref : 0;
    f.speed = Math.min(2.5, r);
    f.el.style.strokeWidth = (1.4 + 2.2 * Math.min(2, r)).toFixed(2);
    return r;
  }
  function renderLive(force) {
    const L = S.live, R = D.runs[L.key], i = L.idx;
    if (i === L.last && !force) return;
    L.last = i;
    const t = R.t0 + i * R.step, vals = {};
    D.sensors.forEach((s) => (vals[s] = R.v[s][i]));
    $("clock").textContent = clock(t);
    if ($("elapsed")) $("elapsed").textContent = `minute ${((t - R.t0) / 60).toFixed(1)} of ${(((R.n - 1) * R.step) / 60).toFixed(1)}`;
    $("slider").value = i;
    setTags(vals);
    colourColumn(vals, L.tmin, L.tmax);
    setPump("P701", setFlow("flow-reflux", vals.FT704, R.st.FT704.med));
    setPump("P702", setFlow("flow-distillate", vals.FT703, R.st.FT703.med));
    setFlow("flow-cool-in", vals.FYI702, R.st.FYI702.med); setFlow("flow-cool-out", vals.FYI702, R.st.FYI702.med);
    if ($("pnow")) { $("pnow").setAttribute("points", TEMPS.map((s) => L.px(vals[s]).toFixed(1) + "," + L.PY[s]).join(" "));
      TEMPS.forEach((s) => { const d = $("pd-" + s); d.setAttribute("cx", L.px(vals[s]).toFixed(1)); d.setAttribute("cy", L.PY[s]); }); }
    $("trend").innerHTML = L.trendHtml(i);
    const act = R.events.filter((e) => e.kind !== "spike" && t >= e.b && t <= e.e);
    const pert = R.events.filter((e) => e.kind !== "spike" && e.pb != null && t >= e.pb && t <= e.pe);
    const spk = R.events.some((e) => e.kind === "spike" && t >= e.b && t <= e.e);
    const b = $("banner");
    if (act.length || pert.length) {
      const names = [...new Set([...pert, ...act])].map((e) => `<b>${esc(e.short)}</b>: ${esc(e.what)}`).join("<br>");
      b.className = act.length ? "banner alert" : "banner pert";
      b.innerHTML = (pert.length ? "Disturbance being applied. " : "") + (act.length ? "Inside an annotated anomaly interval." : "") + "<br>" + names;
    } else if (spk) { b.className = "banner pert"; b.innerHTML = "Inside a short annotated spike interval (leaking sample valve; see FT703 / FT704)."; }
    else { b.className = "banner"; b.innerHTML = R.type === "normal" ? "Normal run: no disturbances were applied in this recording." : "No annotated anomaly at this moment."; }
    if (pop.classList.contains("open") && pop.dataset.kind === "sen" && force !== "nopop") {
      const big = pop.querySelector(".big"); if (big) big.textContent = fmt(pop.dataset.id, vals[pop.dataset.id]);
    }
  }
  function liveTick(dt) {
    const L = S.live; if (!L || !L.playing) return;
    const R = D.runs[L.key];
    L.acc += dt * D.speeds[L.speedIdx];
    const end = L.stopAt != null ? L.stopAt : R.n - 1;
    if (L.acc >= 1) { const k = Math.floor(L.acc); L.acc -= k; L.idx = Math.min(end, L.idx + k);
      if (L.idx >= end) { L.playing = false; $("play").innerHTML = S.view === "anom" ? "&#9654; Replay" : "&#9654; Play"; } }
    renderLive(false);
  }

  // ------------------------------------------------------------------ start
  drawMarks();
  setView(D.start_view || "process");
  function showPlace(eq) {            // used by the annotation section: point at a part of the plant
    if (S.view !== "process") setView("process");
    focus([eq], [], { pulse: true });
    const el = $(eq); if (el) setTimeout(() => openPop("eq", el.dataset.id, el), 450);
  }
  function playAt(run, t, trend) { closePop(); S.pending = { run, t, trend }; setView("live"); }
  window.__plant = { setView, openPop, loadRun, showPlace, playAt, openAnomaly, S };
})();
