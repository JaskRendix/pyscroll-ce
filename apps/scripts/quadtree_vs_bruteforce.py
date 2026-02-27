"""
Multi-scale Performance Benchmark: FastQuadTree vs Brute-force

Runs benchmarks with increasing numbers of rectangles to show how
quadtree query time scales compared to brute-force.
"""

import random
import timeit

from pygame.rect import Rect
from pyscroll.quadtree import FastQuadTree


def generate_rects(n, bounds=(0, 0, 800, 600), tile_size=(32, 32)) -> list[Rect]:
    x0, y0, w, h = bounds
    tw, th = tile_size
    return [
        Rect(random.randint(x0, x0 + w - tw), random.randint(y0, y0 + h - th), tw, th)
        for _ in range(n)
    ]


def brute_force_hit(items: list[Rect], target: Rect) -> list[Rect]:
    return [r for r in items if r.colliderect(target)]


def run_benchmark(item_count, query_count=1000, depth=4):
    items = generate_rects(item_count)
    queries = [
        Rect(random.randint(0, 800), random.randint(0, 600), 64, 64)
        for _ in range(query_count)
    ]

    # Build quadtree
    start = timeit.default_timer()
    tree = FastQuadTree(items, depth=depth)
    build_time = timeit.default_timer() - start

    # Quadtree queries
    start = timeit.default_timer()
    for q in queries:
        tree.hit(q)
    quadtree_time = timeit.default_timer() - start

    # Brute force queries
    start = timeit.default_timer()
    for q in queries:
        brute_force_hit(items, q)
    brute_time = timeit.default_timer() - start

    return build_time, quadtree_time, brute_time


def benchmark_series(sizes=(1000, 5000, 10000, 20000), query_count=1000, depth=4):
    print(f"\nBenchmarking with query_count={query_count}, depth={depth}\n")
    for n in sizes:
        build, qt_time, bf_time = run_benchmark(n, query_count, depth)
        print(f"{n:6d} rects:")
        print(f"  Build Time:   {build:.6f}s")
        print(f"  Quadtree Time:{qt_time:.6f}s")
        print(f"  Brute-force:  {bf_time:.6f}s\n")


if __name__ == "__main__":
    benchmark_series()
