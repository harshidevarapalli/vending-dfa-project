/* STATE MACHINE: scroll experience (frontend only).
   Injected into web/experience.html by app/pages/1_Inside_the_Machine.py.
   Reads M (the backend's minimized DFA + Mealy outputs). Never alters it. */
(function () {
'use strict';

/* ─── palette (single source: core/theme.py → CSS vars) ─── */
const css = getComputedStyle(document.documentElement);
const C = {};
['primary', 'secondary', 'bg', 'panel', 'text', 'muted', 'warning', 'success']
  .forEach(k => { C[k] = css.getPropertyValue('--' + k).trim(); });
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ─── machine facts (derived from M only) ─── */
const cfg = M.cfg;
const COINS = Object.entries(cfg.coins).sort((a, b) => a[1] - b[1]);   // [[sym, value]]
const PRODS = Object.entries(cfg.products);                             // [[sym, {name, price}]]
const G = COINS[0][1];
const isFinal = q => M.final.includes(q);
const bal = q => (/^q\d+$/.test(q) ? +q.slice(1) : null);
const symLabel = a => a in cfg.coins ? '₹' + cfg.coins[a] + ' coin'
  : a === 'cancel' ? 'Cancel' : (cfg.products[a] ? cfg.products[a].name : a);

function classify(prev, sym, next) {
  if (prev === 'q_dead' || isFinal(prev)) return 'blocked';
  if (next === 'q_dead') return sym in cfg.coins ? 'overpay' : 'short';
  if (isFinal(next)) return 'accept';
  if (sym === 'cancel') return 'cancel';
  return 'coin';
}

/* ─── one shared state for the body (3D) and the brain (graph) ─── */
const S = { q: M.start, word: [], last: null };
const subs = [];
const on = f => subs.push(f);
function feed(sym) {
  const prev = S.q, next = M.delta[prev][sym], out = M.lambda[prev][sym];
  const ev = { prev, sym, next, out, kind: classify(prev, sym, next), i: S.word.length };
  S.q = next; S.word.push(sym); S.last = ev;
  subs.forEach(f => f(ev));
}
function resetMachine() {
  S.q = M.start; S.word = []; S.last = null;
  subs.forEach(f => f(null));
}

/* scenarios: real symbol strings, built from the config, fed through δ */
function coinsFor(amount) {                 // greedy, always exact because G | amount
  const seq = []; let left = amount;
  for (const [s, v] of [...COINS].reverse()) while (left >= v) { seq.push(s); left -= v; }
  return seq;
}
function scenarios() {
  const byPrice = [...PRODS].sort((a, b) => a[1].price - b[1].price);
  const [cheapS, cheap] = byPrice[0], [dearS, dear] = byPrice[byPrice.length - 1];
  const big = COINS[COINS.length - 1];
  const list = [['Exact payment', [...coinsFor(cheap.price), cheapS]]];
  for (const [s, p] of byPrice) {                       // overshoot with the big coin → change
    const n = Math.ceil(p.price / big[1]), paid = n * big[1];
    if (paid > p.price && paid <= cfg.cap) { list.push(['With change', [...Array(n).fill(big[0]), s]]); break; }
  }
  if (G < dear.price) list.push(['Not enough money', [COINS[0][0], dearS]]);
  list.push(['Overpay the cap', Array(Math.floor(cfg.cap / big[1]) + 1).fill(big[0])]);
  list.push(['Cancel', [COINS[0][0], 'cancel']]);
  list.push(['A coin after buying', [...coinsFor(cheap.price), cheapS, COINS[0][0]]]);
  return list;
}
let runToken = 0;
async function play(seq, btn) {
  const t = ++runToken;
  document.querySelectorAll('.scen button').forEach(b => b.classList.toggle('on', b === btn));
  resetMachine();
  await wait(650);
  for (const s of seq) {
    if (t !== runToken) return;
    feed(s);
    await wait(REDUCED ? 450 : 1250);
  }
  if (btn) btn.classList.remove('on');
}
const wait = ms => new Promise(r => setTimeout(r, ms));

/* ════════════════ UI: decks, tape, readouts ════════════════ */
function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

function buildDeck(root) {
  root.innerHTML = '';
  root.append(el('div', 'lbl', 'Coins'));
  const r1 = el('div', 'row');
  COINS.forEach(([s, v]) => {
    const b = el('button', 'key coin', `<span class="main">₹${v}</span><span class="sub">${s}</span>`);
    b.dataset.sym = s; r1.append(b);
  });
  const cancel = el('button', 'key warn', '<span class="main">Cancel</span><span class="sub">cancel</span>');
  cancel.dataset.sym = 'cancel'; r1.append(cancel);
  root.append(r1);
  root.append(el('div', 'lbl', 'Products'));
  const r2 = el('div', 'row');
  PRODS.forEach(([s, p]) => {
    const b = el('button', 'key prod', `<span class="main">${p.name} · ₹${p.price}</span><span class="sub">${s}</span>`);
    b.dataset.sym = s; b.dataset.price = p.price; r2.append(b);
  });
  const rs = el('button', 'key ghost', '<span class="main">Reset</span><span class="sub">new string</span>');
  rs.dataset.reset = '1'; r2.append(rs);
  root.append(r2);
  root.append(el('div', 'lbl', 'Input string w'));
  root.append(el('div', 'tape'));
  root.append(el('div', 'readout'));
  root.append(el('div', 'verdict'));
  root.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    runToken++;
    if (b.dataset.reset) resetMachine(); else if (b.dataset.sym) feed(b.dataset.sym);
  });
}
function renderDeck(root, ev) {
  const b = bal(S.q);
  root.querySelectorAll('.key.prod').forEach(k => k.classList.toggle('afford', b !== null && b >= +k.dataset.price));
  const tape = root.querySelector('.tape');
  const w = S.word, start = Math.max(0, w.length - 9);
  tape.innerHTML = w.length ? (start ? '<span class="eps">…</span>' : '') : '<span class="eps">w = ε (empty)</span>';
  w.slice(start).forEach((s, j) => {
    const i = start + j, c = el('span', 'cell', s);
    if (i === w.length - 1) c.classList.add(isFinal(S.q) ? 'ok' : S.q === 'q_dead' ? 'bad' : 'now');
    tape.append(c);
  });
  root.querySelector('.readout').innerHTML = formal(ev);
  const v = root.querySelector('.verdict');
  v.className = 'verdict ' + (isFinal(S.q) ? 'ok' : S.q === 'q_dead' ? 'bad' : '');
  v.textContent = isFinal(S.q) ? 'w ∈ L(M): accepted'
    : S.q === 'q_dead' ? 'w ∉ L(M): trapped, press Reset'
    : w.length ? 'reading… not accepted yet' : '';
}
function formal(ev) {
  if (!ev) return `<span class="lam">start in ${M.start}, balance ₹0</span>`;
  return `δ(${ev.prev}, ${ev.sym}) = ${ev.next} <span class="lam">· λ = ${ev.out}</span>`;
}

