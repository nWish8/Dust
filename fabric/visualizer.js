import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

// ─────────────────────────────────────────────
//  Fixed geometry config (cannot change at runtime)
// ─────────────────────────────────────────────
const SEGS         = 110;
const VN           = SEGS + 1;
const TOTAL        = VN * VN;
const MESH_W       = 14.0;
const FFT_SIZE     = 2048;
const MAX_HOTSPOTS = 10;  // upper bound for buffer allocation

// ─────────────────────────────────────────────
//  Runtime params — all tweakable via the panel
// ─────────────────────────────────────────────
const DEFAULTS = {
  numHotspots:   5,
  hotspotSpeed:  0.006,
  springK:       0.045,
  neighborK:     0.13,
  damp:          0.91,
  hScale:        1.6,
  peakCurve:     0.50,
  rippleFalloff: 0.38,
  bloomStrength: 0.95,
};

const params = { ...DEFAULTS };

// ─────────────────────────────────────────────
//  Renderer
// ─────────────────────────────────────────────
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;

// ─────────────────────────────────────────────
//  Scene & Camera
// ─────────────────────────────────────────────
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x010008);

const camera = new THREE.PerspectiveCamera(
  58, window.innerWidth / window.innerHeight, 0.1, 100
);
camera.position.set(0, 4.5, 5.8);

// ─────────────────────────────────────────────
//  Orbit Controls
// ─────────────────────────────────────────────
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping   = true;
controls.dampingFactor   = 0.04;
controls.autoRotate      = true;
controls.autoRotateSpeed = 0.25;
controls.minDistance     = 2.5;
controls.maxDistance     = 16.0;
controls.maxPolarAngle   = Math.PI * 0.46;
controls.minPolarAngle   = 0.04;
controls.target.set(0, 0.3, 0);
controls.update();

controls.addEventListener('start', () => { controls.autoRotate = false; });

// ─────────────────────────────────────────────
//  Post-processing
// ─────────────────────────────────────────────
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));

const bloom = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  params.bloomStrength, 0.85, 0.14
);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// ─────────────────────────────────────────────
//  Point field geometry
// ─────────────────────────────────────────────
const posArr = new Float32Array(TOTAL * 3);

for (let j = 0; j < VN; j++) {
  for (let i = 0; i < VN; i++) {
    const vi = j * VN + i;
    posArr[vi * 3]     = (i / SEGS - 0.5) * MESH_W;
    posArr[vi * 3 + 1] = 0;
    posArr[vi * 3 + 2] = (j / SEGS - 0.5) * MESH_W;
  }
}

const geo     = new THREE.BufferGeometry();
const posAttr = new THREE.BufferAttribute(posArr, 3);
posAttr.setUsage(THREE.DynamicDrawUsage);
geo.setAttribute('position', posAttr);

// ─────────────────────────────────────────────
//  Point shader — screen-space circular vignette
// ─────────────────────────────────────────────
const mat = new THREE.ShaderMaterial({
  transparent: true,
  depthWrite:  false,
  blending:    THREE.AdditiveBlending,
  uniforms: {
    uMaxH:       { value: params.hScale },
    uHalfH:      { value: window.innerHeight * 0.5 },
    uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
  },
  vertexShader: /* glsl */`
    uniform float uMaxH;
    uniform float uHalfH;
    varying float vH;

    void main() {
      vH  = clamp(position.y / uMaxH, 0.0, 1.0);
      vec4 mvPos  = modelViewMatrix * vec4(position, 1.0);
      gl_Position = projectionMatrix * mvPos;
      float camDist    = max(-mvPos.z, 0.5);
      gl_PointSize     = (0.035 + vH * 0.19) * (uHalfH / camDist);
      gl_PointSize     = clamp(gl_PointSize, 1.0, 18.0);
    }
  `,
  fragmentShader: /* glsl */`
    uniform vec2  uResolution;
    varying float vH;

    vec3 ramp(float t) {
      t = clamp(t, 0.0, 1.0);
      vec3 c0 = vec3(0.02, 0.00, 0.12);
      vec3 c1 = vec3(0.04, 0.22, 0.78);
      vec3 c2 = vec3(0.12, 0.80, 0.98);
      vec3 c3 = vec3(0.82, 0.96, 1.00);
      if (t < 0.30) return mix(c0, c1, t / 0.30);
      if (t < 0.65) return mix(c1, c2, (t - 0.30) / 0.35);
      return mix(c2, c3, (t - 0.65) / 0.35);
    }

    void main() {
      vec2  coord = gl_PointCoord - vec2(0.5);
      float d     = length(coord);
      if (d > 0.5) discard;

      float core  = smoothstep(0.48, 0.10, d);
      float halo  = exp(-d * d * 9.0);
      float alpha = (core * 0.85 + halo * 0.40) * (0.055 + vH * 0.945);

      // Screen-space circular vignette — fades off at screen edges
      vec2 sc = (gl_FragCoord.xy / uResolution) - vec2(0.5);
      sc.x   *= uResolution.x / uResolution.y;
      float r = length(sc);
      alpha  *= (1.0 - smoothstep(0.44, 0.50, r));

      gl_FragColor = vec4(ramp(vH), alpha);
    }
  `,
});

