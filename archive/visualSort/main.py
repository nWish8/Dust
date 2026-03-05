import pygame
import random
import time

from sorts import bubble_sort, insertion_sort, selection_sort, merge_sort, quick_sort, heap_sort

BAR_WIDTH = 4
ARRAY_SIZE = 800 // BAR_WIDTH
FPS = 60

ALGORITHMS = [
    ("Bubble Sort", bubble_sort),
    ("Insertion Sort", insertion_sort),
    ("Selection Sort", selection_sort),
    ("Merge Sort", merge_sort),
    ("Quick Sort", quick_sort),
    ("Heap Sort", heap_sort),
]

# Tailwind palette (repeat if more algos than colors)
COLORS = [
    (86, 86, 86),    # Davy's gray
    (252, 122, 74),  # Coral
    (142, 184, 205), # Carolina blue
    (97, 208, 149),  # Emerald
    (109, 76, 61),   # Coffee
    (252, 122, 74),  # Coral (repeat)
]
HIGHLIGHT_COLORS = [
    (97, 208, 149),  # Emerald
    (109, 76, 61),   # Coffee
    (252, 122, 74),  # Coral
    (142, 184, 205), # Carolina blue
    (252, 122, 74),  # Coral
    (86, 86, 86),    # Davy's gray
]
BG_COLOR = (245, 245, 245)
SEPARATOR_COLOR = (200, 200, 200)

# Dynamic height calculation
ALGO_HEIGHT = 120  # px per algorithm
WIDTH = 800
HEIGHT = ALGO_HEIGHT * len(ALGORITHMS)
ARRAY_SIZE = WIDTH // BAR_WIDTH


def draw_arrays(screen, arrays, highlights, finish_times):
    screen.fill(BG_COLOR)
    font = pygame.font.SysFont("Arial", 20, bold=True)
    time_font = pygame.font.SysFont("Arial", 16, bold=True)
    label_height = 22
    margin = 8
    bar_area = ALGO_HEIGHT - label_height - margin
    for idx, arr in enumerate(arrays):
        y_offset = idx * ALGO_HEIGHT
        # Draw label
        label = font.render(ALGORITHMS[idx][0], True, COLORS[idx])
        label_rect = label.get_rect(center=(WIDTH // 2, y_offset + label_height // 2 + 2))
        screen.blit(label, label_rect)
        # Draw finish time if available
        if finish_times[idx] is not None:
            time_str = f"{finish_times[idx]:.2f} s"
            time_label = time_font.render(time_str, True, (0, 0, 0))
            time_rect = time_label.get_rect(center=(WIDTH // 2, y_offset + label_height + 10))
            screen.blit(time_label, time_rect)
        # Draw horizontal separator
        if idx > 0:
            pygame.draw.line(screen, SEPARATOR_COLOR, (0, y_offset), (WIDTH, y_offset), 2)
        for i, val in enumerate(arr):
            color = COLORS[idx]
            if highlights[idx] == i:
                color = HIGHLIGHT_COLORS[idx]
            bar_height = int(bar_area * (val / HEIGHT))
            x = i * BAR_WIDTH
            y = y_offset + ALGO_HEIGHT - bar_height
            pygame.draw.rect(
                screen,
                color,
                pygame.Rect(x, y, BAR_WIDTH, bar_height),
            )
    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Visual Sort Comparison")
    clock = pygame.time.Clock()

    base = [random.randint(10, HEIGHT - 10) for _ in range(ARRAY_SIZE)]
    arrays = [base.copy() for _ in ALGORITHMS]
    generators = [alg(arr) for (_, alg), arr in zip(ALGORITHMS, arrays)]
    highlights = [None] * len(ALGORITHMS)
    start_times = [None] * len(ALGORITHMS)
    finish_times = [None] * len(ALGORITHMS)
    running = True
    sorting = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        if sorting:
            for idx, gen in enumerate(generators):
                if finish_times[idx] is not None:
                    continue
                if start_times[idx] is None:
                    start_times[idx] = time.time()
                try:
                    highlights[idx] = next(gen)
                except StopIteration:
                    highlights[idx] = None
                    finish_times[idx] = time.time() - start_times[idx]
            if all(h is None for h in highlights):
                sorting = False
        draw_arrays(screen, arrays, highlights, finish_times)
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()
