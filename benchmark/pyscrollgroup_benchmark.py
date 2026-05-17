import time
from unittest.mock import MagicMock

import pygame
from pygame.rect import Rect
from pygame.sprite import Sprite
from pygame.surface import Surface

from pyscroll.group import PyscrollGroup
from pyscroll.orthographic import BufferedRenderer


def make_sprite(x, y):
    spr = Sprite()
    spr.image = Surface((32, 32))
    spr.rect = Rect(x, y, 32, 32)
    return spr


def benchmark_group(n_sprites=5000, iterations=200):
    pygame.init()

    map_layer = MagicMock(spec=BufferedRenderer)
    map_layer.get_center_offset.return_value = (0, 0)
    map_layer.view_rect = Rect(0, 0, 800, 600)
    map_layer.draw.return_value = []

    group = PyscrollGroup(map_layer)
    surface = Surface((800, 600))

    for i in range(n_sprites):
        group.add(make_sprite(i % 800, (i * 3) % 600))

    for _ in range(20):
        group.draw(surface)

    start = time.perf_counter()
    for _ in range(iterations):
        group.draw(surface)
    end = time.perf_counter()

    total = end - start
    per_frame = total / iterations

    print(f"Sprites: {n_sprites}")
    print(f"Iterations: {iterations}")
    print(f"Total time: {total:.4f}s")
    print(f"Avg per frame: {per_frame * 1000:.3f} ms")
    print(f"FPS equivalent: {1 / per_frame:.1f} FPS")


def benchmark_culling(n_sprites=5000):
    pygame.init()

    map_layer = MagicMock(spec=BufferedRenderer)
    map_layer.get_center_offset.return_value = (0, 0)
    map_layer.view_rect = Rect(0, 0, 800, 600)
    map_layer.draw.return_value = []

    group = PyscrollGroup(map_layer)
    surface = Surface((800, 600))

    for i in range(n_sprites):
        x = 2000 if i % 20 else i % 800
        y = 2000 if i % 20 else (i * 3) % 600
        group.add(make_sprite(x, y))

    start = time.perf_counter()
    for _ in range(200):
        group.draw(surface)
    end = time.perf_counter()

    print(f"Culling benchmark: {end - start}")


def benchmark_renderable_creation(n=200000):
    from pyscroll.group import Renderable

    start = time.perf_counter()
    for _ in range(n):
        Renderable(1, Rect(0, 0, 32, 32), None, None)
    end = time.perf_counter()

    print(f"Renderable creation: {end - start:.4f}s for {n} instances")


def benchmark_spritedict(n=5000):
    group = PyscrollGroup(MagicMock(spec=BufferedRenderer))
    spritedict = group.spritedict

    sprites = [make_sprite(i, i) for i in range(n)]
    for spr in sprites:
        spritedict[spr] = spr.rect

    start = time.perf_counter()
    for spr in sprites:
        spritedict[spr] = spr.rect.move(5, 5)
    end = time.perf_counter()

    print(f"spritedict update: {end - start:.4f}s for {n} updates")


if __name__ == "__main__":
    print("PyscrollGroup Benchmark")
    benchmark_group()
    benchmark_culling()
    benchmark_renderable_creation()
    benchmark_spritedict()
