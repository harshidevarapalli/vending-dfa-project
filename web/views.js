/* Sidebar + Simulator + Generator views (frontend only).
   Functional reference: app/Simulator.py, app/pages/Generator.py, ui/session.py,
   ui/panels.py. Automaton behaviour is never computed here:
   · Simulator steps are lookups in δ/λ produced by the Python backend
     (via ctx.feed, the same engine that drives the 3D machine);
   · trap messages come from core.mealy.explain_dead (pre-computed in Python);
   · Generator results come from core.generator.build + core.minimize.to_minimal
     + core.render tables, requested through `backend`. */
window.VM_VIEWS = {
init(ctx, backend) {
'use strict';
const { M, C, S, on, feed, resetMachine, isFinal, bal, HOOK } = ctx;
const cfg = M.cfg;
const COINS = Object.entries(cfg.coins).sort((a, b) => a[1] - b[1]);
const PRODS = Object.entries(cfg.products);
const $ = (sel, root = document) => root.querySelector(sel);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const h = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const now = () => { const d = new Date(); return [d.getHours(), d.getMinutes(), d.getSeconds()].map(n => String(n).padStart(2, '0')).join(':'); };
const iconFor = name => (M.icons && M.icons[name]) || '📦';

/* ═══════════════ navigation ═══════════════ */
const nav = $('#vm-nav'), views = { sim: $('#view-sim'), gen: $('#view-gen') };
let current = 'home';
function setView(v) {
  current = v;
  Object.entries(views).forEach(([k, el]) => { el.hidden = k !== v; });
  document.body.classList.toggle('in-view', v !== 'home');
  document.body.classList.toggle('view-sim', v === 'sim');
  document.body.classList.toggle('view-gen', v === 'gen');
  HOOK.sim = v === 'sim';
  HOOK.paused = v === 'gen';
  nav.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  if (v === 'home') ctx.syncScroll(); else $('#stage').style.visibility = v === 'sim' ? 'visible' : 'hidden';
  if (v === 'sim') { views.sim.scrollTop = 0; paintSimGraph(); }
  try { sessionStorage.setItem('vm_view', v); } catch (e) { /* ignore */ }
}
nav.addEventListener('click', e => { const b = e.target.closest('[data-view]'); if (b) { ctx.cancelRun(); setView(b.dataset.view); } });
const navLcd = $('#nav-lcd');
function paintNavLcd() {
  const b = bal(S.q);
  navLcd.innerHTML = `<span class="st">${esc(S.q)}</span><span class="bl">${isFinal(S.q) ? 'SOLD' : S.q === 'q_dead' ? 'BEEP' : '₹' + (b ?? '—')}</span>`;
  navLcd.className = 'vm-nav-lcd mono' + (isFinal(S.q) ? ' ok' : S.q === 'q_dead' ? ' bad' : '');
}

/* ═══════════════ generic state diagram (SVG) ═══════════════ */
const NS = 'http://www.w3.org/2000/svg';
const sv = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.append(e); return e; };
let gid = 0;
function makeGraph(svgEl, g) {
  const id = 'g' + (++gid);
  svgEl.innerHTML = ''; svgEl.setAttribute('viewBox', '0 0 980 640'); svgEl.classList.add('vm-graph');
  const isF = q => g.final.includes(q);
  const B = g.states.filter(q => bal(q) !== null).sort((a, b) => bal(a) - bal(b));
  const F = g.states.filter(q => bal(q) === null && isF(q));
  const Dd = g.states.filter(q => q === 'q_dead');
  const O = g.states.filter(q => bal(q) === null && !isF(q) && q !== 'q_dead');
  const P = {}, R = {};
  const cols = F.length > 5 ? 2 : 1, rowsN = Math.ceil(F.length / cols);
  const bigR = 34, fR = F.length > 1 ? Math.max(24, Math.min(32, 440 / Math.max(1, rowsN - 1) / 2 - 6)) : 34;
  B.forEach((q, i) => { const t = B.length > 1 ? i / (B.length - 1) : 0; P[q] = { x: 90 + t * (F.length > 4 ? 590 : 620), y: 430 - Math.sin(Math.PI * t) * 170 }; R[q] = bigR; });
  F.forEach((q, i) => {
    const c = cols === 2 ? i % 2 : 0, r = cols === 2 ? Math.floor(i / 2) : i;
    P[q] = F.length === 1 ? { x: 880, y: 160 } : { x: cols === 2 ? 842 + c * 88 + (r % 2 ? 0 : 0) : 880, y: 56 + r * (440 / Math.max(1, rowsN - 1)) + (cols === 2 && c ? 22 : 0) };
    R[q] = fR; });
  Dd.forEach(q => { P[q] = { x: 880, y: F.length > 1 ? 572 : 500 }; R[q] = bigR; });
  O.forEach((q, i) => { P[q] = { x: 760, y: 300 + i * 74 }; R[q] = 30; });

  const defs = sv('defs', {}, svgEl);
  [['mu', C.muted], ['tx', C.text], ['bl', C.secondary]].forEach(([k, c]) => {
    const m = sv('marker', { id: `${id}-${k}`, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse' }, defs);
    sv('path', { d: 'M0,0 L10,5 L0,10 z', fill: c }, m);
  });
  const gE = sv('g', {}, svgEl), gN = sv('g', {}, svgEl);
  const E = {};
  g.states.forEach(u => g.symbols.forEach(a => { const v = g.delta[u][a], k = u + '>' + v; (E[k] = E[k] || { u, v, syms: [] }).syms.push(a); }));
  const nrm = (p, q) => { const l = Math.hypot(q.x - p.x, q.y - p.y) || 1; return { x: (q.x - p.x) / l, y: (q.y - p.y) / l }; };
  Object.values(E).forEach(e => {
    const a = P[e.u], b = P[e.v]; let d, lx, ly;
    if (e.u === e.v) {
      const up = e.v === 'q_dead' ? 1 : -1, r = R[e.u];
      d = `M${a.x - 13},${a.y + up * r * .9} C${a.x - 54},${a.y + up * (r + 64)} ${a.x + 54},${a.y + up * (r + 64)} ${a.x + 13},${a.y + up * r * .9}`;
      lx = a.x; ly = a.y + up * (r + 54);
    } else {
      const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L, mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      const back = e.v === g.start, toEnd = e.v === 'q_dead' || isF(e.v);
      const k = back ? .3 * L : toEnd ? .1 * L : .2 * L + 8;
      const c1 = { x: mx + nx * k, y: my + ny * k }, c2 = { x: mx - nx * k, y: my - ny * k };
      const c = back || e.v === 'q_dead' ? (c1.y > c2.y ? c1 : c2) : (c1.y < c2.y ? c1 : c2);
      const d1 = nrm(a, c), d2 = nrm(b, c);
      const s = { x: a.x + d1.x * R[e.u], y: a.y + d1.y * R[e.u] }, t = { x: b.x + d2.x * (R[e.v] + 3), y: b.y + d2.y * (R[e.v] + 3) };
      d = `M${s.x},${s.y} Q${c.x},${c.y} ${t.x},${t.y}`;
      lx = .25 * s.x + .5 * c.x + .25 * t.x; ly = .25 * s.y + .5 * c.y + .25 * t.y;
    }
    e.g = sv('g', { class: 'e' }, gE);
    e.p = sv('path', { d, 'marker-end': `url(#${id}-mu)` }, e.g);
    const t = sv('text', { x: lx, y: ly }, e.g); t.textContent = e.syms.sort().join(', ');
  });
  const s0 = P[g.start];
  sv('line', { x1: s0.x - 76, y1: s0.y, x2: s0.x - R[g.start] - 4, y2: s0.y, class: 'start', 'marker-end': `url(#${id}-mu)` }, gN);
  const N = {};
  g.states.forEach(q => {
    const p = P[q], r = R[q];
    const n = sv('g', { class: 'n' + (isF(q) ? ' acc' : '') + (q === 'q_dead' ? ' dead' : ''), transform: `translate(${p.x},${p.y})`, tabindex: 0 }, gN);
    sv('circle', { class: 'ring', r }, n);
    if (isF(q)) sv('circle', { class: 'inner', r: r - 5 }, n);
    const m = /^done_(\w+?)_ch(\d+)$/.exec(q);
    if (m) { const a = sv('text', { class: 'nm small', y: -8 }, n); a.textContent = m[1]; const b = sv('text', { class: 'nm small', y: 9 }, n); b.textContent = '+₹' + m[2]; }
    else { const a = sv('text', { class: 'nm' + (q.length > 6 ? ' small' : '') }, n); a.textContent = q; }
    const cap = sv('text', { class: 'cap', y: r + 17 }, n);
    cap.textContent = bal(q) !== null ? '₹' + bal(q) : isF(q) ? (F.length > 1 ? '' : 'accept') : q === 'q_dead' ? 'trap' : '';
    const t = sv('title', {}, n); t.textContent = q;
    N[q] = n;
  });
  const token = sv('circle', { class: 'token', r: 8, opacity: 0 }, svgEl);
  let base = null, taken = null;
  function paint(focus) {
    Object.values(E).forEach(e => {
      const isT = taken && e.u === taken.u && e.v === taken.v, out = focus && e.u === focus && !isT;
      e.g.classList.toggle('out', !!out); e.g.classList.toggle('taken', !!isT);
      e.p.setAttribute('marker-end', `url(#${id}-${isT ? 'bl' : out ? 'tx' : 'mu'})`);
    });
    Object.entries(N).forEach(([q, n]) => n.classList.toggle('focus', q === focus && q !== base));
  }
  gN.addEventListener('mouseover', e => { const n = e.target.closest('.n'); if (n) paint(n.querySelector('title').textContent); });
  gN.addEventListener('focusin', e => { const n = e.target.closest('.n'); if (n) paint(n.querySelector('title').textContent); });
  svgEl.addEventListener('mouseleave', () => paint(base));
  return {
    set(q, ev) {
      Object.values(N).forEach(n => n.classList.remove('cur', 'prev'));
      base = q; taken = ev ? { u: ev.prev, v: ev.next } : null;
      if (q && N[q]) N[q].classList.add('cur');
      if (ev && ev.prev !== ev.next && N[ev.prev]) N[ev.prev].classList.add('prev');
      paint(q);
      const e = ev && E[ev.prev + '>' + ev.next];
      if (e && !matchMedia('(prefers-reduced-motion: reduce)').matches && svgEl.isConnected && svgEl.getBoundingClientRect().width) {
        const len = e.p.getTotalLength(), t0 = performance.now(); token.setAttribute('opacity', 1);
        (function run(t) { const k = Math.min(1, (t - t0) / 600), pt = e.p.getPointAtLength((k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2) * len);
          token.setAttribute('cx', pt.x); token.setAttribute('cy', pt.y); if (k < 1) requestAnimationFrame(run); else token.setAttribute('opacity', 0); })(t0);
      }
    },
  };
}

/* ═══════════════ CSV (same shape as ui/session.to_csv / csv.DictWriter) ═══════════════ */
function toCSV(rows) {
  if (!rows.length) return '';
  const keys = Object.keys(rows[0]);
  const q = v => { v = Array.isArray(v) ? v.join(' + ') : v == null ? '' : String(v); return /[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  return [keys.map(q).join(','), ...rows.map(r => keys.map(k => q(r[k])).join(','))].join('\r\n') + '\r\n';
}
function download(name, text) {
  const a = h('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' })); a.download = name;
  document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}

/* ═══════════════ SIMULATOR ═══════════════
   Session model mirrors ui/session.py (record_step / classify / stats). */
const SIM = { log: [], history: [], tx: null, last: null, started: new Date() };
const newTx = () => ({ coins: [], symbols: [], started: now() });
SIM.tx = newTx();
function classify(prev, sym, next) {                    // == ui.session.classify
  if (prev === 'q_dead' || isFinal(prev)) return 'blocked';
  if (next === 'q_dead') return 'trap';
  if (isFinal(next)) return 'accept';
  if (sym === 'cancel') return 'cancel';
  return 'coin';
}
function closeTx(kind, title, info) {
  const e = Object.assign({ kind, title, time: now(), started: SIM.tx.started, coins: SIM.tx.coins.slice(),
    word: SIM.tx.symbols.join(' '), paid: 0, price: 0, change: 0, refund: 0, product: null }, info);
  SIM.history.push(e); SIM.tx = newTx();
}
function record(ev) {                                    // == ui.session.record_step
  const kind = classify(ev.prev, ev.sym, ev.next), b = bal(ev.prev) || 0;
  SIM.last = Object.assign({}, ev, { kind });
  SIM.tx.symbols.push(ev.sym);
  if (kind === 'coin') SIM.tx.coins.push(cfg.coins[ev.sym]);
  else if (kind === 'cancel') closeTx('cancel', 'Cancelled', { refund: b, detail: ev.out });
  else if (kind === 'accept') { const p = cfg.products[ev.sym];
    closeTx('purchase', p.name, { product: ev.sym, paid: b, price: p.price, change: b - p.price, detail: ev.out }); }
  else if (kind === 'trap') closeTx('reject', ev.sym in cfg.coins ? 'Rejected: over cap' : `Rejected: ${cfg.products[ev.sym].name} unaffordable`,
    { product: ev.sym in cfg.products ? ev.sym : null, paid: b, detail: ev.out });
}
function message(ev) {                                   // == app/Simulator.py press()
  if (!ev) return 'Insert coins, then choose a product.';
  if (ev.next === 'q_dead') return `${ev.out} — ${(M.dead_reason[ev.prev] || {})[ev.sym] || ''}`;
  if (isFinal(ev.next)) return `Dispensed: ${ev.out}. Transaction accepted.`;
  return ev.out !== '—' ? ev.out : `Balance ₹${ev.next.slice(1)}`;
}
function stats() {                                       // == ui.session.stats
  const hs = SIM.history, buys = hs.filter(e => e.kind === 'purchase');
  return { purchases: buys.length, revenue: buys.reduce((s, e) => s + e.price, 0), change: buys.reduce((s, e) => s + e.change, 0),
    refunds: hs.filter(e => e.kind === 'cancel').reduce((s, e) => s + e.refund, 0), rejected: hs.filter(e => e.kind === 'reject').length,
    transactions: hs.length, steps: SIM.log.length };
}

const sp = $('#sim-panel');
sp.innerHTML = `
  <header class="sp-head">
    <div class="kicker">Simulator</div>
    <h2>Operate the machine</h2>
    <p>A DFA acceptor with a Mealy output layer. Every button is one input symbol. The machine on the left and its state diagram move together.</p>
  </header>
  <section class="sp-sec"><div class="lbl">Machine status</div><div id="sp-lcd"></div></section>
  <section class="sp-sec">
    <div class="lbl">Coin input</div><div class="row" id="sp-coins"></div>
    <div class="lbl">Product selection</div><div class="prods" id="sp-prods"></div>
  </section>
  <section class="sp-sec"><div class="lbl">Transaction status</div><div class="status" id="sp-status"></div>
    <button class="key cta wide" id="sp-reset"><span class="main">↺ Reset machine</span><span class="sub">start a new input string</span></button></section>
  <section class="sp-sec"><div class="lbl">Automaton monitor</div><div class="mon" id="sp-mon"></div><div class="chips" id="sp-chips"></div>
    <svg id="sp-graph" role="img" aria-label="DFA state diagram"></svg><div class="hint">Hover a state to trace its arrows.</div></section>
  <section class="sp-sec"><div class="lbl">How the DFA works</div><div class="exp" id="sp-exp"></div>
    <details class="legend"><summary>State legend</summary><div id="sp-legend"></div></details></section>
  <section class="sp-sec"><div class="lbl">Transaction history</div><div class="cap" id="sp-hcap"></div><div class="hist" id="sp-hist"></div></section>
  <section class="sp-sec"><div class="lbl">Step log</div><div id="sp-log"></div></section>
  <section class="sp-sec"><div class="lbl">Session statistics</div><div class="stats" id="sp-stats"></div><div class="cap" id="sp-rate"></div>
    <div class="lbl">Export</div><div class="row">
      <button class="key" id="dl-log"><span class="main">Step log (CSV)</span><span class="sub">step_log.csv</span></button>
      <button class="key" id="dl-tx"><span class="main">Transactions (CSV)</span><span class="sub">transactions.csv</span></button></div></section>`;

// controls: identical labels to the Streamlit Simulator
const coinRow = $('#sp-coins');
COINS.forEach(([s, v]) => { const b = h('button', 'key coin', `<span class="main">₹${v}</span><span class="sub">${s}</span>`); b.dataset.sym = s; coinRow.append(b); });
const cb = h('button', 'key warn', '<span class="main">Cancel</span><span class="sub">cancel</span>'); cb.dataset.sym = 'cancel'; coinRow.append(cb);
const prodBox = $('#sp-prods');
PRODS.forEach(([s, p]) => { const b = h('button', 'key prod', `<span class="pi">${iconFor(p.name)}</span><span><span class="main">${esc(p.name)} · ₹${p.price}</span><span class="sub">${s}</span></span>`);
  b.dataset.sym = s; b.dataset.price = p.price; prodBox.append(b); });
sp.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.sym) { ctx.cancelRun(); b.classList.add('pressed'); setTimeout(() => b.classList.remove('pressed'), 140); feed(b.dataset.sym); }
});
$('#sp-reset').onclick = () => { ctx.cancelRun(); resetMachine(); };
$('#dl-log').onclick = () => SIM.log.length && download('step_log.csv', toCSV(SIM.log));
$('#dl-tx').onclick = () => SIM.history.length && download('transactions.csv', toCSV(SIM.history.map(e =>
  ({ started: e.started, time: e.time, kind: e.kind, title: e.title, coins: e.coins, price: e.price, change: e.change, refund: e.refund, word: e.word }))));

