from __future__ import annotations

"""Entry point for the Dust audio visualizer."""

from visualization import run_visualization


if __name__ == "__main__":
    try:
        run_visualization()
    except KeyboardInterrupt:
        pass
