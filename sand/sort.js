// ─────────────────────────────────────────────
//  Config
// ─────────────────────────────────────────────
const ARRAY_SIZE  = 200;
const BAR_WIDTH   = 4;
const ALGO_HEIGHT = 130;
const CANVAS_W    = ARRAY_SIZE * BAR_WIDTH;  // 800
const CANVAS_H    = ALGO_HEIGHT * 6;         // 780

const BG        = '#010008';
const BAR_COLOR = 'rgba(120, 185, 255, 0.45)';
const CMP_COLOR = '#88c4f7';
const SWP_COLOR = '#e8f4ff';
const SEP_COLOR = 'rgba(255, 255, 255, 0.05)';
const TEXT_DIM  = 'rgba(255, 255, 255, 0.24)';
const TEXT_DONE = 'rgba(136, 196, 247, 0.55)';

// ─────────────────────────────────────────────
//  Sorting generators  — yield { idx, swapIdx? }
// ─────────────────────────────────────────────
function* bubbleSort(arr) {
  const n = arr.length;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n - i - 1; j++) {
      if (arr[j] > arr[j + 1]) {
        [arr[j], arr[j + 1]] = [arr[j + 1], arr[j]];
        yield { idx: j, swapIdx: j + 1 };
      } else {
        yield { idx: j };
      }
    }
  }
}

function* insertionSort(arr) {
  for (let i = 1; i < arr.length; i++) {
    const key = arr[i];
    let j = i - 1;
    while (j >= 0 && arr[j] > key) {
      arr[j + 1] = arr[j];
      j--;
      yield { idx: j + 1, swapIdx: j + 2 };
    }
    arr[j + 1] = key;
    yield { idx: j + 1 };
  }
}

function* selectionSort(arr) {
  const n = arr.length;
  for (let i = 0; i < n; i++) {
    let minIdx = i;
    for (let j = i + 1; j < n; j++) {
      if (arr[j] < arr[minIdx]) minIdx = j;
      yield { idx: j };
    }
    if (minIdx !== i) {
      [arr[i], arr[minIdx]] = [arr[minIdx], arr[i]];
      yield { idx: i, swapIdx: minIdx };
    }
  }
}

function* mergeSort(arr) {
  function* merge(start, mid, end) {
    const left  = arr.slice(start, mid);
    const right = arr.slice(mid, end);
    let i = 0, j = 0;
    for (let k = start; k < end; k++) {
      if (i < left.length && (j >= right.length || left[i] <= right[j])) {
        arr[k] = left[i++];
      } else {
        arr[k] = right[j++];
      }
      yield { idx: k };
    }
  }
  function* _sort(start, end) {
    if (end - start > 1) {
      const mid = (start + end) >> 1;
      yield* _sort(start, mid);
      yield* _sort(mid, end);
      yield* merge(start, mid, end);
    }
  }
  yield* _sort(0, arr.length);
}

function* quickSort(arr) {
  function* _sort(start, end) {
    if (start < end) {
      const pivot = arr[end - 1];
      let i = start;
      for (let j = start; j < end - 1; j++) {
        if (arr[j] < pivot) {
          [arr[i], arr[j]] = [arr[j], arr[i]];
          yield { idx: i, swapIdx: j };
          i++;
        } else {
          yield { idx: j };
        }
      }
      [arr[i], arr[end - 1]] = [arr[end - 1], arr[i]];
      yield { idx: i, swapIdx: end - 1 };
      yield* _sort(start, i);
      yield* _sort(i + 1, end);
    }
  }
  yield* _sort(0, arr.length);
}

function* heapSort(arr) {
  function* heapify(n, i) {
    let largest = i;
    const l = 2 * i + 1, r = 2 * i + 2;
    if (l < n && arr[l] > arr[largest]) largest = l;
    if (r < n && arr[r] > arr[largest]) largest = r;
    if (largest !== i) {
      [arr[i], arr[largest]] = [arr[largest], arr[i]];
      yield { idx: i, swapIdx: largest };
      yield* heapify(n, largest);
    } else {
      yield { idx: i };
    }
  }
  const n = arr.length;
  for (let i = Math.floor(n / 2) - 1; i >= 0; i--) yield* heapify(n, i);
  for (let i = n - 1; i > 0; i--) {
    [arr[0], arr[i]] = [arr[i], arr[0]];
    yield { idx: 0, swapIdx: i };
    yield* heapify(i, 0);
  }
}

// ─────────────────────────────────────────────
//  Renderer
// ─────────────────────────────────────────────
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');

canvas.width  = CANVAS_W;
canvas.height = CANVAS_H;

const ALGOS = [
  { name: 'BUBBLE SORT',    fn: bubbleSort,    steps: 4 },
  { name: 'INSERTION SORT', fn: insertionSort, steps: 4 },
  { name: 'SELECTION SORT', fn: selectionSort, steps: 4 },
  { name: 'MERGE SORT',     fn: mergeSort,     steps: 8 },
  { name: 'QUICK SORT',     fn: quickSort,     steps: 6 },
  { name: 'HEAP SORT',      fn: heapSort,      steps: 5 },
];