const simGraph = makeGraph($('#sp-graph'), M);
function paintSimGraph() { simGraph.set(S.q, SIM.last && SIM.last.kind !== undefined ? SIM.last : null); }

function renderSim(ev) {
  const q = S.q, b = bal(q), msg = message(ev), fx = ev ? SIM.last.kind : 'idle';
  // LCD (== ui.panels.lcd)
  const [big, tag] = isFinal(q) ? ['SOLD', 'ACCEPTED'] : q === 'q_dead' ? ['ERROR', 'TRAP'] : ['₹' + (b ?? '—'), 'CREDIT'];
  $('#sp-lcd').innerHTML = `<div class="lcd fx-${fx}" data-n="${SIM.log.length}"><div class="r"><span class="tg">${tag}</span><span class="stb">${esc(q)}</span></div>
    <div class="big">${big}</div><div class="msg">&gt; ${esc(msg)}</div></div>`;
  // status (== st.success / st.error / st.info)
  const st = $('#sp-status'); st.className = 'status ' + (q === 'q_dead' ? 'err' : isFinal(q) ? 'ok' : 'info'); st.textContent = msg;
  // affordability (products stay clickable: pressing one you can't afford shows the trap)
  prodBox.querySelectorAll('.key').forEach(k => { const ok = b !== null && b >= +k.dataset.price; k.classList.toggle('afford', ok); k.classList.toggle('dim', !ok); });
  // monitor (== ui.panels.monitor)
  const L = SIM.last;
  const cells = [['State', q, 'cur'], ['Previous', L ? L.prev : '—', ''], ['Last input', L ? L.sym : '—', ''],
    ['Balance', b !== null ? '₹' + b : '—', ''], ['Transition', L ? `δ(${L.prev}, ${L.sym}) = ${L.next}` : '—', 'edge']];
  $('#sp-mon').innerHTML = cells.map(([k, v, c]) => `<div class="cell ${c}"><div class="k">${k}</div><div class="v" title="${esc(v)}">${esc(v)}</div></div>`).join('');
  const rec = SIM.log.slice(-6);
  $('#sp-chips').innerHTML = rec.map((r, i) => `<span class="chip ${i === rec.length - 1 ? 'latest' : ''} ${r.next === 'q_dead' ? 'bad' : isFinal(r.next) ? 'ok' : ''}">${esc(r.state)} —<b>${esc(r.input)}</b>→ ${esc(r.next)}</span>`).join('');
  if (current === 'sim') paintSimGraph();
  $('#sp-exp').innerHTML = explain();
  renderHistory(); renderLog(); renderStats();
}

