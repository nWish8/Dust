// Sand particle animation for the loading overlay.
// Listens for the 'dust:overlay-hidden' event to stop.

const sandCanvas = document.getElementById('sand');
const ctx = sandCanvas.getContext('2d');

function resize() {
  sandCanvas.width  = window.innerWidth;
  sandCanvas.height = window.innerHeight;
}
resize();
window.addEventListener('resize', resize);

function r(min, max) { return min + Math.random() * (max - min); }

// ── Layer spawn functions ────────────────────────────────────
function spawnDust(randomX = false) {
  return {
    layer: 0,
    x:     randomX ? Math.random() * window.innerWidth : -20,
    y:     Math.random() * window.innerHeight,
    speed: r(0.4, 2.0),
    vy:    (Math.random() - 0.5) * 0.15,
    size:  r(0.3, 0.8),
    alpha: r(0.02, 0.10),
    len:   r(3, 12),
    phase: Math.random() * Math.PI * 2,
  };
}

function spawnStreak(randomX = false) {
  return {
    layer:  1,
    x:      randomX ? Math.random() * window.innerWidth : -60,
    y:      Math.random() * window.innerHeight,
    speed:  r(0.25, 0.9),
    vy:     (Math.random() - 0.5) * 0.10,
    size:   r(0.6, 1.4),
    alpha:  r(0.06, 0.18),
    len:    r(18, 55),
    phase:  Math.random() * Math.PI * 2,
    vPhase: r(0.3, 0.8),   // oscillation frequency
    vAmp:   r(0.05, 0.20), // oscillation amplitude
  };
}

function spawnMote(randomX = false) {
  return {
    layer: 2,
    x:     randomX ? Math.random() * window.innerWidth : -10,
    y:     Math.random() * window.innerHeight,
    speed: r(0.05, 0.30),
    vy:    (Math.random() - 0.5) * 0.4,
    size:  r(1.0, 2.0),
    alpha: r(0.25, 0.55),
    len:   r(2, 6),
    phase: Math.random() * Math.PI * 2,
  };
}

function spawnFlare(y) {
  return {
    x:     -10,
    y,
    speed: r(3.0, 6.0),
    vy:    (Math.random() - 0.5) * 0.3,
    size:  r(1.2, 2.2),
    alpha: r(0.4, 0.7),
    len:   r(20, 45),
    life:  1.0,
  };
}

// 900 grains across three layers
const grains = [
  ...Array.from({ length: 600 }, () => spawnDust(true)),
  ...Array.from({ length: 240 }, () => spawnStreak(true)),
  ...Array.from({ length:  60 }, () => spawnMote(true)),
];

let flares = [];
let lastFlareTime = 0;
let rafId   = null;
let running = true;

function draw(ts) {
  if (!running) return;
  const t = ts * 0.001;
  const W = sandCanvas.width, H = sandCanvas.height;

  ctx.clearRect(0, 0, W, H);

  // Flare event every ~4–6 s
  if (t - lastFlareTime > 4.0 + Math.random() * 2.0) {
    lastFlareTime = t;
    const fy = Math.random() * H;
    for (let k = 0; k < 12; k++) {
      flares.push(spawnFlare(fy + (Math.random() - 0.5) * 60));
    }
  }

  // Regular grains
  for (let i = 0; i < grains.length; i++) {
    const g = grains[i];

    g.x += g.speed;
    if (g.layer === 1) {
      // Streaks: subtle vertical oscillation
      g.y += g.vy + Math.sin(t * g.vPhase + g.phase) * g.vAmp;
    } else {
      g.y += g.vy + Math.sin(t * 0.4 + g.phase) * 0.04;
    }

    const maxX = W + g.len + 10;
    if (g.x > maxX) {
      grains[i] = g.layer === 0 ? spawnDust(false)
                : g.layer === 1 ? spawnStreak(false)
                : spawnMote(false);
      continue;
    }
    if (g.y < 0) g.y = H;
    if (g.y > H) g.y = 0;

    ctx.beginPath();
    ctx.strokeStyle = `rgba(155, 195, 230, ${g.alpha})`;
    ctx.lineWidth   = g.size;
    ctx.lineCap     = 'round';
    ctx.moveTo(g.x, g.y);
    ctx.lineTo(g.x - g.len, g.y - g.vy * 0.5);
    ctx.stroke();
  }

  // Flares
  for (let i = flares.length - 1; i >= 0; i--) {
    const f = flares[i];
    f.x    += f.speed;
    f.y    += f.vy;
    f.life -= 0.012;

    if (f.life <= 0 || f.x > W + f.len) {
      flares.splice(i, 1);
      continue;
    }

    ctx.beginPath();
    ctx.strokeStyle = `rgba(200, 225, 255, ${f.alpha * f.life})`;
    ctx.lineWidth   = f.size;
    ctx.lineCap     = 'round';
    ctx.moveTo(f.x, f.y);
    ctx.lineTo(f.x - f.len, f.y - f.vy * 0.5);
    ctx.stroke();
  }

  rafId = requestAnimationFrame(draw);
}

rafId = requestAnimationFrame(draw);

document.addEventListener('dust:overlay-hidden', () => {
  running = false;
  if (rafId) cancelAnimationFrame(rafId);
  sandCanvas.style.transition = 'opacity 1.2s ease';
  sandCanvas.style.opacity = '0';
});
