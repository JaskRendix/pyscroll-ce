import random

import pygame
from pygame.rect import Rect

from pyscroll.quadtree import FastQuadTree

SCREEN_SIZE = (800, 600)
TILE_SIZE = (32, 32)
RECT_COUNT = 1000
DEPTH = 3
QUERY_RECT = Rect(400, 300, 64, 64)
FPS = 30


def generate_tile_rects(n, bounds=(0, 0, 800, 600), tile_size=(32, 32)):
    x0, y0, w, h = bounds
    tw, th = tile_size
    return [
        Rect(
            random.randint(x0, x0 + w - tw),
            random.randint(y0, y0 + h - th),
            tw,
            th,
        )
        for _ in range(n)
    ]


def main():
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    tile_rects = generate_tile_rects(
        RECT_COUNT, bounds=(0, 0, *SCREEN_SIZE), tile_size=TILE_SIZE
    )
    tree = FastQuadTree(tile_rects, depth=DEPTH)

    running = True
    show_hits = True

    while running:
        screen.fill((30, 30, 30))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_h:
                show_hits = not show_hits

        for rect in tile_rects:
            pygame.draw.rect(screen, (120, 120, 120), rect, 1)

        pygame.draw.rect(screen, (0, 128, 255), QUERY_RECT, 2)

        hits = tree.hit(QUERY_RECT)
        if show_hits:
            for hit_rect in hits:
                pygame.draw.rect(screen, (255, 0, 0), hit_rect, 2)

        text = font.render(
            f"Hits: {len(hits)}  |  Press H to toggle", True, (240, 240, 240)
        )
        screen.blit(text, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
