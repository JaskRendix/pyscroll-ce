import random
import time
from unittest.mock import MagicMock

from pyscroll.animation import AnimationFrame, AnimationToken


def macro_benchmark(token_count=5000, cycles=200):
    surf = MagicMock()
    positions = {(0, 0, 0)}

    tokens = []
    for _ in range(token_count):
        frames = [
            AnimationFrame(
                image=surf,
                duration=random.uniform(0.01, 0.5),
                frame_speed_multiplier=random.uniform(0.5, 2.0),
            )
            for _ in range(random.randint(1, 5))
        ]

        token = AnimationToken(
            positions=positions,
            frames=frames,
            initial_time=random.uniform(0, 5),
            loop=random.choice([True, False]),
            speed_multiplier=random.uniform(0.5, 3.0),
            ping_pong=random.choice([True, False]),
            random_jitter=random.uniform(0.0, 0.1),
            random_start_frame=random.choice([True, False]),
        )
        tokens.append(token)

    start = time.perf_counter()

    for _ in range(cycles):
        current_time = random.uniform(0, 10)
        for token in tokens:
            token.update(current_time=current_time, elapsed_time=None)

    end = time.perf_counter()
    total = end - start

    print(f"Tokens: {token_count}")
    print(f"Cycles: {cycles}")
    print(f"Total updates: {token_count * cycles}")
    print(f"Total time: {total:.6f} seconds")
    print(f"Per update: {total / (token_count * cycles) * 1e6:.2f} µs")


if __name__ == "__main__":
    macro_benchmark()