// explainer text == ui.panels.explain
function afford(bv) { return PRODS.filter(([, p]) => p.price <= bv).map(([, p]) => p.name); }
function explain() {
  const L = SIM.last, word = SIM.log.map(r => r.input).join(' ') || 'ε';
  if (!L) {
    const sigma = [...M.symbols].sort().join(', '), cheapest = Math.min(...PRODS.map(([, p]) => p.price));
    return `<div class="formal">${esc(M.start)} <span class="lam">start state, balance ₹0</span></div>
      <p>Every button is one <b>input symbol</b> from Σ = {${esc(sigma)}}. The DFA reads it and follows exactly <b>one</b> arrow; that's what <i>deterministic</i> means.</p>
      <p>Insert coins until the balance reaches a product's price (cheapest ₹${cheapest}), then choose it.</p>`;
  }
  const { prev, sym, next, out, kind } = L, b0 = bal(prev), b1 = bal(next);
  let text;
  if (kind === 'coin') { const can = afford(b1);
    text = `<span class="tag coin">coin</span>You inserted a ₹${cfg.coins[sym]} coin. A DFA has no memory except its current state, so “the balance is ₹${b1}” is stored entirely as <b>being in ${esc(next)}</b>.</p><p>${can.length ? `You can now afford: <b>${esc(can.join(', '))}</b>.` : 'Not enough for any product yet. Keep inserting coins.'}`; }
  else if (kind === 'cancel') text = `<span class="tag cancel">cancel</span>Cancel sends every balance state back to the start: δ(q<sub>b</sub>, cancel) = q0. The Mealy output refunds ₹${b0 || 0}, and the machine “forgets” the coins. The input string keeps going.`;
  else if (kind === 'accept') text = `<span class="tag accept">accepted</span><b>${esc(next)}</b> is an accepting state (double circle), so the input string <b>w ∈ L(M)</b>, a valid transaction. The Mealy layer turns that into a physical output: <b>${esc(out)}</b>.</p><p>Any further input goes to the trap: one string = one transaction. Press <b>Reset</b> for the next customer.`;
  else if (kind === 'trap' && sym in cfg.coins) { const v = cfg.coins[sym];
    text = `<span class="tag trap">trap</span>₹${b0} + ₹${v} = ₹${b0 + v} would exceed the ₹${cfg.cap} cap. The cap is exactly what keeps the set of states <b>finite</b>, so overflowing goes to the trap <b>q_dead</b> and λ returns the coin.`; }
  else if (kind === 'trap') { const p = cfg.products[sym];
    text = `<span class="tag trap">trap</span>${esc(p.name)} costs ₹${p.price} but the balance is only ₹${b0}. Selecting it sends the DFA to <b>q_dead</b>, a trap state whose every arrow loops back to itself, so this string can never be accepted. Press <b>Reset</b>.`; }
  else text = `<span class="tag trap">blocked</span>The machine was already in <b>${esc(prev)}</b>. Both q_done and q_dead send every symbol to q_dead: the transaction is over. Press <b>Reset</b> to start a new input string.`;
  return `<div class="formal">δ(${esc(prev)}, ${esc(sym)}) = ${esc(next)} <span class="lam">λ = ${esc(out)}</span></div><p>${text}</p>
    <div class="word">w = ${esc(word)} · current state ${isFinal(next) ? 'in F (accepting)' : 'not in F'}</div>`;
}
// legend == ui.panels.legend
(function legend() {
  const order = q => bal(q) !== null ? [0, bal(q)] : [q === 'q_dead' ? 2 : 1, 0];
  const rows = [...M.states].sort((a, b) => { const x = order(a), y = order(b); return x[0] - y[0] || x[1] - y[1]; }).map(q => {
    const b = bal(q); let m, l;
    if (q === M.start) [m, l] = ['Start: balance ₹0', 'arrow from a dot'];
    else if (b !== null) [m, l] = [`Balance ₹${b} inserted so far`, 'circle'];
    else if (isFinal(q)) [m, l] = ['Purchase complete (accepting)', 'double circle'];
    else if (q === 'q_dead') [m, l] = ['Trap: illegal input, no way out', 'dashed circle'];
    else [m, l] = ['Merged state', 'circle'];
    return `<tr><td class="mono">${esc(q)}</td><td>${m}</td><td>${l}</td></tr>`; }).join('');
  const key = [[C.primary, 'Current state (filled)'], [C.secondary, 'Previous state + last transition'], [C.success, 'Accepting state'], [C.warning, 'Trap state']]
    .map(([c, t]) => `<tr><td><i class="sw" style="background:${c}"></i></td><td colspan="2">${t}</td></tr>`).join('');
  $('#sp-legend').innerHTML = `<table class="tbl"><thead><tr><th>State</th><th>Meaning</th><th>Drawn as</th></tr></thead><tbody>${rows}</tbody></table>
    <table class="tbl" style="margin-top:10px"><thead><tr><th colspan="3">Colour key</th></tr></thead><tbody>${key}</tbody></table>`;
})();
function renderHistory() {                               // == ui.panels.history
  const hs = SIM.history, s = stats(), t = SIM.started;
  $('#sp-hcap').textContent = `Session started ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')} · ${s.transactions} transactions · ${s.purchases} purchases`;
  if (!hs.length) { $('#sp-hist').innerHTML = '<div class="empty">No finished transactions yet. Buy something, cancel, or trigger a rejection and it appears here.</div>'; return; }
  $('#sp-hist').innerHTML = hs.slice(-8).reverse().map(e => {
    const coins = e.coins.map(c => '₹' + c).join(' + ') || 'no coins';
    const [ico, right] = e.kind === 'purchase' ? [iconFor(e.title), `<b>₹${e.price}</b>change ₹${e.change}`]
      : e.kind === 'cancel' ? ['↩', `<b>₹${e.refund}</b>refunded`] : ['⚠', `<b>₹${e.paid}</b>balance`];
    return `<div class="tx ${e.kind}"><div class="ico">${ico}</div><div><div class="t">${esc(e.title)}</div><div class="d">${esc(coins)} · w = ${esc(e.word)}</div></div>
      <div class="rr">${right}<br>${e.started}–${e.time}</div></div>`; }).join('') +
    (hs.length > 8 ? `<div class="cap">Showing the latest 8 of ${hs.length}. Download the CSV for all.</div>` : '');
}
function renderLog() {
  const box = $('#sp-log');
  if (!SIM.log.length) { box.innerHTML = '<div class="cap">No steps yet.</div>'; return; }
  box.innerHTML = `<div class="scroll"><table class="tbl"><thead><tr><th>step</th><th>state</th><th>input</th><th>next</th><th>output</th></tr></thead><tbody>` +
    SIM.log.slice().reverse().map(r => `<tr><td>${r.step}</td><td class="mono">${esc(r.state)}</td><td class="mono">${esc(r.input)}</td><td class="mono">${esc(r.next)}</td><td>${esc(r.output)}</td></tr>`).join('') +
    '</tbody></table></div>';
}
function renderStats() {
  const s = stats();
  $('#sp-stats').innerHTML = [['Purchases', s.purchases], ['Revenue', '₹' + s.revenue], ['Change given', '₹' + s.change],
    ['Refunded', '₹' + s.refunds], ['Rejected', s.rejected], ['Steps', s.steps]]
    .map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
  $('#sp-rate').textContent = `Acceptance rate: ${s.transactions ? Math.round(100 * s.purchases / s.transactions) + '%' : '—'} of finished transactions`;
  $('#dl-log').disabled = !SIM.log.length; $('#dl-tx').disabled = !SIM.history.length;
}

