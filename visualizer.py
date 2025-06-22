"""Simple real-time audio spectrum visualizer.

This script captures audio from the system's default output device using the
``soundcard`` library and displays the frequency spectrum in a Pygame window.
It serves as a lightweight proof-of-concept for real-time audio visualization.
"""

from __future__ import annotations

import numpy as np
import pygame
import soundcard as sc


def open_output_recorder(samplerate: int) -> sc.Recorder:
    """Return a recorder capturing the default speaker output."""
    speaker = sc.default_speaker()
    mic = sc.get_microphone(str(speaker.name), include_loopback=True)
    return mic.recorder(samplerate=samplerate)


def compute_fft_bars(samples: np.ndarray, num_bars: int) -> np.ndarray:
    """Return averaged magnitude spectrum values for ``samples``.

    Parameters
    ----------
    samples:
        Mono audio samples.
    num_bars:
        Number of output frequency bands.
    """
    spectrum = np.abs(np.fft.rfft(samples))
    bins = np.linspace(0, len(spectrum), num_bars + 1, dtype=int)
    return np.array([spectrum[bins[i] : bins[i + 1]].mean() for i in range(num_bars)])


def run_visualizer(*, samplerate: int = 44100, blocksize: int = 1024, num_bars: int = 60) -> None:
    """Run the visualization until the window is closed."""
    recorder_cm = open_output_recorder(samplerate)

    pygame.init()
    width, height = 800, 400
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Audio Visualizer")
    clock = pygame.time.Clock()

    with recorder_cm as recorder:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            data = recorder.record(numframes=blocksize)
            mono = data.mean(axis=1)
            bars = compute_fft_bars(mono, num_bars)
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

    pygame.quit()


if __name__ == "__main__":
    try:
        run_visualizer()
    except KeyboardInterrupt:
        pass