scene.add(new THREE.Points(geo, mat));

// ─────────────────────────────────────────────
//  Hotspot markers
// ─────────────────────────────────────────────
const hotspotGeo = new THREE.BufferGeometry();
const hotspotPos = new Float32Array(MAX_HOTSPOTS * 3);  // always allocate max
hotspotGeo.setAttribute(
  'position',
  new THREE.BufferAttribute(hotspotPos, 3).setUsage(THREE.DynamicDrawUsage)
);
hotspotGeo.setDrawRange(0, params.numHotspots);

const hotspotMat = new THREE.ShaderMaterial({
  transparent: true,
  depthWrite:  false,
  blending:    THREE.AdditiveBlending,
  uniforms: {
    uEnergy: { value: 0 },
    uHalfH:  { value: window.innerHeight * 0.5 },
  },
  vertexShader: /* glsl */`
    uniform float uEnergy;
    uniform float uHalfH;
    void main() {
      vec4 mvPos  = modelViewMatrix * vec4(position, 1.0);
      gl_Position = projectionMatrix * mvPos;
      float camDist = max(-mvPos.z, 0.5);
      gl_PointSize  = (0.14 + uEnergy * 0.22) * (uHalfH / camDist);
      gl_PointSize  = clamp(gl_PointSize, 3.0, 28.0);
    }
  `,
  fragmentShader: /* glsl */`
    uniform float uEnergy;
    void main() {
      vec2  coord = gl_PointCoord - vec2(0.5);
      float d     = length(coord);
      if (d > 0.5) discard;
      float a = exp(-d * d * 7.0) * (0.5 + uEnergy * 0.5);
      gl_FragColor = vec4(0.6 + uEnergy * 0.4, 0.9, 1.0, a);
    }
  `,
});

scene.add(new THREE.Points(hotspotGeo, hotspotMat));

scene.fog = new THREE.FogExp2(0x010008, 0.07);

// ─────────────────────────────────────────────
//  Physics buffers
// ─────────────────────────────────────────────
const heights    = new Float32Array(TOTAL).fill(0);
const velocities = new Float32Array(TOTAL).fill(0);
const nextH      = new Float32Array(TOTAL);

// ─────────────────────────────────────────────
//  Hotspot state
// ─────────────────────────────────────────────
const hotspots = Array.from({ length: params.numHotspots }, () => {
  const hw = MESH_W * 0.46;
  return {
    x:  (Math.random() - 0.5) * hw * 2,
    z:  (Math.random() - 0.5) * hw * 2,
    vx: (Math.random() - 0.5) * params.hotspotSpeed,
    vz: (Math.random() - 0.5) * params.hotspotSpeed,
  };
});

// ─────────────────────────────────────────────
//  Auto-hotspot state
// ─────────────────────────────────────────────
let autoHotspotsEnabled = false;
let smoothedVolatility  = 0;
let lastAutoChange      = 0;
const AUTO_CHANGE_INTERVAL = 8000; // ms between auto adjustments

function moveHotspots() {
  const hw = MESH_W * 0.46;

  // Sync array length to current param (add or remove)
  while (hotspots.length < params.numHotspots) {
    hotspots.push({
      x:  (Math.random() - 0.5) * hw * 2,
      z:  (Math.random() - 0.5) * hw * 2,
      vx: (Math.random() - 0.5) * params.hotspotSpeed,
      vz: (Math.random() - 0.5) * params.hotspotSpeed,
    });
  }
  while (hotspots.length > params.numHotspots) hotspots.pop();
  hotspotGeo.setDrawRange(0, params.numHotspots);

  for (const h of hotspots) {
    h.vx += (Math.random() - 0.5) * 0.0005;
    h.vz += (Math.random() - 0.5) * 0.0005;
    const spd = Math.sqrt(h.vx * h.vx + h.vz * h.vz);
    if (spd > params.hotspotSpeed) {
      h.vx = h.vx / spd * params.hotspotSpeed;
      h.vz = h.vz / spd * params.hotspotSpeed;
    }
    h.x += h.vx;
    h.z += h.vz;
    if (Math.abs(h.x) > hw) { h.vx *= -0.85; h.x = Math.sign(h.x) * hw; }
    if (Math.abs(h.z) > hw) { h.vz *= -0.85; h.z = Math.sign(h.z) * hw; }
  }
}

