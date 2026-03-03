# AudioFabric

A polished, web-based real-time audio visualizer inspired by [audiofabric](https://github.com/rolyatmax/audiofabric).

## Features

- **3D wireframe mesh** that deforms in real-time to audio frequencies
- **Spring physics** with neighbour coupling for organic, flowing wave motion
- **Bloom glow** post-processing for the glowing fabric aesthetic
- **Microphone input** — visualize live audio
- **Audio file input** — load any audio file; drag & drop supported
- **Orbit controls** — drag to rotate, scroll to zoom; gentle auto-rotate by default
- **No build step** — pure HTML/CSS/JS, loads Three.js from CDN

## Usage

Open `index.html` in a modern browser (Chrome, Edge, Firefox, Safari 16.4+).

- Click **Enable Microphone** to visualize live audio
- Click **Load Audio File** or **drag & drop** an audio file to play and visualize it

## Embedding on a Website

Drop the three files (`index.html`, `style.css`, `visualizer.js`) into any folder on your site and link to `index.html`, or embed it in an `<iframe>`:

```html
<iframe src="audiofabric/index.html" width="100%" height="600" frameborder="0" allowfullscreen
        allow="microphone"></iframe>
```

The `allow="microphone"` attribute is required for the microphone button to work inside an iframe.

## Tuning

Key constants in `visualizer.js`:

| Constant | Default | Effect |
|----------|---------|--------|
| `SEGS` | 80 | Grid density (higher = more detail, more CPU) |
| `H_SCALE` | 2.4 | Maximum peak height |
| `SPRING_K` | 0.08 | How fast vertices chase the audio target |
| `NEIGHBOR_K` | 0.20 | How strongly vertices pull on their neighbours |
| `DAMP` | 0.84 | Velocity damping — lower = snappier, higher = more ringing |
| `FREQ_USE_RATIO` | 0.62 | Fraction of FFT bins used (~0–14 kHz) |

Bloom is tuned in the `UnrealBloomPass` constructor: `(resolution, strength=1.15, radius=0.65, threshold=0.16)`.
