"""
mesh_wave.py - Audio visualizer inspired by the original audiofabric repo
- Mesh grid with Delaunay triangulation
- Spring/neighbor mesh update logic
- FFT bin mapping and color logic closely emulating audiofabric
- Camera controls (orbit/zoom)
- Device selection via terminal before start
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

def run_mesh_wave(*, samplerate: int = 44100, blocksize: int = 2048, num_bars: int = 60, interp: float = 0.5) -> None:
    device_index = choose_capture_device()
    pygame.init()
    screen = pygame.display.set_mode(WIN_SIZE, DOUBLEBUF | OPENGL)
    ctx = moderngl.create_context()
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
    # Mesh grid
    x, y = np.meshgrid(np.linspace(-1, 1, GRID_N), np.linspace(-1, 1, GRID_N))
    points2d = np.stack([x.flatten(), y.flatten()], axis=-1)
    tri = Delaunay(points2d)
    positions = np.stack([x, np.zeros_like(x), y], axis=-1).reshape(-1, 3)
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
                f_color = vec4(0.2 + c, 0.5*c, 1.0-c, 1.0);
            }
        """
    )
    vao = ctx.vertex_array(prog, [(vbo, '3f', 'in_pos')], ibo)
    pa, stream, channels, sample_format = open_output_stream(
        samplerate=samplerate,
        blocksize=blocksize,
        device_index=device_index,
    )
    blocksize = 2048
    heights = np.zeros(GRID_N*GRID_N, dtype='f4')
    velocities = np.zeros(GRID_N*GRID_N, dtype='f4')
    spring_k = 0.12
    neighbor_k = 0.18
    damp = 0.88
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
        if sample_format == 8:  # pyaudio.paInt16
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            samples = np.frombuffer(data, dtype=np.float32)
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)
        fft_bars = compute_fft_bars(samples, GRID_N*GRID_N)
        # --- Audiofabric mesh update logic ---
        for i in range(GRID_N*GRID_N):
            target = fft_bars[i] * 2.0
            neighbor_avg = np.mean([heights[j] for j in neighbors[i]]) if neighbors[i] else 0.0
            force = spring_k * (target - heights[i]) + neighbor_k * (neighbor_avg - heights[i])
            velocities[i] = damp * (velocities[i] + force)
        heights += velocities
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

if __name__ == "__main__":
    run_mesh_wave()