const deckHero = document.getElementById('deck-hero');
const deckBrain = document.getElementById('deck-brain');
buildDeck(deckHero); buildDeck(deckBrain);
const scenBox = document.getElementById('scenarios');
scenarios().forEach(([name, seq]) => {
  const b = el('button', '', `<span class="play">▶</span>${name}`);
  b.title = seq.join(' ');
  b.onclick = () => play(seq, b);
  scenBox.append(b);
});
on(ev => { renderDeck(deckHero, ev); renderDeck(deckBrain, ev); });

/* ════════════════ 3D: the machine ════════════════ */
const canvas = document.getElementById('stage');
let R;
try { R = new THREE.WebGLRenderer({ canvas, antialias: true }); }
catch (e) { R = null; }
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
const VM = new THREE.Group(); scene.add(VM);
const hit = [];                                   // clickable meshes
const DIM = { W: 2.3, H: 3.9, D: 1.35 };
const FRONT = DIM.D / 2;
const WIN = { x: -0.34, w: 1.36, y0: 1.0, y1: 3.28 };       // product window
const COL = { x: 0.8, w: 0.52 };                               // control column
const anchors = {};                                            // for callouts

if (R) {
  R.setPixelRatio(Math.min(devicePixelRatio, 2));
  R.outputColorSpace = THREE.SRGBColorSpace;
  R.toneMapping = THREE.ACESFilmicToneMapping; R.toneMappingExposure = 1.0;
  R.shadowMap.enabled = true; R.shadowMap.type = THREE.PCFSoftShadowMap;
  scene.background = new THREE.Color(C.bg);
  scene.fog = new THREE.Fog(C.bg, 13, 30);
}

function mat(color, o = {}) { return new THREE.MeshStandardMaterial(Object.assign({ color, roughness: .55, metalness: .05 }, o)); }
function roundBox(w, h, d, r, material) {
  const s = new THREE.Shape(), x = -w / 2 + r, y = -h / 2 + r, iw = w - 2 * r, ih = h - 2 * r;
  s.moveTo(x, y - r); s.lineTo(x + iw, y - r); s.quadraticCurveTo(x + iw + r, y - r, x + iw + r, y);
  s.lineTo(x + iw + r, y + ih); s.quadraticCurveTo(x + iw + r, y + ih + r, x + iw, y + ih + r);
  s.lineTo(x, y + ih + r); s.quadraticCurveTo(x - r, y + ih + r, x - r, y + ih);
  s.lineTo(x - r, y); s.quadraticCurveTo(x - r, y - r, x, y - r);
  const g = new THREE.ExtrudeGeometry(s, { depth: d - r, bevelEnabled: true, bevelThickness: r / 2,
    bevelSize: r / 2 * 0.001, bevelSegments: 3, curveSegments: 10 });
  g.center();
  const m = new THREE.Mesh(g, material); m.castShadow = m.receiveShadow = true; return m;
}
function box(w, h, d, material) { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material); m.castShadow = m.receiveShadow = true; return m; }
function cyl(r, h, material, seg = 32) { const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, seg), material); m.castShadow = true; return m; }
function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  t.userData = { c, ctx: c.getContext('2d'), draw }; if (draw) { draw(t.userData.ctx, w, h); t.needsUpdate = true; }
  return t;
}
function mono(px, w = 600) { return `${w} ${px}px "IBM Plex Mono", ui-monospace, Menlo, monospace`; }

let lcdTex, slotRim, flap, cupCoins = [], rows = [], coinProto = {}, traces, buzzer, keyMeshes = {};