function nearestHotspotDist(x, z) {
  let minD2 = Infinity;
  for (const h of hotspots) {
    const dx = x - h.x, dz = z - h.z;
    const d2 = dx * dx + dz * dz;
    if (d2 < minD2) minD2 = d2;
  }
  return Math.sqrt(minD2);
}

// ─────────────────────────────────────────────
//  Audio
// ─────────────────────────────────────────────
let analyser   = null;
let freqData   = null;
let audioReady = false;

function setupAnalyser(ctx) {
  analyser = ctx.createAnalyser();
  analyser.fftSize = FFT_SIZE;
  analyser.smoothingTimeConstant = 0.90;
  freqData = new Uint8Array(analyser.frequencyBinCount);
}

async function initSystemAudio() {
  try {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, sampleRate: 44100 },
      video: { width: 1, height: 1, frameRate: 1 },
    });
    const audioTracks = stream.getAudioTracks();
    if (audioTracks.length === 0) {
      stream.getTracks().forEach(t => t.stop());
      alert('No system audio captured.\n\nIn Chrome\'s share dialog:\n  1. Choose "Entire Screen"\n  2. Tick "Share system audio"\n  3. Click Share\n\nThen try again.');
      return;
    }
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    setupAnalyser(ctx);
    ctx.createMediaStreamSource(new MediaStream(audioTracks)).connect(analyser);
    audioTracks[0].addEventListener('ended', () => {
      audioReady = false;
      const ov = document.getElementById('overlay');
      ov.style.display = '';
      requestAnimationFrame(() => ov.classList.remove('hidden'));
    });
    audioReady = true;
    hideOverlay();
  } catch (err) {
    if (err.name !== 'NotAllowedError' && err.name !== 'AbortError') {
      alert('System audio capture failed: ' + err.message);
    }
  }
}

async function initMic() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const ctx    = new (window.AudioContext || window.webkitAudioContext)();
    setupAnalyser(ctx);
    ctx.createMediaStreamSource(stream).connect(analyser);
    audioReady = true;
    hideOverlay();
  } catch {
    alert('Microphone access denied. Please allow microphone access and try again.');
  }
}

async function initFile(file) {
  const ctx      = new (window.AudioContext || window.webkitAudioContext)();
  const arrayBuf = await file.arrayBuffer();
  const audioBuf = await ctx.decodeAudioData(arrayBuf);
  setupAnalyser(ctx);
  const src  = ctx.createBufferSource();
  src.buffer = audioBuf;
  src.loop   = true;
  src.connect(analyser);
  analyser.connect(ctx.destination);
  src.start(0);
  audioReady = true;
  hideOverlay();
}

function hideOverlay() {
  const ov = document.getElementById('overlay');
  ov.classList.add('hidden');
  setTimeout(() => {
    ov.style.display = 'none';
    document.dispatchEvent(new Event('dust:overlay-hidden'));
  }, 1100);
  const hint = document.getElementById('corner-hint');
  hint.style.opacity = '0.9';
  setTimeout(() => { hint.style.opacity = '0'; }, 4500);
}

document.getElementById('sysBtn').addEventListener('click', initSystemAudio);
document.getElementById('micBtn').addEventListener('click', initMic);
document.getElementById('fileBtn').addEventListener('click', () => document.getElementById('fileInput').click());
document.getElementById('fileInput').addEventListener('change', e => { const f = e.target.files[0]; if (f) initFile(f); });

document.addEventListener('dragenter', () => document.body.classList.add('drag-active'));
document.addEventListener('dragleave', e => { if (!e.relatedTarget) document.body.classList.remove('drag-active'); });
document.addEventListener('dragover',  e => e.preventDefault());
document.addEventListener('drop', e => {
  e.preventDefault();
  document.body.classList.remove('drag-active');
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('audio/')) initFile(f);
});

// ─────────────────────────────────────────────
//  Mesh update
// ─────────────────────────────────────────────
let overallEnergy = 0;

