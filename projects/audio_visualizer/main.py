from __future__ import annotations

"""Entry point for the Dust audio visualizer."""

from bars import run_bars
from mesh_wave import run_mesh_wave
from mesh_ripple import run_mesh_ripple


def select_visualizer() -> str:
    print("Select a visualizer to run:")
    print("1. Bars")
    print("2. Mesh Wave")
    print("3. Mesh Ripple")
    choice = input("Enter 1, 2, or 3: ").strip()
    if choice == "2":
        return "mesh_wave"
    elif choice == "3":
        return "mesh_ripple"
    else:
        return "bars"


if __name__ == "__main__":
    try:
        vis = select_visualizer()
        if vis == "bars":
            run_bars()
        elif vis == "mesh_wave":
            run_mesh_wave()
        elif vis == "mesh_ripple":
            run_mesh_ripple()
    except KeyboardInterrupt:
        pass