function buildScene() {
  /* lights */
  scene.add(new THREE.HemisphereLight(0xcfe6ff, new THREE.Color(C.bg), 0.55));
  const key = new THREE.DirectionalLight(0xffffff, 2.1);
  key.position.set(-4, 7, 6); key.castShadow = true; key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.left = -4; key.shadow.camera.right = 4; key.shadow.camera.top = 6; key.shadow.camera.bottom = -2;
  scene.add(key);
  const rimPink = new THREE.PointLight(new THREE.Color(C.primary), 26, 12); rimPink.position.set(-3, 3.2, -2.4); scene.add(rimPink);
  const rimBlue = new THREE.PointLight(new THREE.Color(C.secondary), 22, 12); rimBlue.position.set(3.4, 2.4, -1.6); scene.add(rimBlue);

  /* floor: a lit disc so the machine stands somewhere */
  const floor = new THREE.Mesh(new THREE.CircleGeometry(9, 64), mat(C.panel, { roughness: .95 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

  /* body */
  const bodyMat = mat(C.primary, { roughness: .42, metalness: .08 });
  const body = roundBox(DIM.W, DIM.H, DIM.D, 0.14, bodyMat); body.position.y = DIM.H / 2 + 0.08; VM.add(body);
  const navy = mat(C.panel, { roughness: .6 });
  const deep = mat(C.bg, { roughness: .8 });
  [-0.85, 0.85].forEach(x => { const f = box(0.28, 0.1, 0.9, deep); f.position.set(x, 0.05, 0); VM.add(f); });

  /* header sign */
  const signTex = canvasTex(1024, 180, (g, w, h) => {
    g.fillStyle = C.bg; g.fillRect(0, 0, w, h);
    g.font = '800 104px Inter, system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.shadowColor = C.primary; g.shadowBlur = 26; g.fillStyle = C.primary; g.fillText('STATE MACHINE', w / 2, h / 2 + 4);
    g.shadowBlur = 0; g.fillStyle = '#ffd6e0'; g.fillText('STATE MACHINE', w / 2, h / 2 + 4);
  });
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(DIM.W - 0.34, 0.36), new THREE.MeshBasicMaterial({ map: signTex }));
  sign.position.set(0, DIM.H - 0.12, FRONT + 0.012); VM.add(sign); anchors.q0 = sign;

  /* product window: back wall, frame, shelves, coils, items, glass */
  const wh = WIN.y1 - WIN.y0, wy = (WIN.y0 + WIN.y1) / 2;
  const back = box(WIN.w, wh, 0.04, deep); back.position.set(WIN.x, wy, FRONT + 0.01); VM.add(back);
  const frameM = navy;
  [[WIN.w + 0.12, 0.06, 0, wh / 2 + 0.03], [WIN.w + 0.12, 0.06, 0, -wh / 2 - 0.03],
   [0.06, wh + 0.12, WIN.w / 2 + 0.03, 0], [0.06, wh + 0.12, -WIN.w / 2 - 0.03, 0]].forEach(([w, h, dx, dy]) => {
    const f = box(w, h, 0.44, frameM); f.position.set(WIN.x + dx, wy + dy, FRONT + 0.22); VM.add(f);
  });
  const nR = PRODS.length, rowH = wh / nR;
  const itemCols = [C.warning, C.secondary, C.primary, C.success];
  const coilMat = mat(C.muted, { metalness: .8, roughness: .3 });
  PRODS.forEach(([sym, p], r) => {
    const yBase = WIN.y1 - (r + 1) * rowH + 0.04;
    const shelf = box(WIN.w, 0.03, 0.4, mat(C.panel, { roughness: .4 })); shelf.position.set(WIN.x, yBase, FRONT + 0.22); VM.add(shelf);
    const strip = new THREE.Mesh(new THREE.BoxGeometry(WIN.w, 0.022, 0.012),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(C.secondary) }));
    strip.position.set(WIN.x, yBase - 0.006, FRONT + 0.43); strip.material.transparent = true; strip.material.opacity = .55; VM.add(strip);
    const tagTex = canvasTex(256, 64, (g, w, h) => { g.fillStyle = C.bg; g.fillRect(0, 0, w, h); g.fillStyle = C.text; g.font = mono(30);
      g.textBaseline = 'middle'; g.fillText(sym.toUpperCase(), 12, h / 2); g.fillStyle = C.success; g.textAlign = 'right'; g.fillText('₹' + p.price, w - 12, h / 2); });
    const tag = new THREE.Mesh(new THREE.PlaneGeometry(0.34, 0.085), new THREE.MeshBasicMaterial({ map: tagTex }));
    tag.position.set(WIN.x, yBase - 0.05, FRONT + 0.445); VM.add(tag);
    const itemMat = mat(itemCols[r % 4], { roughness: .5 });
    const items = [];
    const h = Math.min(0.42, rowH * 0.62);
    [-0.44, 0, 0.44].forEach(dx => {
      const coil = helix(0.105, 0.34, 4.5, coilMat); coil.position.set(WIN.x + dx, yBase + 0.12, FRONT + 0.22); VM.add(coil);
      const it = itemMesh(r % 4, h, itemMat); it.position.set(WIN.x + dx, yBase + 0.015 + it.userData.h / 2, FRONT + 0.25); VM.add(it);
      it.userData.home = it.position.clone(); it.userData.homeRot = it.rotation.clone();
      items.push({ it, coil });
    });
    rows.push({ sym, strip, items, yBase });
  });
  anchors.rowTop = rows[0].strip;
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(WIN.w, wh), new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(C.secondary), transparent: true, opacity: .1, roughness: .05, metalness: 0,
    emissive: new THREE.Color(C.secondary), emissiveIntensity: .05, depthWrite: false }));
  glass.position.set(WIN.x, wy, FRONT + 0.445); VM.add(glass);
  const inner = new THREE.PointLight(new THREE.Color(C.secondary), 3.2, 3); inner.position.set(WIN.x, wy + 0.4, FRONT + 0.3); VM.add(inner);

  /* dispense bay + flap */
  const BAY = { y0: 0.3, y1: 0.76, d: 0.36 };
  const bayBack = box(WIN.w, BAY.y1 - BAY.y0, 0.02, deep); bayBack.position.set(WIN.x, (BAY.y0 + BAY.y1) / 2, FRONT + 0.01); VM.add(bayBack);
  [[WIN.w + 0.12, 0.05, BAY.y0 - 0.025], [WIN.w + 0.12, 0.05, BAY.y1 + 0.025]].forEach(([w, h, y]) => {
    const b = box(w, h, BAY.d, navy); b.position.set(WIN.x, y, FRONT + BAY.d / 2); VM.add(b); });
  [-1, 1].forEach(sd => { const b = box(0.06, BAY.y1 - BAY.y0 + 0.1, BAY.d, navy); b.position.set(WIN.x + sd * (WIN.w / 2 + 0.03), (BAY.y0 + BAY.y1) / 2, FRONT + BAY.d / 2); VM.add(b); });
  anchors.bayFloor = BAY.y0; anchors.bayZ = FRONT + BAY.d * 0.45;
  flap = new THREE.Group(); flap.position.set(WIN.x, BAY.y1, FRONT + BAY.d);
  const flapM = new THREE.Mesh(new THREE.PlaneGeometry(WIN.w, BAY.y1 - BAY.y0), new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(C.secondary), transparent: true, opacity: .16, roughness: .2, depthWrite: false }));
  flapM.position.y = -(BAY.y1 - BAY.y0) / 2; flap.add(flapM); VM.add(flap);
  const pull = box(0.4, 0.04, 0.05, mat(C.muted, { metalness: .7, roughness: .3 })); pull.position.set(0, -(BAY.y1 - BAY.y0) + 0.06, 0.02); flap.add(pull);
  anchors.flap = pull;

  /* control column */
  const panel = box(COL.w, 2.9, 0.06, navy); panel.position.set(COL.x, 2.0, FRONT + 0.03); VM.add(panel);
  lcdTex = canvasTex(1024, 512, null);
  const lcd = new THREE.Mesh(new THREE.PlaneGeometry(0.44, 0.22), new THREE.MeshBasicMaterial({ map: lcdTex }));
  lcd.position.set(COL.x, 3.12, FRONT + 0.065); VM.add(lcd); anchors.lcd = lcd;
  const bezel = box(0.48, 0.26, 0.02, deep); bezel.position.set(COL.x, 3.12, FRONT + 0.055); VM.add(bezel);

  // coin slot with a lit rim
  slotRim = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.22, 0.01), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.secondary), transparent: true, opacity: .35 }));
  slotRim.position.set(COL.x - 0.12, 2.78, FRONT + 0.062); VM.add(slotRim);
  const slot = box(0.035, 0.16, 0.02, mat('#000000')); slot.position.set(COL.x - 0.12, 2.78, FRONT + 0.068); VM.add(slot);
  anchors.slot = slot;
  const slotLbl = canvasTex(128, 48, (g, w, h) => { g.fillStyle = C.panel; g.fillRect(0, 0, w, h); g.fillStyle = C.muted; g.font = mono(22, 500); g.textBaseline = 'middle'; g.fillText('COINS', 8, h / 2); });
  const sl = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 0.06), new THREE.MeshBasicMaterial({ map: slotLbl })); sl.position.set(COL.x + 0.1, 2.78, FRONT + 0.062); VM.add(sl);

  // keypad: one key per product + cancel (physical buttons that feed δ)
  const keySyms = [...PRODS.map(([s]) => s), 'cancel'];
  keySyms.forEach((s, i) => {
    const cx = COL.x - 0.11 + (i % 2) * 0.22, cy = 2.48 - Math.floor(i / 2) * 0.2;
    const lab = s === 'cancel' ? '✕' : s.toUpperCase();
    const face = canvasTex(128, 128, (g, w, h) => {
      g.fillStyle = s === 'cancel' ? C.warning : C.text; g.beginPath(); g.arc(w / 2, h / 2, w / 2, 0, 7); g.fill();
      g.save(); g.translate(w / 2, h / 2); g.rotate(-Math.PI / 2);
      g.fillStyle = C.bg; g.font = mono(s === 'cancel' ? 60 : 44); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(lab, 0, 2); g.restore();
    });
    const k = new THREE.Mesh(new THREE.CylinderGeometry(0.068, 0.072, 0.05, 40),
      [mat(C.muted, { roughness: .4 }), new THREE.MeshStandardMaterial({ map: face, roughness: .4 }), mat(C.muted)]);
    k.rotation.x = Math.PI / 2; k.position.set(cx, cy, FRONT + 0.085); k.userData.sym = s; k.userData.baseZ = k.position.z;
    VM.add(k); hit.push(k); keyMeshes[s] = k;
  });
  anchors.keys = keyMeshes[keySyms[0]];

  // circuit traces (δ: the wiring) — invisible until the dive reveals them
  const pts = [];
  const lcdP = new THREE.Vector3(COL.x, 3.0, FRONT + 0.064), slotP = new THREE.Vector3(COL.x - 0.12, 2.7, FRONT + 0.064);
  keySyms.forEach(s => { const k = keyMeshes[s].position; pts.push(k.clone().setZ(FRONT + 0.064), new THREE.Vector3(k.x, k.y, FRONT + 0.064).setX(COL.x + 0.2));
    pts.push(new THREE.Vector3(COL.x + 0.2, k.y, FRONT + 0.064), new THREE.Vector3(COL.x + 0.2, 3.0, FRONT + 0.064)); });
  pts.push(slotP, new THREE.Vector3(COL.x - 0.2, 2.7, FRONT + 0.064), new THREE.Vector3(COL.x - 0.2, 2.7, FRONT + 0.064), new THREE.Vector3(COL.x - 0.2, 3.0, FRONT + 0.064));
  pts.push(new THREE.Vector3(COL.x - 0.2, 3.0, FRONT + 0.064), lcdP);
  traces = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color: new THREE.Color(C.secondary), transparent: true, opacity: 0 }));
  VM.add(traces); anchors.traces = keyMeshes['cancel'];

  // buzzer grille (the trap's voice)
  buzzer = new THREE.Group(); buzzer.position.set(COL.x, 1.35, FRONT + 0.065);
  const dotM = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.bg) });
  for (let a = 0; a < 3; a++) for (let j = 0; j < 6 * a + (a ? 0 : 1); j++) {
    const ang = j / (6 * a || 1) * Math.PI * 2, d = new THREE.Mesh(new THREE.CircleGeometry(0.012, 10), dotM);
    d.position.set(Math.cos(ang) * a * 0.045, Math.sin(ang) * a * 0.045, 0); buzzer.add(d);
  }
  VM.add(buzzer); anchors.buzzer = buzzer;

  // return cup
  const cup = box(0.3, 0.2, 0.1, deep); cup.position.set(COL.x, 0.95, FRONT + 0.04); VM.add(cup);
  const cupRim = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.24, 0.01), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.primary), transparent: true, opacity: .5 }));
  cupRim.position.set(COL.x, 0.95, FRONT + 0.035); VM.add(cupRim);

  // coin tray in front of the machine: the physical Σ
  const tray = box(0.34 * COINS.length + 0.1, 0.03, 0.34, navy);
  tray.position.set(-DIM.W / 2 - 0.42, 1.2, FRONT + 0.2); VM.add(tray);
  const trayLeg = box(0.04, 1.2, 0.04, navy); trayLeg.position.set(-DIM.W / 2 - 0.42, 0.6, FRONT + 0.2); VM.add(trayLeg);
  COINS.forEach(([s, v], i) => {
    const c = coinMesh(v); c.position.set(tray.position.x - (COINS.length - 1) * 0.17 + i * 0.34, 1.232, FRONT + 0.2);
    c.userData.sym = s; c.userData.home = c.position.clone(); VM.add(c); hit.push(c); coinProto[s] = c;
  });
  anchors.tray = coinProto[COINS[0][0]];
  drawLCD(null);
}