function updateMesh(t) {
  moveHotspots();

  // Keep shader uniform in sync with hScale param
  mat.uniforms.uMaxH.value = params.hScale;

  if (!audioReady) {
    for (let j = 0; j < VN; j++) {
      for (let i = 0; i < VN; i++) {
        const vi = j * VN + i;
        const x  = posArr[vi * 3], z = posArr[vi * 3 + 2];
        const d  = Math.sqrt(x * x + z * z);
        posArr[vi * 3 + 1] = Math.max(0,
          (Math.sin(d * 1.7 - t * 1.2) * 0.038 + Math.sin(d * 2.9 - t * 1.9) * 0.016)
          * Math.exp(-d * 0.42)
        );
      }
    }
    posAttr.needsUpdate = true;
    for (let k = 0; k < params.numHotspots; k++) {
      hotspotPos[k * 3] = hotspots[k].x; hotspotPos[k * 3 + 1] = 0.02; hotspotPos[k * 3 + 2] = hotspots[k].z;
    }
    hotspotGeo.attributes.position.needsUpdate = true;
    hotspotMat.uniforms.uEnergy.value = 0.05;
    return;
  }

  analyser.getByteFrequencyData(freqData);
  const bins = freqData.length;

  // Smoothed bass energy for hotspot glow
  let sumE = 0;
  const eb = Math.floor(bins * 0.15);
  for (let b = 0; b < eb; b++) sumE += freqData[b];
  overallEnergy += (sumE / (eb * 255) - overallEnergy) * 0.08;

  const maxDist = MESH_W * 0.68;

  for (let j = 0; j < VN; j++) {
    for (let i = 0; i < VN; i++) {
      const vi       = j * VN + i;
      const x        = posArr[vi * 3], z = posArr[vi * 3 + 2];
      const minDist  = nearestHotspotDist(x, z);
      const distNorm = Math.min(minDist / maxDist, 1.0);
      const binIdx   = Math.min(Math.floor(distNorm * bins * 0.55), bins - 1);
      const raw      = freqData[binIdx] / 255.0;
      const influence = Math.exp(-minDist * params.rippleFalloff);
      const target   = Math.pow(Math.max(0, raw * influence), params.peakCurve) * params.hScale;

      let nSum = 0, nCnt = 0;
      if (i > 0)    { nSum += heights[vi - 1];  nCnt++; }
      if (i < SEGS) { nSum += heights[vi + 1];  nCnt++; }
      if (j > 0)    { nSum += heights[vi - VN]; nCnt++; }
      if (j < SEGS) { nSum += heights[vi + VN]; nCnt++; }
      const nAvg = nCnt > 0 ? nSum / nCnt : 0;

      const force    = params.springK * (target - heights[vi]) + params.neighborK * (nAvg - heights[vi]);
      velocities[vi] = params.damp * (velocities[vi] + force);
      nextH[vi]      = heights[vi] + velocities[vi];
    }
  }

  heights.set(nextH);
  for (let vi = 0; vi < TOTAL; vi++) posArr[vi * 3 + 1] = heights[vi];
  posAttr.needsUpdate = true;

  // Slow volatility tracking — sample every 4th vertex
  let volSum = 0, volCnt = 0;
  for (let vi = 0; vi < TOTAL; vi += 4) {
    volSum += Math.abs(heights[vi]);
    volCnt++;
  }
  // EMA coefficient 0.002 ≈ 8s time constant at 60fps
  smoothedVolatility += (volSum / volCnt / params.hScale - smoothedVolatility) * 0.002;

  // Auto-adjust hotspot count with deliberate delay
  if (autoHotspotsEnabled) {
    const now = Date.now();
    if (now - lastAutoChange > AUTO_CHANGE_INTERVAL) {
      const target  = Math.round(2 + smoothedVolatility * 8);
      const clamped = Math.max(1, Math.min(10, target));
      if (clamped !== params.numHotspots) {
        params.numHotspots = clamped;
        const slider = document.getElementById('ps-numHotspots');
        const valEl  = document.getElementById('pv-numHotspots');
        slider.value = clamped;
        valEl.textContent = String(clamped);
        sliderFill(slider);
        lastAutoChange = now;
      }
    }
  }

  for (let k = 0; k < params.numHotspots; k++) {
    const gi = Math.round((hotspots[k].x / MESH_W + 0.5) * SEGS);
    const gj = Math.round((hotspots[k].z / MESH_W + 0.5) * SEGS);
    const vi = Math.max(0, Math.min(gj * VN + gi, TOTAL - 1));
    hotspotPos[k * 3] = hotspots[k].x; hotspotPos[k * 3 + 1] = heights[vi] + 0.04; hotspotPos[k * 3 + 2] = hotspots[k].z;
  }
  hotspotGeo.attributes.position.needsUpdate = true;
  hotspotMat.uniforms.uEnergy.value = overallEnergy;
}

