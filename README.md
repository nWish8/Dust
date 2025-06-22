# Dust Audio Visualizer

This repository contains a small real-time audio visualizer written in Python. It captures audio directly from the system's default **speaker output** (loopback) using the `soundcard` library and displays the frequency spectrum in a Pygame window. No physical microphone is required.

## Requirements

```
pip install soundcard numpy pygame
```

## Usage

Run the visualizer with:

```
python visualizer.py
```

Close the window or press `Ctrl+C` to exit.