function helix(r, len, turns, material) {
  class H extends THREE.Curve { getPoint(t) { const a = t * turns * Math.PI * 2; return new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, (t - .5) * len); } }
  return new THREE.Mesh(new THREE.TubeGeometry(new H(), 120, 0.009, 6, false), material);
}
function itemMesh(kind, h, material) {
  let m;
  if (kind === 0) { m = roundBox(0.3, h, 0.12, 0.05, material); }                       // bag
  else if (kind === 1) { m = roundBox(0.2, h, 0.16, 0.03, material); }                  // carton
  else if (kind === 2) { m = roundBox(0.34, h * 0.55, 0.06, 0.02, material); h *= .55; } // bar
  else { m = cyl(0.08, h, material); }                                                   // can
  m.userData.h = h; return m;
}
function coinMesh(v) {
  const face = canvasTex(128, 128, (g, w, h) => {
    g.fillStyle = '#d9dde3'; g.beginPath(); g.arc(w / 2, h / 2, w / 2, 0, 7); g.fill();
    g.strokeStyle = '#9aa3ad'; g.lineWidth = 6; g.beginPath(); g.arc(w / 2, h / 2, w / 2 - 10, 0, 7); g.stroke();
    g.fillStyle = C.bg; g.font = mono(v >= 10 ? 44 : 50); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('₹' + v, w / 2, h / 2 + 2);
  });
  const r = 0.085 + Math.min(v, 20) * 0.0022;
  const edge = mat('#b8bec6', { metalness: .85, roughness: .28 }), fm = new THREE.MeshStandardMaterial({ map: face, metalness: .6, roughness: .35 });
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.022, 40), [edge, fm, fm]); m.castShadow = true;
  return m;
}

/* LCD: shows balance AND the DFA state name — the first hint */
function drawLCD(ev) {
  if (!lcdTex) return;
  const g = lcdTex.userData.ctx, w = 512, h = 256, q = S.q;
  g.setTransform(2, 0, 0, 2, 0, 0);
  let big, msg, col = C.success;
  if (!ev) { big = '₹0'; msg = 'INSERT COIN'; }
  else if (ev.kind === 'accept') { big = 'SOLD'; msg = ev.out; }
  else if (ev.kind === 'coin') { big = '₹' + bal(ev.next); msg = 'CREDIT'; }
  else if (ev.kind === 'cancel') { big = '₹0'; msg = ev.out === '—' ? 'CANCELLED' : ev.out; }
  else if (ev.kind === 'blocked') { big = 'BEEP'; msg = 'PRESS RESET'; col = C.warning; }
  else { big = 'BEEP'; msg = ev.out; col = C.warning; }
  g.fillStyle = '#04070d'; g.fillRect(0, 0, w, h);
  g.fillStyle = 'rgba(125,226,176,.06)'; for (let y = 0; y < h; y += 4) g.fillRect(0, y, w, 1);
  g.shadowColor = col; g.shadowBlur = 14; g.fillStyle = col;
  g.font = mono(96); g.textBaseline = 'alphabetic'; g.fillText(big, 26, 150);
  g.shadowBlur = 0; g.font = mono(28, 500); g.fillText(msg.length > 26 ? msg.slice(0, 25) + '…' : msg, 28, 218);
  g.font = mono(34); g.textAlign = 'right'; g.fillStyle = col; g.fillText(ev ? ev.next : q, w - 24, 56);
  g.strokeStyle = col; g.lineWidth = 2; const tw = g.measureText(ev ? ev.next : q).width;
  g.strokeRect(w - 34 - tw, 20, tw + 20, 48); g.textAlign = 'left';
  lcdTex.needsUpdate = true;
}

