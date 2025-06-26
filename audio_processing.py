from __future__ import annotations

"""Audio capture and processing utilities for the visualizer."""

import sys
from typing import Tuple

import numpy as np
import pyaudio


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


def device_channels(info: dict) -> int:
    """Return the supported channel count for a device."""
    return int(info.get("maxInputChannels") or info.get("maxOutputChannels") or 1)


def open_output_stream(*, samplerate: int, blocksize: int, device_index: int | None = None) -> Tuple[pyaudio.PyAudio, pyaudio.Stream, int]:
    """Return a PyAudio stream capturing the chosen output device."""
    pa = pyaudio.PyAudio()

    if sys.platform == "win32":
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

            channels = device_channels(device)
            stream = pa.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=samplerate,
                frames_per_buffer=blocksize,
                input=True,
                input_device_index=device["index"],
            )
            return pa, stream, channels

    try:
        device = (
            pa.get_device_info_by_index(device_index)
            if device_index is not None
            else pa.get_default_input_device_info()
        )
        channels = device_channels(device)
        stream = pa.open(
            format=pyaudio.paFloat32,
            channels=channels,
            rate=samplerate,
            input=True,
            frames_per_buffer=blocksize,
            input_device_index=device["index"],
        )
        return pa, stream, channels
    except OSError as exc:
        pa.terminate()
        raise RuntimeError("No input device available") from exc


def compute_fft_bars(samples: np.ndarray, num_bars: int) -> np.ndarray:
    """Return averaged magnitude spectrum values for ``samples``."""
    spectrum = np.abs(np.fft.rfft(samples))
    bins = np.linspace(0, len(spectrum), num_bars + 1, dtype=int)
    return np.array([spectrum[bins[i] : bins[i + 1]].mean() for i in range(num_bars)])

