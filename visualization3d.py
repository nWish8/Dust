"""
3D Audio Visualizer (mesh/lines/colors/camera controls) - inspired by audiofabric
- 3D mesh (triangles/lines) animated by FFT
- Orbit/zoom camera with mouse
- Color mapped to frequency
- Uses your audio_processing.py
- Requires: moderngl, pygame, numpy, scipy
"""
import moderngl
import numpy as np
import pygame
from pygame.locals import *
from scipy.spatial import Delaunay
import pyaudio
from pyrr import Matrix44
import random

from audio_processing import choose_capture_device, open_output_stream, compute_fft_bars

WIN_SIZE = (1000, 700)
GRID_N = 32
BAR_SCALE = 1.2

pygame.init()
screen = pygame.display.set_mode(WIN_SIZE, DOUBLEBUF | OPENGL)
ctx = moderngl.create_context()

# --- Camera state ---
camera_angle = 0.0
camera_dist = 3.5
camera_elev = 1.2
mouse_down = False
last_mouse = (0, 0)

def get_proj_view(angle, dist, elev):
    proj = np.array(Matrix44.perspective_projection(45, WIN_SIZE[0]/WIN_SIZE[1], 0.1, 100), dtype='f4')
    eye = np.array([
        np.sin(angle)*dist,
        elev,
        np.cos(angle)*dist
    ])
    look = np.array([0, 0, 0])
    up = np.array([0, 1, 0])
    view = np.array(Matrix44.look_at(eye, look, up), dtype='f4')
    return proj, view

# --- Grid/mesh geometry ---
x, y = np.meshgrid(np.linspace(-1, 1, GRID_N), np.linspace(-1, 1, GRID_N))
points2d = np.stack([x.flatten(), y.flatten()], axis=-1)
tri = Delaunay(points2d)
positions = np.stack([x, np.zeros_like(x), y], axis=-1).reshape(-1, 3)

# --- Build neighbor list for each mesh point (audiofabric style) ---
neighbors = [[] for _ in range(GRID_N*GRID_N)]
for simplex in tri.simplices:
    for i in range(3):
        a, b = simplex[i], simplex[(i+1)%3]
        if b not in neighbors[a]:
            neighbors[a].append(b)
        if a not in neighbors[b]:
            neighbors[b].append(a)

vbo = ctx.buffer(positions.astype('f4').tobytes())
ibo = ctx.buffer(tri.simplices.astype('i4').tobytes())

prog = ctx.program(
    vertex_shader=f"""
        #version 330
        in vec3 in_pos;
        uniform mat4 proj, view;
        uniform float bars[{GRID_N*GRID_N}];
        out float v_height;
        void main() {{
            int idx = int((in_pos.x+1.0)*0.5*{GRID_N-1} + (in_pos.z+1.0)*0.5*{GRID_N-1}*{GRID_N});
            float h = bars[idx] * {BAR_SCALE};
            v_height = h;
            gl_Position = proj * view * vec4(in_pos.x, h, in_pos.z, 1.0);
        }}
    """,
    fragment_shader="""
        #version 330
        in float v_height;
        out vec4 f_color;
        void main() {
            float c = clamp(v_height*2.0, 0.0, 1.0);
            f_color = vec4(0.2 + c, 0.5*c, 1.0-c, 1.0); // color by height
        }
    """
)
vao = ctx.vertex_array(prog, [(vbo, '3f', 'in_pos')], ibo)

# --- Audio ---
def get_audio_stream():
    device_index = choose_capture_device()
    pa, stream, channels, sample_format = open_output_stream(
        samplerate=44100,
        blocksize=2048,
        device_index=device_index
    )
    return pa, stream, channels, sample_format

pa, stream, channels, sample_format = get_audio_stream()
blocksize = 2048

