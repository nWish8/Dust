from __future__ import annotations

"""Audio capture and processing utilities for the visualizer."""

import sys
from typing import Tuple

import numpy as np
import pyaudio


def choose_capture_device() -> int | None:
    """Prompt the user to select an input or loopback device (MME/WASAPI only, table format)."""
    pa = pyaudio.PyAudio()
    try:
        device_indices: list[int] = []  # Store actual PyAudio device indices
        device_rows = []
        allowed_apis = {"MME", "WASAPI"}
        for idx in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(idx)
            label = info.get("name", "")
            # Skip hands-free devices
            if "hands-free" in label.lower():
                continue
            host_api_index = info.get("hostApi")
            host_api_name = pa.get_host_api_info_by_index(host_api_index).get("name", "?")
            if host_api_name.startswith("Windows "):
                host_api_name = host_api_name.replace("Windows ", "")
            if host_api_name not in allowed_apis:
                continue
            if info.get("maxInputChannels", 0) > 0 or info.get("isLoopbackDevice", False):
                device_indices.append(idx)
                is_loopback = info.get("isLoopbackDevice", False)
                device_rows.append([
                    str(len(device_indices) - 1),
                    label,
                    host_api_name,
                    str(idx),
                    "Yes" if is_loopback else "No"
                ])
        if not device_indices:
            print("No available capture devices.")
            return None
        # Print table header
        header = ["Idx", "Device Name", "Host API", "Device Idx", "Loopback"]
        col_widths = [max(len(row[i]) for row in ([header] + device_rows)) for i in range(len(header))]
        fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
        print(fmt.format(*header))
        print("-" * (sum(col_widths) + 2 * (len(header) - 1)))
        for row in device_rows:
            print(fmt.format(*row))
        choice = input("Select device [0]: ").strip()
        try:
            selection = int(choice) if choice else 0
        except ValueError:
            selection = 0
        if selection < 0 or selection >= len(device_indices):
            selection = 0
        return device_indices[selection]  # Return the actual PyAudio device index
    finally:
        pa.terminate()


def device_channels(info: dict) -> int:
    """Return the supported channel count for a device."""
    return int(info.get("maxInputChannels") or info.get("maxOutputChannels") or 1)


def open_output_stream(*, samplerate: int, blocksize: int, device_index: int | None = None) -> Tuple[pyaudio.PyAudio, pyaudio.Stream, int, int]:
    """Open the highest-precision supported format/channels for the chosen device (float32 preferred, then int16; stereo preferred, then mono)."""
    pa = pyaudio.PyAudio()
    try:
        device = (
            pa.get_device_info_by_index(device_index)
            if device_index is not None
            else pa.get_default_input_device_info()
        )
        device_samplerate = int(device.get("defaultSampleRate", samplerate))
        channels_list = [device.get("maxInputChannels", 1), 1]
        channels_list = [int(c) for c in channels_list if int(c) > 0]
        format_names = {pyaudio.paFloat32: "float32", pyaudio.paInt16: "int16"}
        # Try all combos, preferring float32 stereo > float32 mono > int16 stereo > int16 mono
        combos = []
        for fmt in [pyaudio.paFloat32, pyaudio.paInt16]:
            for ch in sorted(set(channels_list), reverse=True):
                combos.append((fmt, ch))
        for fmt, ch in combos:
            try:
                stream = pa.open(
                    format=fmt,
                    channels=ch,
                    rate=device_samplerate,
                    input=True,
                    frames_per_buffer=blocksize,
                    input_device_index=device["index"],
                )
                print(f"Opened device with {format_names.get(fmt, fmt)} {ch}ch.")
                return pa, stream, ch, fmt
            except Exception as exc:
                print(f"Error: {exc}\nFailed to open with {format_names.get(fmt, fmt)} {ch}ch. Trying next best...")
        pa.terminate()
        raise RuntimeError("No supported format/channel combination for this device.")
    except OSError as exc:
        pa.terminate()
        raise RuntimeError("No input device available") from exc


def compute_fft_bars(samples: np.ndarray, num_bars: int) -> np.ndarray:
    """Return averaged magnitude spectrum values for ``samples`` with DC removal and windowing."""
    # Remove DC offset
    samples = samples - np.mean(samples)
    # Apply Hann window
    window = np.hanning(len(samples))
    windowed = samples * window
    spectrum = np.abs(np.fft.rfft(windowed))
    bins = np.linspace(0, len(spectrum), num_bars + 1, dtype=int)
    return np.array([spectrum[bins[i] : bins[i + 1]].mean() for i in range(num_bars)])