// every step of the ONE machine (3D keys, hero deck, brain deck, here) is recorded
on(ev => {
  if (!ev) { SIM.log = []; SIM.tx = newTx(); SIM.last = null; }   // == Simulator.reset + ui.session.on_reset
  else { SIM.log.push({ step: SIM.log.length + 1, state: ev.prev, input: ev.sym, next: ev.next, output: ev.out }); record(ev); }
  paintNavLcd(); renderSim(ev);
});

/* ═══════════════ GENERATOR ═══════════════
   Mirrors app/pages/Generator.py; results come from the Python backend. */
const gw = $('#gen-wrap');
const defaults = backend.defaultForm || { coins: [['c5', 5], ['c10', 10]], products: [['s1', 'Chips', 10], ['s2', 'Juice', 15], ['s3', 'Chocolate', 20]], cap: 25 };
gw.innerHTML = `
  <header class="gen-head">
    <div class="kicker">Generator · engineering bay</div>
    <h2>Build an automaton</h2>
    <p>Enter coins and products. The generator builds the naive DFA, minimizes it with Hopcroft's algorithm, and shows both.</p>
    <div class="src ${backend.live ? 'live' : 'off'}"><i></i>${backend.live ? 'Connected to the Python backend: core.generator · core.minimize'
      : 'Offline copy: showing machines pre-built by the Python backend'}</div>
  </header>
  <div class="gen-top"><button class="key" id="g-rand"><span class="main">🎲 Randomize</span><span class="sub">fill a random valid machine and generate it</span></button></div>
  <form class="plate" id="g-form" autocomplete="off" novalidate>
    <div class="pcol"><div class="lbl">Coins · Σ<sub>coin</sub></div><div id="g-coins"></div>
      <label class="fld capf"><span>Balance cap ₹</span><input type="number" min="5" step="5" id="g-cap"></label></div>
    <div class="pcol wide"><div class="lbl">Products · Σ<sub>select</sub></div><div id="g-prods"></div></div>
    <div class="pfoot"><button class="key cta" type="submit" id="g-go"><span class="main">⚙ Generate</span><span class="sub">build → minimize</span></button>
      <div class="gerr" id="g-err" role="alert"></div></div>
  </form>
  <div id="g-out" hidden>
    <div class="metrics" id="g-metrics"></div>
    <div class="diagrams">
      <div class="dg"><div class="lbl">Naive DFA</div><svg id="g-naive" role="img" aria-label="Naive DFA"></svg></div>
      <div class="dg"><div class="lbl">Minimized DFA</div><svg id="g-min" role="img" aria-label="Minimized DFA"></svg></div>
    </div>
    <div class="hint">Hover a state to trace its arrows.</div>
    <div class="tabs" role="tablist">
      <button class="tab on" data-t="classes" role="tab">Equivalence classes</button>
      <button class="tab" data-t="trace" role="tab">Hopcroft trace</button>
      <button class="tab" data-t="mealy" role="tab">Mealy output table</button>
    </div>
    <div class="tabbody"><div class="row"><button class="key" id="g-csv"><span class="main">Download CSV</span><span class="sub" id="g-csvname"></span></button></div>
      <div class="scroll tall" id="g-table"></div></div>
    <button class="key cta wide" id="g-load"><span class="main">▶ Load this machine into the Simulator</span><span class="sub">the 3D machine and the whole experience switch to it</span></button>
  </div>`;