// ─────────────────────────────────────────────
//  Controls panel
// ─────────────────────────────────────────────
function sliderFill(input) {
  const min = parseFloat(input.min), max = parseFloat(input.max), val = parseFloat(input.value);
  const pct = ((val - min) / (max - min)) * 100;
  const fillColor = input.disabled ? 'rgba(122,196,245,0.18)' : 'rgba(122,196,245,0.55)';
  input.style.background =
    `linear-gradient(to right, ${fillColor} ${pct}%, rgba(255,255,255,0.08) ${pct}%)`;
}

function setupControls() {
  // Each entry: [paramKey, sliderId, parseFunc, displayFormat]
  const bindings = [
    ['numHotspots',   'numHotspots',   v => Math.round(v),        v => String(Math.round(v))],
    ['hotspotSpeed',  'hotspotSpeed',  v => parseFloat(v),        v => v.toFixed(3)],
    ['springK',       'springK',       v => parseFloat(v),        v => v.toFixed(3)],
    ['neighborK',     'neighborK',     v => parseFloat(v),        v => v.toFixed(2)],
    ['damp',          'damp',          v => parseFloat(v),        v => v.toFixed(2)],
    ['hScale',        'hScale',        v => parseFloat(v),        v => v.toFixed(1)],
    ['peakCurve',     'peakCurve',     v => parseFloat(v),        v => v.toFixed(2)],
    ['rippleFalloff', 'rippleFalloff', v => parseFloat(v),        v => v.toFixed(2)],
    ['bloomStrength', 'bloomStrength', v => parseFloat(v),        v => v.toFixed(2)],
  ];

  for (const [key, id, parse, fmt] of bindings) {
    const slider = document.getElementById('ps-' + id);
    const valEl  = document.getElementById('pv-' + id);
    sliderFill(slider);

    slider.addEventListener('input', () => {
      params[key] = parse(slider.value);
      valEl.textContent = fmt(params[key]);
      sliderFill(slider);
      if (key === 'bloomStrength') bloom.strength = params[key];
    });
  }

  // Toggle params panel
  const toggle = document.getElementById('params-toggle');
  const panel  = document.getElementById('params');
  toggle.addEventListener('click', () => {
    panel.classList.toggle('open');
    toggle.classList.toggle('active');
  });

  // AUTO hotspots toggle
  const autoBtn      = document.getElementById('auto-hotspots');
  const hotspotSlider = document.getElementById('ps-numHotspots');
  autoBtn.addEventListener('click', () => {
    autoHotspotsEnabled = !autoHotspotsEnabled;
    autoBtn.classList.toggle('active', autoHotspotsEnabled);
    hotspotSlider.disabled = autoHotspotsEnabled;
    sliderFill(hotspotSlider);
    // Seed the change timer so it waits a full interval before first adjustment
    lastAutoChange = Date.now();
  });

  // Reset
  document.getElementById('params-reset').addEventListener('click', () => {
    // Disable auto mode on reset
    if (autoHotspotsEnabled) {
      autoHotspotsEnabled = false;
      autoBtn.classList.remove('active');
      hotspotSlider.disabled = false;
    }
    Object.assign(params, DEFAULTS);
    bloom.strength = params.bloomStrength;
    for (const [key, id, parse, fmt] of bindings) {
      const slider = document.getElementById('ps-' + id);
      const valEl  = document.getElementById('pv-' + id);
      slider.value = DEFAULTS[key];
      valEl.textContent = fmt(DEFAULTS[key]);
      sliderFill(slider);
    }
  });
}

setupControls();

// ─────────────────────────────────────────────
//  Resize
// ─────────────────────────────────────────────
window.addEventListener('resize', () => {
  const w = window.innerWidth, h = window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  composer.setSize(w, h);
  bloom.resolution.set(w, h);
  mat.uniforms.uHalfH.value        = h * 0.5;
  mat.uniforms.uResolution.value.set(w, h);
  hotspotMat.uniforms.uHalfH.value = h * 0.5;
});

// ─────────────────────────────────────────────
//  Render loop
// ─────────────────────────────────────────────
let time = 0;

function animate() {
  requestAnimationFrame(animate);
  time += 0.016;
  controls.update();
  updateMesh(time);
  composer.render();
}

animate();
