// route.js — Sprint routing visualizer on a real OSMnx street network

const STEPS_PER_FRAME   = 1;    // edges revealed per frame
const PATH_REVEAL_SPEED = 3;    // path sweep: 3 edges per frame
const EDGE_FADE_FRAMES  = 50;   // frames for new edge to reach full opacity

// Colors
const BG           = '#010008';
const SOURCE_COLOR = '#44e87a';
const DEST_COLOR   = '#ff4466';

// 4-pass glow for explored edges: [strokeStyle, lineWidth]
const EDGE_GLOW_PASSES = [
  ['rgba(100, 28, 0, 0.10)', 44],     // wide ambient bloom
  ['rgba(200, 70, 5, 0.28)', 18],     // area glow
  ['rgba(248, 135, 22, 0.56)', 5],    // mid glow
  ['rgba(255, 215, 90, 0.88)', 1.2],  // hot white-gold core
];

// Fallback JS street rendering (used when PNG image is unavailable)
const ROAD_COLORS = [
  'rgba(136,196,247,0.18)', 'rgba(136,196,247,0.28)', 'rgba(136,196,247,0.42)',
  'rgba(136,196,247,0.58)', 'rgba(136,196,247,0.74)', 'rgba(136,196,247,0.90)',
];
const ROAD_WIDTHS = [0.5, 0.8, 1.1, 1.6, 2.2, 3.0];

const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');

// ── Data ─────────────────────────────────────────────────────────────────────
let nodeMap   = {};   // id -> { x, y, sx, sy }
let adjList   = {};   // id -> [{ id, len }]
let allEdges  = [];   // [{ u, v, rank }]  — kept for JS fallback rendering
let cityLabel  = '';
let cityAspect = 1;   // x_range / y_range from JSON
let cityImg    = null;
let imgRect    = null; // { x, y, w, h } in canvas pixels

function loadImage(url) {
  return new Promise(resolve => {
    const img = new Image();
    img.onload  = () => resolve(img);
    img.onerror = () => resolve(null);  // graceful fallback to JS streets
    img.src = url;
  });
}

export async function loadCity(slug) {
  const base = `./${slug}`;
  const [data, img] = await Promise.all([
    fetch(`${base}.json`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
    loadImage(`${base}.png`),
  ]);
  cityLabel  = data.city ?? '';
  cityAspect = data.aspect ?? 1;
  cityImg    = img;
  nodeMap = {}; adjList = {}; allEdges = [];

  for (const [id, n] of Object.entries(data.nodes)) {
    nodeMap[id] = { x: n.x, y: n.y, sx: 0, sy: 0 };
    adjList[id] = [];
  }
  for (const e of data.edges) {
    allEdges.push({ u: e.u, v: e.v, rank: e.rank ?? 0 });
    adjList[e.u].push({ id: e.v, len: e.len });
    adjList[e.v].push({ id: e.u, len: e.len });
  }
  computeScreenCoords();
}

function computeScreenCoords() {
  const W = canvas.width, H = canvas.height;
  const PAD   = 0.06;
  const availW = W * (1 - 2 * PAD);
  const availH = H * (1 - 2 * PAD);

  // Fit the map image (cityAspect = w/h) into the available area
  let imgW, imgH;
  if (cityAspect >= availW / availH) {
    imgW = availW;
    imgH = availW / cityAspect;
  } else {
    imgH = availH;
    imgW = availH * cityAspect;
  }
  const imgX = PAD * W + (availW - imgW) / 2;
  const imgY = PAD * H + (availH - imgH) / 2;
  imgRect = { x: imgX, y: imgY, w: imgW, h: imgH };

  for (const n of Object.values(nodeMap)) {
    n.sx = imgX + n.x * imgW;
    n.sy = imgY + n.y * imgH;
  }
}

export function onResize() {
  computeScreenCoords();
  draw();
}

// ── Nearest-node hit-test ─────────────────────────────────────────────────────
function nearestNode(px, py) {
  let best = null, bestD = Infinity;
  for (const [id, n] of Object.entries(nodeMap)) {
    const d = (n.sx - px) ** 2 + (n.sy - py) ** 2;
    if (d < bestD) { bestD = d; best = id; }
  }
  return best;
}

// ── Min-heap ─────────────────────────────────────────────────────────────────
class MinHeap {
  constructor() { this.h = []; }
  push(pri, val) {
    this.h.push([pri, val]);
    let i = this.h.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (this.h[p][0] <= this.h[i][0]) break;
      [this.h[p], this.h[i]] = [this.h[i], this.h[p]]; i = p;
    }
  }
  pop() {
    const top = this.h[0], last = this.h.pop();
    if (this.h.length) {
      this.h[0] = last; let i = 0;
      while (true) {
        let m = i, l = 2*i+1, r = 2*i+2;
        if (l < this.h.length && this.h[l][0] < this.h[m][0]) m = l;
        if (r < this.h.length && this.h[r][0] < this.h[m][0]) m = r;
        if (m === i) break;
        [this.h[m], this.h[i]] = [this.h[i], this.h[m]]; i = m;
      }
    }
    return top;
  }
  get size() { return this.h.length; }
}