/* ─── tiny tween engine ─── */
const tweens = [];
const ease = { out: t => 1 - Math.pow(1 - t, 3), in: t => t * t, inOut: t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2, lin: t => t };
function tween(dur, fn, e = ease.out, delay = 0) {
  if (REDUCED) { fn(1); return Promise.resolve(); }
  return new Promise(res => tweens.push({ t0: performance.now() + delay, dur, fn, e, res }));
}
function stepTweens(now) {
  for (let i = tweens.length - 1; i >= 0; i--) {
    const tw = tweens[i], k = (now - tw.t0) / tw.dur; if (k < 0) continue;
    tw.fn(tw.e(Math.min(1, k))); if (k >= 1) { tweens.splice(i, 1); tw.res(); }
  }
}

/* ─── physical reactions: one per kind of transition ─── */
let chain = Promise.resolve();
on(ev => { chain = chain.then(() => react(ev)).catch(() => {}); });

async function react(ev) {
  if (!R) return;
  if (!ev) { restock(); drawLCD(null); return; }
  const k = keyMeshes[ev.sym]; if (k) pressKey(k);
  switch (ev.kind) {
    case 'coin': await coinIn(ev.sym); drawLCD(ev); flash(slotRim, .35); break;
    case 'overpay': await coinIn(ev.sym); drawLCD(ev); shake(); await dropCoins(1, cfg.coins[ev.sym]); break;
    case 'cancel': drawLCD(ev); await dropCoins(Math.min(5, Math.round(bal(ev.prev) / G)), G); break;
    case 'accept': drawLCD(ev); await vend(ev); break;
    case 'short': drawLCD(ev); rowAlarm(ev.sym); shake(); break;
    default: drawLCD(ev); shake();
  }
}
function pressKey(k) {
  return tween(110, t => { k.position.z = k.userData.baseZ - 0.025 * Math.sin(t * Math.PI); }, ease.lin);
}
function flash(m, base) { return tween(500, t => { m.material.opacity = base + (1 - t) * .6; }); }
async function coinIn(sym) {
  const proto = coinProto[sym], c = proto.clone(); VM.add(c);
  const from = proto.userData.home.clone(), slot = anchors.slot.position, to = new THREE.Vector3(slot.x, slot.y, FRONT + 0.2);
  proto.visible = false;
  await tween(520, t => {
    c.position.lerpVectors(from, to, t); c.position.y += Math.sin(t * Math.PI) * 0.35;
    c.rotation.set(Math.PI / 2 * t, 0, Math.PI / 2 * t);
  }, ease.inOut);
  await tween(200, t => { c.position.z = FRONT + 0.2 - 0.2 * t; }, ease.in);
  VM.remove(c);
  proto.visible = true; proto.scale.setScalar(.01);
  tween(260, t => proto.scale.setScalar(Math.max(.01, t)));
}
async function dropCoins(n, v) {
  for (let i = 0; i < n; i++) {
    const c = coinMesh(v); c.rotation.x = Math.PI / 2 * 0.25; VM.add(c); cupCoins.push(c);
    const x = COL.x - 0.07 + (cupCoins.length % 4) * 0.045, z = FRONT + 0.1;
    await tween(260, t => c.position.set(x, 1.12 - 0.22 * t, z), ease.in);
    tween(160, t => { c.position.y = 0.9 + Math.sin(t * Math.PI) * 0.03; }, ease.out);
  }
}
async function vend(ev) {
  const row = rows.find(r => r.sym === ev.sym);
  const slotIt = row.items.find(x => !x.it.userData.gone) || row.items[1];
  const { it, coil } = slotIt; it.userData.gone = true;
  const z0 = it.position.z, y0 = it.position.y;
  await tween(900, t => { coil.rotation.z = -t * Math.PI * 2; it.position.z = z0 + 0.16 * t; }, ease.inOut);
  coil.rotation.z = 0;
  const yEnd = anchors.bayFloor + Math.min(it.userData.h, 0.3) / 2 + 0.02, zEnd = anchors.bayZ, zA = z0 + 0.16;
  await tween(460, t => { it.position.y = y0 + (yEnd - y0) * t; it.rotation.x = -t * Math.PI / 2 * (it.userData.h > .3 ? 1 : 0);
    it.position.z = zA + (zEnd - zA) * t; }, ease.in);
  tween(380, t => { flap.rotation.x = -Math.sin(t * Math.PI) * 0.7; });
  await tween(180, t => { it.position.y = yEnd + Math.sin(t * Math.PI) * 0.05; });
  const ch = bal(ev.prev) - cfg.products[ev.sym].price;
  if (ch > 0) await dropCoins(Math.min(4, Math.round(ch / G)), G);
}
function rowAlarm(sym) {
  const row = rows.find(r => r.sym === sym); if (!row) return;
  const m = row.strip.material, base = new THREE.Color(C.secondary), warn = new THREE.Color(C.warning);
  tween(900, t => { const on = Math.floor(t * 6) % 2 === 0 && t < 1; m.color.copy(on ? warn : base); m.opacity = on ? 1 : .55; }, ease.lin);
}
function shake() { return tween(320, t => { VM.position.x = Math.sin(t * Math.PI * 7) * 0.05 * (1 - t); }, ease.lin); }
function restock() {
  rows.forEach(r => r.items.forEach(({ it, coil }) => { it.position.copy(it.userData.home); it.rotation.copy(it.userData.homeRot); it.userData.gone = false; coil.rotation.z = 0; }));
  cupCoins.forEach(c => VM.remove(c)); cupCoins = []; flap.rotation.x = 0;
}

/* ─── pointer: hover + click the physical controls ─── */
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let hovered = null, drag = null, yaw = 0, yawT = 0;
function pick(e) {
  const r = canvas.getBoundingClientRect(); ptr.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
  ray.setFromCamera(ptr, camera); const h = ray.intersectObjects(hit, false)[0]; return h ? h.object : null;
}
// canvas sits under <main>; listen on the window and ignore clicks on real UI
function overUI(e) { return e.target.closest && e.target.closest('button, .panel, a, table, .chapter, .graph-wrap'); }
addEventListener('pointermove', e => {
  if (!R || diveP > .3 || overUI(e)) { if (hovered) { hovered = null; document.body.style.cursor = ''; } return; }
  if (drag) { yawT = Math.max(-.6, Math.min(.6, drag.yaw + (e.clientX - drag.x) / 300)); return; }
  hovered = pick(e); document.body.style.cursor = hovered ? 'pointer' : '';
});
addEventListener('pointerdown', e => { if (!R || diveP > .3 || overUI(e)) return; const h = pick(e);
  if (h) { runToken++; feed(h.userData.sym); } else drag = { x: e.clientX, yaw: yawT }; });
