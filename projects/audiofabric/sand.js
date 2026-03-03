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

const COUNT = 460;

const grains = Array.from({ length: COUNT }, () => spawn(true));

function spawn(randomX = false) {
  return {
    x:     randomX ? Math.random() * window.innerWidth : -20,
    y:     Math.random() * window.innerHeight,
    speed: 0.35 + Math.pow(Math.random(), 2) * 2.2,   // skew toward slower
    vy:    (Math.random() - 0.5) * 0.18,
    size:  0.3 + Math.random() * 1.1,
    alpha: 0.025 + Math.random() * 0.18,
    len:   2 + Math.random() * 18,
    phase: Math.random() * Math.PI * 2,
  };
}

let rafId = null;
let running = true;

function draw(ts) {
  if (!running) return;
  const t = ts * 0.001;
  const W = sandCanvas.width, H = sandCanvas.height;

  ctx.clearRect(0, 0, W, H);

  for (let i = 0; i < grains.length; i++) {
    const g = grains[i];

    g.x += g.speed;
    g.y += g.vy + Math.sin(t * 0.4 + g.phase) * 0.06;

    if (g.x > W + g.len) grains[i] = spawn(false);
    if (g.y < 0)  g.y = H;
    if (g.y > H)  g.y = 0;

    ctx.beginPath();
    ctx.strokeStyle = `rgba(155, 195, 230, ${g.alpha})`;
    ctx.lineWidth   = g.size;
    ctx.lineCap     = 'round';
    // Streak trails leftward from current position
    ctx.moveTo(g.x, g.y);
    ctx.lineTo(g.x - g.len, g.y - g.vy * 0.5);
    ctx.stroke();
  }

  rafId = requestAnimationFrame(draw);
}

rafId = requestAnimationFrame(draw);

document.addEventListener('dust:overlay-hidden', () => {
  running = false;
  if (rafId) cancelAnimationFrame(rafId);
  // Fade out the canvas gracefully
  sandCanvas.style.transition = 'opacity 1.2s ease';
  sandCanvas.style.opacity = '0';
});