function reconstructPath(prev, src, dst) {
  const path = []; let cur = dst;
  while (cur !== undefined && cur !== src) { path.unshift(cur); cur = prev.get(cur); }
  if (cur === src) { path.unshift(src); return path; }
  return [];
}

// ── Algorithms ───────────────────────────────────────────────────────────────
export function* bfsAlgo(state) {
  const { src, dst, visited, frontier, prev } = state;
  const queue = [src]; visited.add(src);
  while (queue.length) {
    frontier.clear();
    const cur = queue.shift(); state.steps++;
    if (cur === dst) { state.path = reconstructPath(prev, src, dst); return; }
    for (const nb of adjList[cur] ?? []) {
      if (!visited.has(nb.id)) {
        visited.add(nb.id); frontier.add(nb.id);
        prev.set(nb.id, cur); queue.push(nb.id);
      }
    }
    yield;
  }
  state.path = [];
}

export function* dfsAlgo(state) {
  const { src, dst, visited, frontier, prev } = state;
  const stack = [src]; visited.add(src);
  while (stack.length) {
    frontier.clear();
    const cur = stack.pop(); state.steps++;
    if (cur === dst) { state.path = reconstructPath(prev, src, dst); return; }
    for (const nb of adjList[cur] ?? []) {
      if (!visited.has(nb.id)) {
        visited.add(nb.id); frontier.add(nb.id);
        prev.set(nb.id, cur); stack.push(nb.id);
      }
    }
    yield;
  }
  state.path = [];
}

export function* dijkstraAlgo(state) {
  const { src, dst, visited, frontier, prev } = state;
  const dist = new Map([[src, 0]]);
  const pq = new MinHeap(); pq.push(0, src); visited.add(src);
  while (pq.size) {
    frontier.clear();
    const [d, cur] = pq.pop(); state.steps++;
    if (cur === dst) { state.path = reconstructPath(prev, src, dst); return; }
    if (d > (dist.get(cur) ?? Infinity)) { yield; continue; }
    for (const nb of adjList[cur] ?? []) {
      const nd = d + nb.len;
      if (nd < (dist.get(nb.id) ?? Infinity)) {
        dist.set(nb.id, nd); prev.set(nb.id, cur);
        if (!visited.has(nb.id)) { visited.add(nb.id); frontier.add(nb.id); }
        pq.push(nd, nb.id);
      }
    }
    yield;
  }
  state.path = [];
}

function heuristic(a, b) {
  const na = nodeMap[a], nb = nodeMap[b];
  if (!na || !nb) return 0;
  return Math.hypot(na.sx - nb.sx, na.sy - nb.sy);
}

export function* astarAlgo(state) {
  const { src, dst, visited, frontier, prev } = state;
  const g = new Map([[src, 0]]);
  const pq = new MinHeap(); pq.push(heuristic(src, dst), src); visited.add(src);
  while (pq.size) {
    frontier.clear();
    const [, cur] = pq.pop(); state.steps++;
    if (cur === dst) { state.path = reconstructPath(prev, src, dst); return; }
    const gCur = g.get(cur) ?? Infinity;
    for (const nb of adjList[cur] ?? []) {
      const ng = gCur + nb.len;
      if (ng < (g.get(nb.id) ?? Infinity)) {
        g.set(nb.id, ng); prev.set(nb.id, cur);
        if (!visited.has(nb.id)) { visited.add(nb.id); frontier.add(nb.id); }
        pq.push(ng + heuristic(nb.id, dst), nb.id);
      }
    }
    yield;
  }
  state.path = [];
}

