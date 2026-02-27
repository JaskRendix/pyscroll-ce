"""
Enhanced Animated Tile Demo using Pygame + Pyscroll AnimationToken

This demo showcases:
- Looping animations
- Ping-pong animations
- Per-frame speed multipliers
- Global speed multipliers
- Random jitter (desynchronization)
"""

import random

import pygame
from pygame.locals import QUIT
from pyscroll.animation import AnimationFrame, AnimationToken


def make_frames(colors, size=(32, 32), base_duration=0.4) -> list[AnimationFrame]:
    """Create frames with optional per-frame speed multipliers."""
    frames = []
    for color in colors:
        surf = pygame.Surface(size).convert()
        surf.fill(color)

        # Random per-frame speed multiplier (0.5x to 2x)
        frame_speed = random.uniform(0.5, 2.0)

        frames.append(
            AnimationFrame(
                image=surf,
                duration=base_duration,
                frame_speed_multiplier=frame_speed,
            )
        )
    return frames


def create_tokens(count, tile_size, screen_size) -> list[AnimationToken]:
    tokens = []
    for _ in range(count):
        x = random.randint(0, screen_size[0] - tile_size)
        y = random.randint(0, screen_size[1] - tile_size)
        position = {(x, y, 0)}

        # Random color palette
        colors = random.sample(
            [
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255),
                (255, 255, 0),
                (255, 0, 255),
                (0, 255, 255),
            ],
            3,
        )

        frames = make_frames(colors, size=(tile_size, tile_size))

        # Random behavior flags
        loop = random.choice([True, True, True, False])  # mostly looping
        ping_pong = random.choice([True, False])
        speed_multiplier = random.uniform(0.5, 2.0)
        jitter = random.uniform(0.0, 0.3)

        token = AnimationToken(
            positions=position,
            frames=frames,
            loop=loop,
            ping_pong=ping_pong,
            speed_multiplier=speed_multiplier,
            random_jitter=jitter,
        )

        tokens.append(token)

    return tokens


def main():
    pygame.init()
    screen_size = (640, 480)
    screen = pygame.display.set_mode(screen_size)
    pygame.display.set_caption("Enhanced AnimationToken Demo")

    clock = pygame.time.Clock()
    tile_size = 32

    tokens = create_tokens(20, tile_size, screen_size)

    current_time = 0.0
    running = True

    while running:
        elapsed = clock.tick(60) / 1000.0
        current_time += elapsed

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        screen.fill((20, 20, 20))

        for token in tokens:
            frame = token.update(current_time, elapsed)
            for pos in token.positions:
                screen.blit(frame.image, (pos[0], pos[1]))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
