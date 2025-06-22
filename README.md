# Dust Audio Visualizer

This repository contains a small real-time audio visualizer written in Python. It captures audio directly from the system's default **speaker output** (loopback) using the `soundcard` library and displays the frequency spectrum in a Pygame window. No physical microphone is required.

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
python visualizer.py
```

Close the window or press `Ctrl+C` to exit.
