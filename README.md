# Dust Audio Visualizer

This repository contains a small real-time audio visualizer written in Python. It captures audio using the `pyaudio` library and displays the frequency spectrum in a Pygame window. On startup the program lists all devices that can be sampled from (microphones or loopback outputs) so you can easily choose the source. The program automatically uses the device's input channel count when available and otherwise falls back to its output channel count so it works with both stereo and mono sources and avoids "invalid number of channels" errors.

## Setup (Windows)

1. Ensure Python 3.x is installed.
2. Create and activate a virtual environment:
   ```bat
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bat
   pip install -r requirements.txt
   ```

## Usage

Run the visualizer with:

```bash
python main.py
```

Close the window or press `Ctrl+C` to exit.
