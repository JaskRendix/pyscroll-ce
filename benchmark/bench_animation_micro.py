import random
import time
from unittest.mock import MagicMock

from pyscroll.animation import AnimationFrame, AnimationToken


def micro_benchmark(iterations=1_000_000):
    surf = MagicMock()
    frames = [
        AnimationFrame(image=surf, duration=0.1),
        AnimationFrame(image=surf, duration=0.2),
        AnimationFrame(image=surf, duration=0.3),
    ]

    token = AnimationToken(
        positions={(0, 0, 0)},
        frames=frames,
        loop=True,
        speed_multiplier=1.0,
        ping_pong=False,
    )

    start = time.perf_counter()

    for _ in range(iterations):
        t = random.uniform(0, 10)
        token.update(current_time=t, elapsed_time=None)

    end = time.perf_counter()
    total = end - start

    print(f"Iterations: {iterations}")
    print(f"Total time: {total:.6f} seconds")
    print(f"Per update: {total / iterations * 1e9:.2f} ns")


if __name__ == "__main__":
    micro_benchmark()
