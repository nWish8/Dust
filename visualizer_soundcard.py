"""Audio spectrum visualizer using the `soundcard` library.

This script mirrors the functionality of ``visualizer.py`` but captures audio
output via the ``soundcard`` package instead of ``pyaudio``. It opens the system
speaker in loopback mode (where supported) and displays a real-time frequency
spectrum in a Pygame window.
"""

from __future__ import annotations

import numpy as np
import pygame
import soundcard as sc


def choose_speaker() -> sc.Speaker:
    """Prompt the user to select an output device.

    Returns the chosen ``soundcard.Speaker`` instance. If no valid choice is
    made, the default speaker is returned.
    """

    speakers = list(sc.all_speakers())
    if not speakers:
        raise RuntimeError("No speaker devices found")

    print("Available speaker devices:")
    for idx, speaker in enumerate(speakers):
        print(f"{idx}: {speaker.name}")

    choice = input("Select device [0]: ").strip()
    try:
        selection = int(choice) if choice else 0
    except ValueError:
        selection = 0
    if selection < 0 or selection >= len(speakers):
        selection = 0
    return speakers[selection]


def compute_fft_bars(samples: np.ndarray, num_bars: int) -> np.ndarray:
    """Return averaged magnitude spectrum values for ``samples``."""

    spectrum = np.abs(np.fft.rfft(samples))
    bins = np.linspace(0, len(spectrum), num_bars + 1, dtype=int)
    return np.array([spectrum[bins[i] : bins[i + 1]].mean() for i in range(num_bars)])


def run_visualizer(*, samplerate: int = 44100, blocksize: int = 1024, num_bars: int = 60) -> None:
    """Run the visualization until the window is closed."""

    try:
        speaker = choose_speaker()
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return

    channels = speaker.channels or 2

    with speaker.recorder(samplerate=samplerate, channels=channels, blocksize=blocksize) as mic:
        pygame.init()
        width, height = 800, 400
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Audio Visualizer (soundcard)")
        clock = pygame.time.Clock()

        running = True
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                data = mic.record(numframes=blocksize)
                if data.ndim > 1:
                    samples = data.mean(axis=1)
                else:
                    samples = data

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
            pygame.quit()


if __name__ == "__main__":
    try:
        run_visualizer()
    except KeyboardInterrupt:
        pass