addEventListener('pointerup', () => { drag = null; });

/* ════════════════ scroll: hero → dive → brain ════════════════ */
const hero = document.getElementById('hero'), dive = document.getElementById('dive');
const heroPanel = hero.querySelector('.panel'), cue = hero.querySelector('.scroll-cue');
const pixels = document.getElementById('pixels'), flashEl = document.getElementById('blueprint-flash');
const diveText = document.getElementById('dive-text'), calloutBox = document.getElementById('callouts');
let diveP = 0, heroP = 0, stageOn = true;
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };

const CALLOUTS = [
  ['lcd', 'Q', 'the display is its memory: states', 'right', .06],
  ['slot', 'Σ', 'coins and keys are input symbols', 'left', .12],
  ['traces', 'δ', 'the wiring picks the next state', 'right', .18],
  ['q0', 'q₀', 'switched on: ₹0, waiting', 'left', .24],
  ['flap', 'F', 'something drops = accepted', 'left', .3],
  ['buzzer', 'q_dead', 'the buzzer: a trap with no exit', 'right', .36],
].map(([a, sym, txt, side, at]) => {
  const d = el('div', 'callout ' + side, `<span class="pin"></span><span class="rule"></span><span class="sym">${sym}</span><span class="txt">${txt}</span>`);
  calloutBox.append(d); return { a, d, at };
});
const DIVE_LINES = [[.0, ''], [.05, 'Every part of the machine is a piece of the math.'],
  [.44, 'Now look closer at the display…'], [.8, '']];

function onScroll() {
  const y = scrollY, vh = innerHeight;
  heroP = clamp(y / (vh * .6));
  const top = dive.offsetTop, len = dive.offsetHeight - vh;
  diveP = clamp((y - top) / len);
  heroPanel.style.opacity = 1 - heroP; heroPanel.style.transform = `translateY(${-heroP * 40}px)`;
  heroPanel.style.pointerEvents = heroP > .5 ? 'none' : 'auto';
  cue.style.opacity = 1 - clamp(heroP * 3);
  let line = ''; DIVE_LINES.forEach(([a, t]) => { if (diveP >= a) line = t; });
  if (diveText.dataset.t !== line) { diveText.style.opacity = 0; setTimeout(() => { diveText.textContent = line; diveText.dataset.t = line; diveText.style.opacity = line ? 1 : 0; }, 180); diveText.dataset.t = line; }
  pixels.style.opacity = smooth(.74, .86, diveP) * (1 - smooth(.9, 1, diveP));
  pixels.style.backgroundSize = `${7 + smooth(.8, 1, diveP) * 40}px ${7 + smooth(.8, 1, diveP) * 40}px`;
  flashEl.style.opacity = smooth(.88, 1, diveP);
  stageOn = diveP < .995;
  canvas.style.visibility = stageOn ? 'visible' : 'hidden';
  if (traces) traces.material.opacity = smooth(.12, .22, diveP) * (1 - smooth(.6, .75, diveP)) * .95;
}
addEventListener('scroll', onScroll, { passive: true });

/* camera keyframes: hero (machine left of centre) → ¾ reveal → into the LCD */
const lerp = (a, b, t) => a + (b - a) * t;
function camKey(p) {
  const wide = innerWidth > 980;
  const K0 = { pos: [wide ? 1.3 : 0.1, 2.35, 9.6], tgt: [wide ? 1.3 : 0.1, 2.05, 0], fov: 30 };
  const K1 = { pos: [3.1, 2.9, 6.4], tgt: [0.25, 2.05, 0.2], fov: 32 };
  const l = anchors.lcd ? anchors.lcd.position : { x: 0.8, y: 3.1 };
  const K2 = { pos: [l.x, l.y, FRONT + 0.3], tgt: [l.x, l.y, FRONT], fov: 26 };
  const a = smooth(0, .34, p), b = smooth(.42, .86, p);
  const mix = (k) => [0, 1, 2].map(i => lerp(lerp(K0[k][i], K1[k][i], a), K2[k][i], b));
  return { pos: mix('pos'), tgt: mix('tgt'), fov: lerp(lerp(K0.fov, K1.fov, a), K2.fov, b) };
}

const tmp = new THREE.Vector3();
function placeCallouts() {
  const vis = diveP > 0 && diveP < .5;
  CALLOUTS.forEach(c => {
    const show = vis && diveP > c.at && diveP < .46 && anchors[c.a];
    c.d.style.opacity = show ? 1 : 0;
    if (!anchors[c.a]) return;
    anchors[c.a].getWorldPosition(tmp); tmp.project(camera);
    c.d.style.left = ((tmp.x + 1) / 2 * innerWidth) + 'px';
    c.d.style.top = ((-tmp.y + 1) / 2 * innerHeight - 5) + 'px';
  });
}

function resize() {
  if (!R) return;
  R.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
}
addEventListener('resize', () => { resize(); onScroll(); });

let tPrev = performance.now();
function frame(now) {
  requestAnimationFrame(frame);
  stepTweens(now);
  if (!R || !stageOn) return;
  const dt = Math.min(.05, (now - tPrev) / 1000); tPrev = now;
  const k = camKey(diveP);
  yaw += ((drag ? yawT : (yawT *= .94)) - yaw) * Math.min(1, dt * 8);
  VM.rotation.y = yaw * (1 - smooth(0, .3, diveP)) + Math.sin(now / 2600) * 0.06 * (1 - smooth(0, .2, diveP)) * (REDUCED ? 0 : 1);
  camera.position.set(...k.pos); camera.lookAt(...k.tgt);
  if (Math.abs(camera.fov - k.fov) > .01) { camera.fov = k.fov; camera.updateProjectionMatrix(); }
  hit.forEach(m => { const on = m === hovered; if (m.material[0]) m.material[0].emissive = new THREE.Color(on ? C.secondary : '#000'); if (m.material[0]) m.material[0].emissiveIntensity = on ? .5 : 0; });
  R.render(scene, camera);
  placeCallouts();
}

/* ════════════════ the brain: SVG state diagram ════════════════ */
const NS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('graph');
const sv = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.append(e); return e; };
const BAL = M.states.filter(q => bal(q) !== null).sort((a, b) => bal(a) - bal(b));
const OTHER = M.states.filter(q => bal(q) === null);
const P = {}, RAD = 36;
BAL.forEach((q, i) => { const t = BAL.length > 1 ? i / (BAL.length - 1) : 0; P[q] = { x: 95 + t * 600, y: 420 - Math.sin(Math.PI * t) * 165 }; });
OTHER.forEach((q, i) => {
  if (isFinal(q)) P[q] = { x: 880, y: 160 };
  else if (q === 'q_dead') P[q] = { x: 880, y: 500 };
  else P[q] = { x: 800, y: 340 + i * 70 };
});