const coinBox = $('#g-coins'), prodBox2 = $('#g-prods');
for (let i = 0; i < 4; i++) {
  coinBox.insertAdjacentHTML('beforeend', `<div class="frow"><label class="fld"><span>Symbol ${i + 1}</span><input id="cs${i}" placeholder="c5"></label>
    <label class="fld"><span>Value ₹ ${i + 1}</span><input id="cv${i}" type="number" min="0" step="5"></label></div>`);
  prodBox2.insertAdjacentHTML('beforeend', `<div class="frow three"><label class="fld"><span>Symbol ${i + 1}</span><input id="ps${i}" placeholder="s1"></label>
    <label class="fld"><span>Name ${i + 1}</span><input id="pn${i}" placeholder="Chips"></label>
    <label class="fld"><span>Price ₹ ${i + 1}</span><input id="pp${i}" type="number" min="0" step="5"></label></div>`);
}
function fillForm(f) {
  for (let i = 0; i < 4; i++) {
    const c = f.coins[i] || ['', 0], p = f.products[i] || ['', '', 0];
    $('#cs' + i).value = c[0]; $('#cv' + i).value = c[1]; $('#ps' + i).value = p[0]; $('#pn' + i).value = p[1]; $('#pp' + i).value = p[2];
  }
  $('#g-cap').value = f.cap;
}
function readForm() {                                    // same row rules as Generator.py
  const coins = {}, products = {};
  for (let i = 0; i < 4; i++) {
    const cs = $('#cs' + i).value.trim(), cv = parseInt($('#cv' + i).value, 10) || 0;
    if (cs && cv) coins[cs] = cv;
    const ps = $('#ps' + i).value.trim(), pn = $('#pn' + i).value.trim(), pp = parseInt($('#pp' + i).value, 10) || 0;
    if (ps && pn && pp) products[ps] = { name: pn, price: pp };
  }
  return { coins, products, cap: parseInt($('#g-cap').value, 10) || 0 };
}
fillForm(defaults);

