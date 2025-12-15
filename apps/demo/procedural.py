# This little demo is just a sandbox to show off how the ProceduralData adapter
# plugs into BufferedRenderer. No map files needed — you get a checkerboard of
# grass and water, some rocks sprinkled in, and animated tiles you can pan/zoom
# around with. Think of it as a quick visual smoke test rather than a full game.

import pygame

from pyscroll.data import ProceduralData
from pyscroll.orthographic import BufferedRenderer


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()

    data = ProceduralData()
    renderer = BufferedRenderer(data, (800, 600))

    renderer.center(
        (
            data.map_size[0] * data.tile_size[0] // 2,
            data.map_size[1] * data.tile_size[1] // 2,
        )
    )

    offset_x, offset_y = 0, 0
    zoom = 1.0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            offset_x -= 10
        if keys[pygame.K_RIGHT]:
            offset_x += 10
        if keys[pygame.K_UP]:
            offset_y -= 10
        if keys[pygame.K_DOWN]:
            offset_y += 10
        if keys[pygame.K_PLUS] or keys[pygame.K_EQUALS]:  # '+' key
            zoom = min(2.0, zoom + 0.05)
        if keys[pygame.K_MINUS]:
            zoom = max(0.5, zoom - 0.05)

        renderer.zoom = zoom
        renderer.center(
            (
                data.map_size[0] * data.tile_size[0] // 2 + offset_x,
                data.map_size[1] * data.tile_size[1] // 2 + offset_y,
            )
        )

        data._update_time()
        data.process_animation_queue(renderer._tile_view)

        screen.fill((0, 0, 0))
        renderer.draw(screen, screen.get_rect())
        pygame.display.flip()

        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
