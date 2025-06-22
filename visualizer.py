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


def choose_output_device() -> int | None:
    """Prompt the user to select an output device.

    Returns the PyAudio device index or ``None`` for the default device.
    """
    pa = pyaudio.PyAudio()
    try:
        devices: list[int] = []
        print("Available output devices:")
        for idx in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(idx)
            if sys.platform == "win32":
                if info.get("maxOutputChannels", 0) > 0 and not info.get("isLoopbackDevice", False):
                    devices.append(idx)
                    print(f"{len(devices) - 1}: {info.get('name')}")
            else:
                if info.get("maxInputChannels", 0) > 0:
                    devices.append(idx)
                    print(f"{len(devices) - 1}: {info.get('name')}")

        if not devices:
            return None

        choice = input("Select device [0]: ").strip()
        try:
            selection = int(choice) if choice else 0
        except ValueError:
            selection = 0
        if selection < 0 or selection >= len(devices):
            selection = 0
        return devices[selection]
    finally:
        pa.terminate()



def open_output_stream(
    *, samplerate: int, blocksize: int, device_index: int | None = None
) -> tuple[pyaudio.PyAudio, pyaudio.Stream, int]:
    """Return a PyAudio stream capturing the chosen output device.

    On Windows this uses WASAPI loopback so whatever is playing through the
    selected speakers will be captured. On other platforms the chosen input
    device is used as a fallback.
    """
    pa = pyaudio.PyAudio()

    if sys.platform == "win32":
        # Locate the WASAPI host API for loopback capture
        wasapi_info = None
        for i in range(pa.get_host_api_count()):
            info = pa.get_host_api_info_by_index(i)
            if info.get("type") == pyaudio.paWASAPI:
                wasapi_info = info
                break

        if wasapi_info is not None:
            out_device = (
                pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
                if device_index is None
                else pa.get_device_info_by_index(device_index)
            )

            device = out_device
            if not device.get("isLoopbackDevice", False):
                for i in range(pa.get_device_count()):
                    dev = pa.get_device_info_by_index(i)
                    if (
                        dev.get("hostApi") == wasapi_info["index"]
                        and dev.get("isLoopbackDevice")
                        and dev.get("name") == out_device.get("name")
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

    # Fallback: capture from the default or selected input device
    device = (
        pa.get_device_info_by_index(device_index)
        if device_index is not None
        else pa.get_default_input_device_info()
    )
    channels = max(int(device.get("maxInputChannels", 1)), 1)
    stream = pa.open(
        format=pyaudio.paFloat32,
        channels=channels,
        rate=samplerate,
        input=True,
        frames_per_buffer=blocksize,
        input_device_index=device["index"],
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
    device_index = choose_output_device()
    pa, stream, channels = open_output_stream(
        samplerate=samplerate,
        blocksize=blocksize,
        device_index=device_index,
    )

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