let result = null, tab = 'classes';
const TABS = { classes: ['classes', 'equivalence_classes.csv'], trace: ['trace', 'hopcroft_trace.csv'], mealy: ['mealy', 'mealy_table.csv'] };
function busy(on) { gw.classList.toggle('busy', on); $('#g-go').disabled = on; $('#g-rand').disabled = on; }
async function ask(op, data) {
  busy(true); $('#g-err').textContent = backend.live ? 'Building on the Python backend…' : ''; $('#g-err').className = 'gerr wait';
  try { return await backend.request(op, data); } finally { busy(false); }
}
function showResult(r) {
  $('#g-err').className = 'gerr';
  if (!r.ok) { $('#g-err').textContent = r.error; return; }        // == st.error(str(ConfigError))
  $('#g-err').textContent = '';
  result = r; $('#g-out').hidden = false;
  const m = r.metrics;
  $('#g-metrics').innerHTML = `<div class="met"><div class="k">Naive states</div><div class="v">${m.naive}</div></div>
    <div class="met arrow">→ Hopcroft →</div>
    <div class="met"><div class="k">Minimal states</div><div class="v">${m.minimal}</div></div>
    <div class="met"><div class="k">Theorem: cap/g + 3</div><div class="v">${m.theorem} <span class="${m.matches ? 'ok' : 'bad'}">${m.matches ? '✓ matches' : '✕ mismatch'}</span></div></div>`;
  makeGraph($('#g-naive'), r.naive).set(null, null);
  makeGraph($('#g-min'), r.minimal).set(null, null);
  renderTab();
  $('#g-out').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
}
function renderTab() {
  gw.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.t === tab));
  const [key, file] = TABS[tab], rows = result[key];
  $('#g-csvname').textContent = file; $('#g-csv').disabled = !rows.length;
  if (!rows.length) { $('#g-table').innerHTML = '<div class="cap">Nothing to show: no refinement steps were needed.</div>'; return; }
  const cols = Object.keys(rows[0]);
  $('#g-table').innerHTML = `<table class="tbl"><thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>` +
    rows.map(r => '<tr>' + cols.map(c => { const v = String(r[c]);
      const cls = /^BEEP/.test(v) ? 'beep' : c === 'output' && v !== '—' ? 'give' : ''; return `<td class="mono ${cls}">${esc(v)}</td>`; }).join('') + '</tr>').join('') + '</tbody></table>';
}
gw.querySelectorAll('.tab').forEach(t => t.onclick = () => { tab = t.dataset.t; renderTab(); });
$('#g-csv').onclick = () => { const [key, file] = TABS[tab]; download(file, toCSV(result[key])); };
$('#g-form').addEventListener('submit', async e => { e.preventDefault(); showResult(await ask('generate', { cfg: readForm() })); });
$('#g-rand').onclick = async () => { const r = await ask('randomize', {}); if (r.ok) fillForm(r.form); showResult(r); };
$('#g-load').onclick = async () => {
  if (!result) return;
  try { sessionStorage.setItem('vm_view', 'sim'); } catch (e) { /* ignore */ }
  $('#g-load').disabled = true; $('#g-err').className = 'gerr wait'; $('#g-err').textContent = 'Loading into the machine…';
  await backend.request('load', { cfg: result.cfg });     // page reloads with the new machine
};

/* ─── go ─── */
paintNavLcd(); renderSim(null);
let start = 'home';
try { start = sessionStorage.getItem('vm_view') || 'home'; } catch (e) { /* ignore */ }
setView(['sim', 'gen'].includes(start) ? start : 'home');
},
};
