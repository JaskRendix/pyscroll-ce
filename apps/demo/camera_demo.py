from __future__ import annotations

from pathlib import Path

import pygame
import pygame.locals
from pygame.math import Vector2
from pygame.sprite import Sprite
from pygame.surface import Surface
from pyscroll.camera import (
    BasicCamera,
    CutsceneCamera,
    DebugFlyCamera,
    PlatformerCamera,
    ZoomCamera,
)
from pyscroll.camera_manager import CameraManager
from pyscroll.data import MapAggregator, TiledMapData
from pyscroll.group import PyscrollGroup
from pyscroll.orthographic import BufferedRenderer
from pytmx.util_pygame import load_pygame  # type: ignore

CURRENT_DIR = Path(__file__).parent
RESOURCES_DIR = CURRENT_DIR
WINDOW_SIZE = (800, 600)
HERO_MOVE_SPEED = 200
ZOOM_STEP = 0.25
INITIAL_ZOOM = 2.0


def load_image(filename: str) -> Surface:
    path = RESOURCES_DIR / filename
    return pygame.image.load(str(path)).convert_alpha()


class Hero(Sprite):
    def __init__(self):
        super().__init__()
        self.image = load_image("hero.png")
        self.velocity = Vector2(0, 0)
        self.position = Vector2(400, 400)
        self.old_position = self.position.copy()
        self.rect = self.image.get_rect(topleft=self.position)

    def update(self, dt: float):
        self.old_position = self.position.copy()
        self.position += self.velocity * dt
        self.rect.topleft = self.position


class CameraDemo:
    def __init__(self, screen: Surface):
        self.screen = screen
        self.running = False

        world_data = MapAggregator((16, 16))
        stitched_maps = [
            ("stitched0.tmx", (-20, -20)),
            ("stitched1.tmx", (0, -20)),
            ("stitched2.tmx", (20, -20)),
            ("stitched3.tmx", (-20, 0)),
            ("stitched4.tmx", (0, 0)),
            ("stitched5.tmx", (20, 0)),
            ("stitched6.tmx", (-20, 20)),
            ("stitched7.tmx", (0, 20)),
            ("stitched8.tmx", (20, 20)),
        ]

        for filename, offset in stitched_maps:
            tmx = load_pygame(str(RESOURCES_DIR / filename))
            world_data.add_map(TiledMapData(tmx), offset)

        self.map_layer = BufferedRenderer(
            world_data, screen.get_size(), clamp_camera=True
        )
        self.map_layer.zoom = INITIAL_ZOOM
        self.group = PyscrollGroup(map_layer=self.map_layer)

        self.hero = Hero()
        self.group.add(self.hero)

        self.cam_smooth = BasicCamera()
        self.cam_platformer = PlatformerCamera()
        self.cam_zoom = ZoomCamera(self.cam_smooth, zoom=1.0)
        self.cam_cutscene = CutsceneCamera(
            waypoints=[(200, 200), (600, 200), (600, 600), (200, 600)],
            duration=8.0,
            loop=True,
        )
        self.cam_debug = DebugFlyCamera()

        self.camera_manager = CameraManager(self.cam_smooth)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.locals.QUIT:
                self.running = False
            elif event.type == pygame.locals.KEYDOWN:
                if event.key == pygame.locals.K_ESCAPE:
                    self.running = False

                elif event.key == pygame.locals.K_1:
                    self.camera_manager.set_camera(self.cam_smooth, duration=1.0)
                elif event.key == pygame.locals.K_2:
                    self.camera_manager.set_camera(self.cam_platformer, duration=1.0)
                elif event.key == pygame.locals.K_3:
                    self.camera_manager.set_camera(self.cam_zoom, duration=1.0)
                elif event.key == pygame.locals.K_4:
                    self.camera_manager.set_camera(self.cam_cutscene, duration=1.0)
                elif event.key == pygame.locals.K_5:
                    self.camera_manager.set_camera(self.cam_debug, duration=0.5)

                elif event.key == pygame.locals.K_EQUALS:
                    self.map_layer.zoom += ZOOM_STEP
                elif event.key == pygame.locals.K_MINUS:
                    if self.map_layer.zoom - ZOOM_STEP > 0:
                        self.map_layer.zoom -= ZOOM_STEP

            elif event.type == pygame.locals.VIDEORESIZE:
                self.screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE
                )
                self.map_layer.set_size((event.w, event.h))

        pressed = pygame.key.get_pressed()
        self.hero.velocity.xy = 0, 0

        if pressed[pygame.locals.K_UP]:
            self.hero.velocity.y = -HERO_MOVE_SPEED
        elif pressed[pygame.locals.K_DOWN]:
            self.hero.velocity.y = HERO_MOVE_SPEED

        if pressed[pygame.locals.K_LEFT]:
            self.hero.velocity.x = -HERO_MOVE_SPEED
        elif pressed[pygame.locals.K_RIGHT]:
            self.hero.velocity.x = HERO_MOVE_SPEED

        dx = dy = 0
        if pressed[pygame.locals.K_w]:
            dy = -1
        if pressed[pygame.locals.K_s]:
            dy = 1
        if pressed[pygame.locals.K_a]:
            dx = -1
        if pressed[pygame.locals.K_d]:
            dx = 1
        self.cam_debug.set_input(dx, dy)

    def update(self, dt: float):
        self.group.update(dt)
        new_center = self.camera_manager.update(self.group.view, self.hero.rect, dt)
        self.group.center(new_center)

    def draw(self):
        self.group.draw(self.screen)

    def run(self):
        clock = pygame.time.Clock()
        self.running = True

        while self.running:
            dt = clock.tick(60) / 1000.0
            self.handle_input()
            self.update(dt)
            self.draw()
            pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption(
        "Camera Demo — Smooth, Platformer, Zoom, Cutscene, Debug"
    )

    game = CameraDemo(screen)
    game.run()

    pygame.quit()


if __name__ == "__main__":
    main()