const defs = sv('defs', {}, svg);
[['m-muted', C.muted], ['m-text', C.text], ['m-blue', C.secondary]].forEach(([id, c]) => {
  const m = sv('marker', { id, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse' }, defs);
  sv('path', { d: 'M0,0 L10,5 L0,10 z', fill: c }, m);
});
const gEdges = sv('g', {}, svg), gNodes = sv('g', {}, svg), gNaive = sv('g', { class: 'naive' }, svg),
  gGhost = sv('g', { class: 'ghosts' }, svg), gCap = sv('g', { class: 'capline' }, svg);

// group arrows by (from, to) like core.render does
const EDGES = {};
M.states.forEach(u => M.symbols.forEach(a => { const v = M.delta[u][a], k = u + '>' + v; (EDGES[k] = EDGES[k] || { u, v, syms: [] }).syms.push(a); }));
function geom(u, v) {
  const a = P[u], b = P[v];
  if (u === v) {
    const up = v === 'q_dead' ? 1 : -1;
    const s = { x: a.x - 14, y: a.y + up * RAD * .9 }, e = { x: a.x + 14, y: a.y + up * RAD * .9 };
    return { d: `M${s.x},${s.y} C${a.x - 56},${a.y + up * 100} ${a.x + 56},${a.y + up * 100} ${e.x},${e.y}`, lx: a.x, ly: a.y + up * 88 };
  }
  const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L, mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
  const back = v === M.start, toEnd = v === 'q_dead' || isFinal(v);
  const k = back ? .3 * L : toEnd ? .1 * L : .2 * L + 8;
  const c1 = { x: mx + nx * k, y: my + ny * k }, c2 = { x: mx - nx * k, y: my - ny * k };
  const c = back ? (c1.y > c2.y ? c1 : c2) : toEnd && v === 'q_dead' ? (c1.y > c2.y ? c1 : c2) : (c1.y < c2.y ? c1 : c2);
  const nrm = (p, q) => { const l = Math.hypot(q.x - p.x, q.y - p.y); return { x: (q.x - p.x) / l, y: (q.y - p.y) / l }; };
  const d1 = nrm(a, c), d2 = nrm(b, c);
  const s = { x: a.x + d1.x * RAD, y: a.y + d1.y * RAD }, e = { x: b.x + d2.x * (RAD + 3), y: b.y + d2.y * (RAD + 3) };
  return { d: `M${s.x},${s.y} Q${c.x},${c.y} ${e.x},${e.y}`, lx: .25 * s.x + .5 * c.x + .25 * e.x, ly: .25 * s.y + .5 * c.y + .25 * e.y };
}
Object.values(EDGES).forEach(E => {
  const g = geom(E.u, E.v); const grp = sv('g', { class: 'edge' }, gEdges);
  E.path = sv('path', { d: g.d, 'marker-end': 'url(#m-muted)' }, grp);
  const t = sv('text', { x: g.lx, y: g.ly }, grp); t.textContent = E.syms.sort().join(', ');
  E.g = grp;
});
// start arrow
const s0 = P[M.start]; sv('line', { x1: s0.x - 78, y1: s0.y, x2: s0.x - RAD - 4, y2: s0.y, class: 'startarrow', 'marker-end': 'url(#m-muted)' }, gNodes);
const NODES = {};
M.states.forEach(q => {
  const p = P[q], cls = 'node' + (isFinal(q) ? ' accept' : '') + (q === 'q_dead' ? ' dead' : '');
  const g = sv('g', { class: cls, transform: `translate(${p.x},${p.y})` }, gNodes);
  sv('circle', { class: 'ring', r: RAD }, g);
  if (isFinal(q)) sv('circle', { class: 'inner', r: RAD - 5 }, g);
  const t = sv('text', { class: 'name' }, g); t.textContent = q;
  const cap = sv('text', { class: 'cap', y: RAD + 18 }, g);
  cap.textContent = bal(q) !== null ? '₹' + bal(q) : isFinal(q) ? 'accept' : q === 'q_dead' ? 'trap' : '';
  NODES[q] = g;
});
const token = sv('circle', { class: 'token', r: 8, opacity: 0 }, svg);

function paintGraph(ev) {
  Object.values(NODES).forEach(g => g.classList.remove('cur', 'prev'));
  NODES[S.q].classList.add('cur');
  if (ev && ev.prev !== ev.next) NODES[ev.prev].classList.add('prev');
  Object.values(EDGES).forEach(E => {
    const taken = ev && E.u === ev.prev && E.v === ev.next;
    E.g.classList.toggle('out', E.u === S.q && !taken);
    E.g.classList.toggle('taken', !!taken);
    E.path.setAttribute('marker-end', taken ? 'url(#m-blue)' : E.u === S.q ? 'url(#m-text)' : 'url(#m-muted)');
  });
  document.getElementById('g-state').textContent = S.q;
  document.getElementById('g-readout').innerHTML = formal(ev);
  if (ev && !REDUCED) {                        // the pink token travels the arrow
    const E = EDGES[ev.prev + '>' + ev.next], len = E.path.getTotalLength(), t0 = performance.now();
    token.setAttribute('opacity', 1);
    (function run(now) { const k = Math.min(1, (now - t0) / 650), pt = E.path.getPointAtLength(ease.inOut(k) * len);
      token.setAttribute('cx', pt.x); token.setAttribute('cy', pt.y); if (k < 1) requestAnimationFrame(run); else token.setAttribute('opacity', 0); })(t0);
  }
  paintTable(ev); paintLambda(ev);
}
on(paintGraph);

/* δ table */
const dtable = document.getElementById('dtable');
const ROWS = [...BAL, ...OTHER], SYMS = [...COINS.map(c => c[0]), 'cancel', ...PRODS.map(p => p[0])];
dtable.innerHTML = '<tr><th class="rowh">δ</th>' + SYMS.map(a => `<th>${a}</th>`).join('') + '</tr>' +
  ROWS.map(q => `<tr data-q="${q}"><th class="rowh">${q}</th>` + SYMS.map(a => {
    const v = M.delta[q][a]; return `<td data-q="${q}" data-a="${a}" class="${v === 'q_dead' ? 'dead' : isFinal(v) ? 'acc' : ''}">${v}</td>`;
  }).join('') + '</tr>').join('');
dtable.addEventListener('mouseover', e => { const td = e.target.closest('td'); Object.values(EDGES).forEach(E => E.g.classList.remove('hl'));
  if (td) EDGES[td.dataset.q + '>' + M.delta[td.dataset.q][td.dataset.a]].g.classList.add('hl'); });
dtable.addEventListener('mouseleave', () => Object.values(EDGES).forEach(E => E.g.classList.remove('hl')));
function paintTable(ev) {
  dtable.querySelectorAll('tr').forEach(tr => tr.classList.toggle('cur', tr.dataset.q === S.q));
  dtable.querySelectorAll('td').forEach(td => td.classList.toggle('taken', !!ev && td.dataset.q === ev.prev && td.dataset.a === ev.sym));
}

/* λ panel */
const ltable = document.getElementById('ltable');
function paintLambda(ev) {
  document.getElementById('split-d').textContent = ev ? `${ev.prev} → ${ev.next}` + (isFinal(ev.next) ? '  ✓ accept' : ev.next === 'q_dead' ? '  ✕ trap' : '') : 'waiting for input';
  document.getElementById('split-l').textContent = ev ? ev.out : '—';
  ltable.innerHTML = `<tr><td colspan="2" style="color:var(--muted)">λ(${S.q}, a) for every symbol a:</td></tr>` +
    SYMS.map(a => { const o = M.lambda[S.q][a], cls = o.startsWith('BEEP') ? 'beep' : o === '—' ? '' : 'give';
      return `<tr><td>${a}</td><td class="${cls}">${o}</td></tr>`; }).join('');
}

/* accept / trap strings: real strings, run live */
const stringBox = document.getElementById('strings');
scenarios().forEach(([name, seq]) => {
  let q = M.start; seq.forEach(a => { q = M.delta[q][a]; });
  const ok = isFinal(q), dead = q === 'q_dead';
  const res = ok ? 'ACCEPT' : dead ? 'TRAP' : 'NOT ACCEPTED (ends in ' + q + ')';
  const b = el('button', '', `<span>${seq.join(' ')}</span><span class="res ${ok ? 'ok' : dead ? 'bad' : ''}">${res} · ${name}</span>`);
  b.onclick = () => play(seq, null); stringBox.append(b);
});

/* minimisation: naive → minimal, using the backend's own equivalence classes */
const naive = M.naive, merged = naive.states.filter(q => !M.states.includes(q));
document.getElementById('min-from').textContent = naive.states.length;
document.getElementById('min-to').textContent = M.states.length;
document.getElementById('n-states').firstChild.textContent = M.states.length;
document.getElementById('states-note').innerHTML = `${BAL.length} balance states (₹0 to ₹${cfg.cap} in steps of ₹${G}), plus <b class="mono">q_done</b> and <b class="mono">q_dead</b>.`;
document.getElementById('cap-label').textContent = `₹${cfg.cap} cap`;
document.getElementById('min-note').innerHTML = merged.length
  ? `Merged here: <span class="mono">${merged.join(', ')}</span> → <b class="mono">${naive.name_of[merged[0]]}</b>. The algorithm ran ${naive.steps} refinement step${naive.steps === 1 ? '' : 's'}.`
  : 'This configuration was already minimal.';
const byTarget = {};
merged.forEach(q => (byTarget[naive.name_of[q]] = byTarget[naive.name_of[q]] || []).push(q));
Object.entries(byTarget).forEach(([t, qs]) => {
  const c = P[t]; if (!c) return;
  qs.forEach((q, i) => {
    const cols = Math.ceil(Math.sqrt(qs.length)), gap = 64;
    const x = c.x - 90 - (cols - 1 - (i % cols)) * gap, y = Math.min(600, Math.max(40, c.y - 20 + Math.floor(i / cols) * gap));
    const g = sv('g', { transform: `translate(${x},${y})` }, gNaive); g.dataset.to = `translate(${c.x},${c.y})`; g.dataset.from = `translate(${x},${y})`;
    sv('circle', { r: 26 }, g);
    const m = /^done_(\w+?)_ch(\d+)$/.exec(q), t1 = sv('text', { y: m ? -6 : 0 }, g); t1.textContent = m ? m[1] : q;
    if (m) { const t2 = sv('text', { y: 9 }, g); t2.textContent = '+₹' + m[2]; }
  });
});
let mergeTimer;
function runMerge() {
  clearTimeout(mergeTimer);
  svg.classList.remove('merging', 'merged');
  gNaive.querySelectorAll('g').forEach(g => g.setAttribute('transform', g.dataset.from));
  mergeTimer = setTimeout(() => {
    svg.classList.add('merging');
    gNaive.querySelectorAll('g').forEach(g => g.setAttribute('transform', g.dataset.to));
    setTimeout(() => svg.classList.add('merged'), 700);
  }, 1300);
}
document.getElementById('replay-min').onclick = runMerge;

/* regularity: states that would exist without the cap */
const last = P[BAL[BAL.length - 1]];
[1, 2, 3].forEach(i => { const midY = OTHER.length ? (Math.min(...OTHER.map(q => P[q].y)) + Math.max(...OTHER.map(q => P[q].y))) / 2 : last.y;
  const at = sv('g', { transform: `translate(${Math.min(950, last.x + i * 85)},${midY})` }, gGhost);
  const g = sv('g', {}, at); sv('circle', { r: 28 }, g); const t = sv('text', {}, g); t.textContent = 'q' + (cfg.cap + i * G); });
sv('line', { x1: last.x + 52, y1: 70, x2: last.x + 52, y2: 600 }, gCap);
const capT = sv('text', { x: last.x + 62, y: 90 }, gCap); capT.textContent = `cap ₹${cfg.cap}`;

/* chapters drive the diagram's emphasis */
const tuple = document.getElementById('tuple');
const io = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  document.querySelectorAll('.chapter').forEach(c => c.classList.toggle('active', c === e.target));
  const mode = e.target.dataset.mode;
  svg.setAttribute('class', 'mode-' + mode);
  if (mode === 'min') runMerge();
}), { rootMargin: '-45% 0px -45% 0px' });
document.querySelectorAll('.chapter').forEach(c => io.observe(c));
new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) {
  tuple.classList.add('in'); tuple.querySelectorAll('span').forEach((s, i) => { s.style.transitionDelay = i * 45 + 'ms'; }); } }),
  { threshold: .6 }).observe(tuple);
const partModes = { Q: 'states', S: 'delta', d: 'delta', q0: 'intro', F: 'fates' };
tuple.querySelectorAll('.part').forEach(s => {
  s.onmouseenter = () => svg.setAttribute('class', 'mode-' + partModes[s.dataset.p]);
  s.onmouseleave = () => svg.setAttribute('class', 'mode-intro');
});

document.getElementById('to-top').onclick = () => scrollTo({ top: 0, behavior: 'smooth' });

/* go */
if (R) buildScene();
resize(); onScroll();
subs.forEach(f => f(null));
requestAnimationFrame(frame);
if (!R) { canvas.style.display = 'none'; document.querySelector('.lede').insertAdjacentHTML('afterend',
  '<p class="lede" style="color:var(--warning)">3D is unavailable in this browser. Everything below still works.</p>'); }
})();
