"""Simple real-time audio spectrum visualizer.

This script captures audio from the system's default **output** device using
``pyaudio`` on Windows and displays the frequency spectrum in a Pygame window.
It serves as a lightweight proof of concept for real-time audio visualization.
On other platforms, the default input device is used instead.
"""

from __future__ import annotations

import numpy as np
import pygame
import pyaudio
import sys



def open_output_stream(
    *, samplerate: int, blocksize: int
) -> tuple[pyaudio.PyAudio, pyaudio.Stream, int]:
    """Return a PyAudio stream capturing the default output device.

    On Windows this uses WASAPI loopback so whatever is playing through the
    speakers will be captured. On other platforms the default input device is
    used as a fallback.
    """
    pa = pyaudio.PyAudio()

    if sys.platform == "win32":
        # Attempt to locate the default speaker's loopback device.
        wasapi_info = None
        for i in range(pa.get_host_api_count()):
            info = pa.get_host_api_info_by_index(i)
            if info.get("type") == pyaudio.paWASAPI:
                wasapi_info = info
                break

        if wasapi_info is not None:
            device = pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            if not device.get("isLoopbackDevice", False):
                for i in range(pa.get_device_count()):
                    dev = pa.get_device_info_by_index(i)
                    if (
                        dev.get("hostApi") == wasapi_info["index"]
                        and dev.get("isLoopbackDevice")
                        and dev.get("name") == device.get("name")
                    ):
                        device = dev
                        break
            channels = max(int(device.get("maxInputChannels", 1)), 1)
            stream = pa.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=samplerate,
                frames_per_buffer=blocksize,
                input=True,
                input_device_index=device["index"],
            )
            return pa, stream, channels

    # Fallback: capture from the default input device
    device = pa.get_default_input_device_info()
    channels = max(int(device.get("maxInputChannels", 1)), 1)
    stream = pa.open(
        format=pyaudio.paFloat32,
        channels=channels,
        rate=samplerate,
        input=True,
        frames_per_buffer=blocksize,
    )
    return pa, stream, channels


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
    pa, stream, channels = open_output_stream(samplerate=samplerate, blocksize=blocksize)

    pygame.init()
    width, height = 800, 400
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Audio Visualizer")
    clock = pygame.time.Clock()

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            data = stream.read(blocksize, exception_on_overflow=False)
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
        run_visualizer()
    except KeyboardInterrupt:
        pass
