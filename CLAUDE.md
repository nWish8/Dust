# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Structure

**Dust** is a web showcase with a landing page (`index.html`) linking to three creative experiments:

| Project | Stack | Entry point |
|---|---|---|
| `fabric/` | Vanilla HTML/CSS/JS, Three.js r168 (CDN) | Open `fabric/index.html` in a browser |
| `sand/` | Vanilla HTML/CSS/JS, Canvas 2D | Open `sand/index.html` in a browser |
| `sprint/` | Placeholder | `sprint/index.html` (coming soon) |
| `archive/audio_visualizer/` | Python, pygame, moderngl, pyaudio, numpy, scipy | `python main.py` |
| `archive/visualSort/` | Python, pygame | `python main.py` |

## Running web projects

No build step. Serve the repo root:
```bash
python -m http.server 8080
```
Then open `http://localhost:8080` in Chrome/Edge/Firefox.

> Direct `file://` access works for `sand/` and `sprint/`, but **Fabric requires a server** (ES modules + microphone API need HTTP).

## Architecture

### Root
- `index.html` — landing page: DUST title, three project cards (FABRIC, SAND, SPRINT)
- `style.css` — shared design tokens (`--bg`, `--accent`, `--accent-dim`, `--text-dim`) and shimmer keyframe

### fabric/
- `index.html` — overlay with start buttons, params panel; loads `sand.js` + `visualizer.js`
- `style.css` — all overlay, button, slider, and params panel styles; includes `.back-link`
- `visualizer.js` — Three.js point-cloud mesh with spring physics and UnrealBloom; audio via Web Audio API AnalyserNode
- `sand.js` — loading screen particle streaks (canvas 2D); stops on `dust:overlay-hidden` event

Key tuning constants are at the top of `visualizer.js` (SEGS, MESH_W, FFT_SIZE, DEFAULTS object).
`SEGS` changes require page reload (buffer size fixed at load).

### sand/
- `index.html` — start overlay, canvas wrapper, inline script wiring buttons to `sort.js` exports
- `sort.js` — 6 sorting algorithms as JS generators (`bubbleSort`, `insertionSort`, `selectionSort`, `mergeSort`, `quickSort`, `heapSort`); canvas renderer at 60 FPS; exports `start()` and `reset()`

Key constants at the top of `sort.js`: `ARRAY_SIZE`, `BAR_WIDTH`, `ALGO_HEIGHT`.

### sprint/
- `sprint/index.html` — self-contained coming-soon page (no external files)

### archive/
- `archive/audio_visualizer/` — Python pygame/moderngl visualizer (3 modes: Bars, Mesh Wave, Mesh Ripple)
- `archive/visualSort/` — Python pygame sorting visualizer

## Python environment
A `.venv/` exists at the repo root with numpy, scipy, pygame, moderngl, pyaudio, pyrr installed. Activate before running archived Python projects.