# --- Hotspot logic ---
class Hotspot:
    def __init__(self):
        self.x = random.uniform(-1, 1)
        self.y = random.uniform(-1, 1)
        self.dx = random.uniform(-0.01, 0.01)
        self.dy = random.uniform(-0.01, 0.01)
    def move(self):
        self.x += self.dx + random.uniform(-0.002, 0.002)
        self.y += self.dy + random.uniform(-0.002, 0.002)
        self.x = np.clip(self.x, -1, 1)
        self.y = np.clip(self.y, -1, 1)
        if abs(self.x) >= 1: self.dx *= -1
        if abs(self.y) >= 1: self.dy *= -1

hotspots = []
max_hotspots = 8

bars = np.zeros(GRID_N*GRID_N, dtype='f4')
heights = np.zeros(GRID_N*GRID_N, dtype='f4')  # persistent mesh heights
spring_k = 0.18  # spring to FFT target
neighbor_k = 0.14  # spring to neighbor average
visc = 0.82  # how much of previous height to keep
running = True
while running:
    for e in pygame.event.get():
        if e.type == QUIT:
            running = False
        elif e.type == MOUSEBUTTONDOWN:
            if e.button == 1:
                mouse_down = True
                last_mouse = e.pos
            elif e.button == 4:
                camera_dist = max(1.5, camera_dist - 0.2)
            elif e.button == 5:
                camera_dist = min(8.0, camera_dist + 0.2)
        elif e.type == MOUSEBUTTONUP:
            if e.button == 1:
                mouse_down = False
        elif e.type == MOUSEMOTION and mouse_down:
            dx, dy = e.pos[0] - last_mouse[0], e.pos[1] - last_mouse[1]
            camera_angle += dx * 0.01
            camera_elev = np.clip(camera_elev - dy * 0.01, 0.2, 3.0)
            last_mouse = e.pos
    data = stream.read(blocksize, exception_on_overflow=False)
    if sample_format == pyaudio.paInt16:
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        samples = np.frombuffer(data, dtype=np.float32)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    # --- FFT bars ---
    fft_bars = compute_fft_bars(samples, GRID_N*GRID_N)
    # --- Hotspot count based on average mesh height ---
    avg_height = np.mean(np.abs(fft_bars))
    n_hot = int(np.clip(1 + avg_height * 16, 1, max_hotspots))
    # Add/remove hotspots as needed
    while len(hotspots) < n_hot:
        hotspots.append(Hotspot())
    while len(hotspots) > n_hot:
        hotspots.pop()
    for h in hotspots:
        h.move()
    # --- For each mesh point, pick FFT bin by distance to nearest hotspot ---
    mesh_xy = points2d  # shape (N*N, 2)
    new_heights = np.zeros_like(heights)
    for i, (px, py) in enumerate(mesh_xy):
        dists = [np.hypot(px - h.x, py - h.y) for h in hotspots]
        min_dist = min(dists)
        # Scale the distance down to make the gradient sharper
        scaled_dist = min_dist * 0.5  # <-- adjust this factor for more/less sharpness
        rel = np.clip(1.0 - scaled_dist/2.0, 0, 1)  # 0 (far) to 1 (close)
        bin_idx = int(rel * (len(fft_bars)-1))
        target = fft_bars[bin_idx] * 8.0
        neighbor_avg = np.mean([heights[j] for j in neighbors[i]]) if neighbors[i] else 0.0
        new_heights[i] = (
            visc * heights[i]
            + spring_k * (target - heights[i])
            + neighbor_k * (neighbor_avg - heights[i])
        )
    heights[:] = new_heights
    bars = heights.astype('f4')
    prog['bars'].write(bars.tobytes())

    ctx.clear(0.05, 0.05, 0.08)
    proj, view = get_proj_view(camera_angle, camera_dist, camera_elev)
    prog['proj'].write(proj.tobytes())
    prog['view'].write(view.tobytes())
    vao.render(moderngl.TRIANGLES)
    vao.render(moderngl.LINES)
    pygame.display.flip()

stream.stop_stream()
stream.close()
pa.terminate()
pygame.quit()
