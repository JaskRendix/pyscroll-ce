from __future__ import annotations

import time

from pygame import Rect

from pyscroll.viewport import ViewPort


class DummyData:
    def __init__(self, tile_size=(32, 32), map_size=(3000, 3000)):
        self.tile_size = tile_size
        self.map_size = map_size


def bench(label, func, iterations=200_000):
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    end = time.perf_counter()

    total = end - start
    per_call = (total / iterations) * 1_000_000  # microseconds

    print(f"{label:<30} {per_call:8.3f} µs per call")


def main():
    print("ViewPort Benchmark")

    data = DummyData()
    vp = ViewPort(data=data, size=(640, 480), zoom=1.0, clamp_camera=True)

    vp.center((1000, 1000))

    bench("center()", lambda: vp.center((1000, 1000)), iterations=50_000)

    bench("translate_point()", lambda: vp.translate_point((123, 456)))
    bench("translate_rect()", lambda: vp.translate_rect((10, 20, 30, 40)))

    pts = [(i, i * 2) for i in range(32)]
    bench("translate_points(32)", lambda: vp.translate_points(pts), iterations=20_000)

    rects = [Rect(i, i * 2, 16, 16) for i in range(32)]
    bench("translate_rects(32)", lambda: vp.translate_rects(rects), iterations=20_000)


if __name__ == "__main__":
    main()