let states  = [];
let rafId   = null;
let running = false;

function makeArray() {
  return Array.from({ length: ARRAY_SIZE }, (_, i) => i + 1)
    .sort(() => Math.random() - 0.5);
}

function init() {
  states = ALGOS.map(a => {
    const arr = makeArray();
    return {
      name:        a.name,
      arr,
      gen:         a.fn(arr),   // same reference — generator mutates this array
      steps:       a.steps,
      highlight:   -1,
      swapIdx:     -1,
      done:        false,
      elapsed:     null,
      startTime:   null,
      comparisons: 0,
    };
  });
}

function drawRow(s, rowIdx) {
  const yOff = rowIdx * ALGO_HEIGHT;
  const maxV = ARRAY_SIZE;

  ctx.fillStyle = BG;
  ctx.fillRect(0, yOff, CANVAS_W, ALGO_HEIGHT);

  if (rowIdx > 0) {
    ctx.fillStyle = SEP_COLOR;
    ctx.fillRect(0, yOff, CANVAS_W, 1);
  }

  // Done-state gradient: left=dim blue, right=bright blue
  let doneGrad = null;
  if (s.done) {
    doneGrad = ctx.createLinearGradient(0, 0, CANVAS_W, 0);
    doneGrad.addColorStop(0, 'rgba(80, 130, 200, 0.40)');
    doneGrad.addColorStop(1, 'rgba(136, 196, 247, 0.90)');
  }

  for (let i = 0; i < s.arr.length; i++) {
    const h = (s.arr[i] / maxV) * (ALGO_HEIGHT - 26);
    const x = i * BAR_WIDTH;
    const y = yOff + ALGO_HEIGHT - h - 1;

    let color;
    if (s.done) {
      color = doneGrad;
    } else if (i === s.swapIdx || (i === s.highlight && s.swapIdx >= 0)) {
      color = SWP_COLOR;
    } else if (i === s.highlight) {
      color = CMP_COLOR;
    } else {
      color = BAR_COLOR;
    }

    ctx.fillStyle = color;
    ctx.fillRect(x, y, BAR_WIDTH - 1, h);
  }

  ctx.font      = '500 10px "Courier New", monospace';
  ctx.fillStyle = s.done ? TEXT_DONE : TEXT_DIM;
  ctx.fillText(s.name, 10, yOff + 14);

  // Live comparison counter
  if (s.comparisons > 0) {
    ctx.fillStyle = s.done ? TEXT_DONE : 'rgba(136, 196, 247, 0.32)';
    ctx.textAlign = 'center';
    ctx.fillText(s.comparisons.toLocaleString() + ' ops', CANVAS_W / 2, yOff + 14);
    ctx.textAlign = 'left';
  }

  if (s.elapsed !== null) {
    const t = (s.elapsed / 1000).toFixed(2) + 's';
    ctx.fillStyle = TEXT_DONE;
    ctx.textAlign = 'right';
    ctx.fillText(t, CANVAS_W - 10, yOff + 14);
    ctx.textAlign = 'left';
  }
}

function step() {
  for (let i = 0; i < states.length; i++) {
    const s = states[i];
    if (s.done) { drawRow(s, i); continue; }

    if (s.startTime === null) s.startTime = performance.now();

    for (let k = 0; k < s.steps; k++) {
      const result = s.gen.next();
      if (result.done) {
        s.done      = true;
        s.highlight = -1;
        s.swapIdx   = -1;
        s.elapsed   = performance.now() - s.startTime;
        break;
      }
      s.highlight = result.value.idx;
      s.swapIdx   = result.value.swapIdx ?? -1;
      s.comparisons++;
    }

    drawRow(s, i);
  }

  if (states.some(s => !s.done)) {
    rafId = requestAnimationFrame(step);
  } else {
    running = false;
    document.getElementById('startBtn').textContent = 'RESTART';
    document.getElementById('startBtn').disabled    = false;
    document.getElementById('resetBtn').disabled    = false;
  }
}

export function start() {
  if (running) return;
  running = true;
  if (rafId) cancelAnimationFrame(rafId);

  for (const s of states) {
    s.startTime  = null;
    s.elapsed    = null;
    s.done       = false;
    s.comparisons = 0;
    s.highlight  = -1;
    s.swapIdx    = -1;
  }

  document.getElementById('startBtn').disabled = true;
  document.getElementById('resetBtn').disabled = true;
  rafId = requestAnimationFrame(step);
}

export function reset() {
  if (rafId) cancelAnimationFrame(rafId);
  running = false;
  init();
  for (let i = 0; i < states.length; i++) drawRow(states[i], i);
  document.getElementById('startBtn').textContent = 'START';
  document.getElementById('startBtn').disabled    = false;
  document.getElementById('resetBtn').disabled    = false;
}

// Initialise on load
init();
for (let i = 0; i < states.length; i++) drawRow(states[i], i);