// ── Drawing ───────────────────────────────────────────────────────────────────
function draw() {
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, W, H);

  // ── City map background ───────────────────────────────────────────────────
  if (cityImg && imgRect) {
    ctx.filter = 'brightness(1.7) contrast(1.35) saturate(1.2)';
    ctx.drawImage(cityImg, imgRect.x, imgRect.y, imgRect.w, imgRect.h);
    ctx.filter = 'none';
  } else if (allEdges.length) {
    // Fallback: draw streets in JS (no PNG available)
    for (let rank = 0; rank <= 5; rank++) {
      ctx.strokeStyle = ROAD_COLORS[rank];
      ctx.lineWidth   = ROAD_WIDTHS[rank];
      ctx.lineCap     = 'round';
      ctx.beginPath();
      for (const e of allEdges) {
        if (e.rank !== rank) continue;
        const u = nodeMap[e.u], v = nodeMap[e.v];
        if (!u || !v) continue;
        ctx.moveTo(u.sx, u.sy);
        ctx.lineTo(v.sx, v.sy);
      }
      ctx.stroke();
    }
  }

  if (anim) {
    ctx.lineCap  = 'round';
    ctx.lineJoin = 'round';
    const curFrame = anim.frame ?? 0;

    // ── Explored edges — additive glow with per-edge fade-in ─────────────
    if (anim.prev.size > 0) {
      ctx.globalCompositeOperation = 'lighter';

      // Separate mature (age >= 18, full opacity) from fresh (fading in)
      const matureSegs = [], freshSegs = [];
      for (const [id, parentId] of anim.prev) {
        const n = nodeMap[id], p = nodeMap[parentId];
        if (!n || !p) continue;
        const age = curFrame - (anim.edgeAge.get(`${parentId}→${id}`) ?? 0);
        const fa  = Math.min(1, age / EDGE_FADE_FRAMES);
        if (fa >= 1) matureSegs.push([p.sx, p.sy, n.sx, n.sy]);
        else         freshSegs.push([p.sx, p.sy, n.sx, n.sy, fa]);
      }

      // Mature edges — 3-pass batch
      if (matureSegs.length) {
        for (const [style, lw] of EDGE_GLOW_PASSES) {
          ctx.strokeStyle = style; ctx.lineWidth = lw;
          ctx.beginPath();
          for (const [x1, y1, x2, y2] of matureSegs) {
            ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
          }
          ctx.stroke();
        }
      }

      // Fresh edges — per-edge with fade alpha
      for (const [x1, y1, x2, y2, fa] of freshSegs) {
        ctx.globalAlpha = fa;
        for (const [style, lw] of EDGE_GLOW_PASSES) {
          ctx.strokeStyle = style; ctx.lineWidth = lw;
          ctx.beginPath();
          ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }

    // ── Frontier: brightest edges at the active exploration front ─────────
    if (anim.frontier.size > 0) {
      const pulse = 0.5 + 0.5 * Math.sin(Date.now() * 0.005);
      ctx.globalCompositeOperation = 'lighter';

      for (const id of anim.frontier) {
        const parentId = anim.prev.get(id);
        if (!parentId) continue;
        const n = nodeMap[id], p = nodeMap[parentId];
        if (!n || !p) continue;
        const age = curFrame - (anim.edgeAge.get(`${parentId}→${id}`) ?? 0);
        const fa  = Math.min(1, age / EDGE_FADE_FRAMES);
        ctx.globalAlpha = fa;

        ctx.strokeStyle = `rgba(230, 110, 10, ${0.22 + 0.14 * pulse})`;
        ctx.lineWidth   = 20;
        ctx.beginPath(); ctx.moveTo(p.sx, p.sy); ctx.lineTo(n.sx, n.sy); ctx.stroke();

        ctx.strokeStyle = `rgba(255, 220, 90, ${0.85 + 0.15 * pulse})`;
        ctx.lineWidth   = 2.8;
        ctx.beginPath(); ctx.moveTo(p.sx, p.sy); ctx.lineTo(n.sx, n.sy); ctx.stroke();
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }

    // ── Final path — brilliant orange, additive glow, dest → source ─────────
    if (anim.path && pathReveal > 1) {
      const total = anim.path.length;
      const limit = Math.min(pathReveal, total);
      // Reveal from destination (end of array) backwards toward source
      const start = total - limit;

      ctx.beginPath();
      let first = true;
      for (let i = start; i < total; i++) {
        const n = nodeMap[anim.path[i]];
        if (!n) continue;
        if (first) { ctx.moveTo(n.sx, n.sy); first = false; }
        else        { ctx.lineTo(n.sx, n.sy); }
      }

      ctx.globalCompositeOperation = 'lighter';
      // Pass 1: wide bloom
      ctx.strokeStyle = 'rgba(200, 80, 10, 0.28)';
      ctx.lineWidth   = 20;
      ctx.stroke();
      // Pass 2: mid
      ctx.strokeStyle = 'rgba(255, 140, 40, 0.55)';
      ctx.lineWidth   = 8;
      ctx.stroke();
      // Pass 3: hot core
      ctx.strokeStyle = 'rgba(255, 200, 100, 0.90)';
      ctx.lineWidth   = 2.5;
      ctx.stroke();
      ctx.globalCompositeOperation = 'source-over';
    }
  }

  // ── Source / dest dots ────────────────────────────────────────────────────
  if (source) drawNodeDot(source, SOURCE_COLOR);
  if (dest)   drawNodeDot(dest,   DEST_COLOR);
}

function drawNodeDot(id, color) {
  const n = nodeMap[id];
  if (!n) return;
  ctx.fillStyle = ctx.shadowColor = color;
  ctx.shadowBlur = 14;
  ctx.beginPath();
  ctx.arc(n.sx, n.sy, 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function updateStats() {
  const el = document.getElementById('stats');
  if (!el || !anim) return;
  el.style.display = 'flex';
  const pathLen = anim.path
    ? (anim.path.length > 1 ? anim.path.length - 1 + ' edges' : 'no path')
    : '...';
  const ms = anim.elapsed != null
    ? anim.elapsed.toFixed(1)
    : (performance.now() - anim.startTime).toFixed(1);
  el.innerHTML =
    `<span>${anim.visited.size} visited</span>` +
    `<span>path: ${pathLen}</span>` +
    `<span>${ms} ms</span>`;
}

function setRunBtn(enabled) {
  const btn = document.getElementById('runBtn');
  if (btn) btn.disabled = !enabled;
}

// ── Animation loop ────────────────────────────────────────────────────────────
let anim       = null;
let pathReveal = 0;
let running    = false;
let rafId      = null;

function animate() {
  if (!anim) return;
  if (!anim.done) {
    for (let i = 0; i < STEPS_PER_FRAME; i++) {
      const r = anim.gen.next();
      if (r.done) { anim.done = true; anim.elapsed = performance.now() - anim.startTime; break; }
    }
    // Stamp newly-added edges with the current frame number
    for (const [id, parentId] of anim.prev) {
      const key = `${parentId}→${id}`;
      if (!anim.edgeAge.has(key)) anim.edgeAge.set(key, anim.frame);
    }
    anim.frame++;
    draw(); updateStats();
    rafId = requestAnimationFrame(animate);
    return;
  }
  if (anim.path && pathReveal < anim.path.length) {
    pathReveal = Math.min(pathReveal + PATH_REVEAL_SPEED, anim.path.length);
    draw(); updateStats();
    rafId = requestAnimationFrame(animate);
    return;
  }
  draw(); updateStats();
  running = false;
  setRunBtn(true);
}

// ── Public API ────────────────────────────────────────────────────────────────
let source        = null;
let dest          = null;
let clickPhase    = 0;
let currentAlgoFn = bfsAlgo;

export function init() {
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null; running = false;
  source = null; dest = null; clickPhase = 0;
  anim = null; pathReveal = 0;
  const statsEl = document.getElementById('stats');
  if (statsEl) statsEl.style.display = 'none';
  setRunBtn(false);
  draw();
}

export function setAlgo(fn) { currentAlgoFn = fn; }

export function run() {
  if (running || !source || !dest) return;
  if (rafId) cancelAnimationFrame(rafId);
  running = true; pathReveal = 0;
  setRunBtn(false);
  const state = {
    src: source, dst: dest,
    visited: new Set(), frontier: new Set(), prev: new Map(),
    path: null, done: false, steps: 0, elapsed: null,
    startTime: performance.now(),
    edgeAge: new Map(), frame: 0,
  };
  state.gen = currentAlgoFn(state);
  anim = state;
  rafId = requestAnimationFrame(animate);
}

export function handleClick(px, py) {
  if (running) return;
  const id = nearestNode(px, py);
  if (!id) return;
  if (clickPhase === 0) {
    source = id; dest = null; clickPhase = 1; anim = null; draw();
    const statsEl = document.getElementById('stats');
    if (statsEl) statsEl.style.display = 'none';
  } else if (clickPhase === 1) {
    if (id === source) return;
    dest = id; clickPhase = 2; anim = null; draw(); setRunBtn(true);
  } else {
    source = null; dest = null; clickPhase = 0;
    anim = null; pathReveal = 0; draw();
    const statsEl = document.getElementById('stats');
    if (statsEl) statsEl.style.display = 'none';
    setRunBtn(false);
  }
}

export function getCityLabel() { return cityLabel; }
