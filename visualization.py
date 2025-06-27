from __future__ import annotations

"""Pygame based visualization for the audio spectrum."""

import numpy as np
import pygame
import pyaudio

from audio_processing import (
    choose_capture_device,
    open_output_stream,
    compute_fft_bars,
)


def run_visualization(*, samplerate: int = 44100, blocksize: int = 2048, num_bars: int = 60, interp: float = 0.5) -> None:
    """Run the visualization until the window is closed. Uses buffered FFT and optional interpolation."""
    device_index = choose_capture_device()
    while True:
        try:
            pa, stream, channels, sample_format = open_output_stream(
                samplerate=samplerate,
                blocksize=blocksize,
                device_index=device_index,
            )
            break
        except RuntimeError as exc:
            print(f"Error: {exc}")
            device_index = choose_capture_device()

    pygame.init()
    width, height = 800, 400
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Audio Visualizer")
    clock = pygame.time.Clock()

    last_bars = np.zeros(num_bars)
    bars = np.zeros(num_bars)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Only read a new buffer if needed (audio thread rate, not render FPS)
        data = stream.read(blocksize, exception_on_overflow=False)
        if sample_format == pyaudio.paInt16:
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            samples = np.frombuffer(data, dtype=np.float32)
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)
        # Compute FFT bars for this buffer
        new_bars = compute_fft_bars(samples, num_bars)
        # Interpolate for smoothness
        bars = interp * new_bars + (1 - interp) * last_bars
        last_bars = bars.copy()

        max_val = np.max(bars) if np.max(bars) > 0 else 1e-6
        screen.fill((0, 0, 0))
        bar_width = width / num_bars
        for i, val in enumerate(bars):
            bar_height = int((val / max_val) * height)
            x = int(i * bar_width)
            y = height - bar_height
            pygame.draw.rect(
                screen,
                (0, 200, 0),  # Green color
                pygame.Rect(x, y, int(bar_width - 2), bar_height),
            )
        pygame.display.flip()
        clock.tick(60)

    stream.stop_stream()
    stream.close()
    pa.terminate()
    pygame.quit()
