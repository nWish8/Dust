"""Simple real-time audio spectrum visualizer (Bars)."""

from __future__ import annotations

import numpy as np
import pygame
from audio_processing import choose_capture_device, compute_fft_bars, open_output_stream


def run_bars(*, samplerate: int = 44100, blocksize: int = 2048, num_bars: int = 60, interp: float = 0.5) -> None:
    """Run the bar visualization until the window is closed."""
    device_index = choose_capture_device()
    pa, stream, channels, sample_format = open_output_stream(
        samplerate=samplerate,
        blocksize=blocksize,
        device_index=device_index,
    )
    pygame.init()
    width, height = 800, 400
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Audio Bars Visualizer")
    clock = pygame.time.Clock()
    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            data = stream.read(blocksize, exception_on_overflow=False)
            if sample_format == 8:  # pyaudio.paInt16
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                samples = np.frombuffer(data, dtype=np.float32)
            if channels > 1:
                samples = samples.reshape(-1, channels).mean(axis=1)
            bars = compute_fft_bars(samples, num_bars)
            max_val = np.max(bars) if np.max(bars) > 0 else 1e-6

            screen.fill((0, 0, 0))
            bar_width = width / num_bars
            for i, val in enumerate(bars):
                bar_height = int((val / max_val) * height)
                x = int(i * bar_width)
                y = height - bar_height
                pygame.draw.rect(
                    screen,
                    (0, 255, 0),
                    pygame.Rect(x, y, int(bar_width - 2), bar_height),
                )

            pygame.display.flip()
            clock.tick(60)
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    pygame.quit()


if __name__ == "__main__":
    try:
        run_bars()
    except KeyboardInterrupt:
        pass
