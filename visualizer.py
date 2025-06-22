import numpy as np
import pygame
import soundcard as sc


def get_default_microphone(samplerate: int) -> sc.Microphone:
    """Return a microphone capturing the default speaker in loopback."""
    speaker = sc.default_speaker()
    return sc.get_microphone(str(speaker.name), include_loopback=True)


def compute_spectrum(samples: np.ndarray, num_bars: int) -> np.ndarray:
    """Return averaged frequency magnitudes for the given samples."""
    spectrum = np.abs(np.fft.rfft(samples))
    bins = np.linspace(0, len(spectrum), num_bars + 1, dtype=int)
    bar_values = np.array([
        spectrum[bins[i] : bins[i + 1]].mean() for i in range(num_bars)
    ])
    return bar_values


def main() -> None:
    samplerate = 44100
    blocksize = 1024
    num_bars = 60

    mic = get_default_microphone(samplerate)

    pygame.init()
    width, height = 800, 400
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Audio Visualizer")
    clock = pygame.time.Clock()

    with mic.recorder(samplerate=samplerate) as recorder:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            data = recorder.record(numframes=blocksize)
            mono = data.mean(axis=1)
            bars = compute_spectrum(mono, num_bars)
            max_val = np.max(bars)
            if max_val <= 0:
                max_val = 1e-6

            screen.fill((0, 0, 0))
            bar_width = width / num_bars
            for i, val in enumerate(bars):
                bar_height = int((val / max_val) * height)
                x = int(i * bar_width)
                y = height - bar_height
                pygame.draw.rect(
                    screen,
                    (0, 255, 0),
                    (x, y, int(bar_width - 2), bar_height),
                )

            pygame.display.flip()
            clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
