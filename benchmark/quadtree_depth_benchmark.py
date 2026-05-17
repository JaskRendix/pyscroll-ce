import random
import timeit
from argparse import ArgumentParser

from pygame.rect import Rect

from pyscroll.quadtree import FastQuadTree


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


def run_benchmark(depth, item_count, query_count, repeats=3):
    build_times = []
    query_times = []

    for _ in range(repeats):
        items = generate_tile_rects(item_count)

        start = timeit.default_timer()
        tree = FastQuadTree(items, depth=depth)
        build_times.append(timeit.default_timer() - start)

        test_rect = Rect(400, 300, 64, 64)

        start = timeit.default_timer()
        for _ in range(query_count):
            tree.hit(test_rect)
        query_times.append(timeit.default_timer() - start)

    return {
        "depth": depth,
        "build_time": sum(build_times) / repeats,
        "query_time": sum(query_times) / repeats,
    }


def main():
    parser = ArgumentParser()
    parser.add_argument("--min-depth", type=int, default=2)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--items", type=int, default=5000)
    parser.add_argument("--queries", type=int, default=1000)
    args = parser.parse_args()

    results = []
    for depth in range(args.min_depth, args.max_depth + 1):
        results.append(run_benchmark(depth, args.items, args.queries))

    print("Configuration:")
    print(f"  Items:   {args.items}")
    print(f"  Queries: {args.queries}")
    print(f"  Depths:  {args.min_depth}–{args.max_depth}")
    print()
    print("FastQuadTree Depth Benchmark")
    print(f"{'Depth':>5} | {'Build (s)':>10} | {'Query (s)':>10}")
    print("-" * 32)

    for r in results:
        print(f"{r['depth']:>5} | {r['build_time']:.6f} | {r['query_time']:.6f}")

    print()


if __name__ == "__main__":
    main()
