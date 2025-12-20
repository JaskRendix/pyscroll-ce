from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Protocol

from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.quadtree import FastQuadTree

if TYPE_CHECKING:
    from pyscroll.data import PyscrollDataAdapter
    from pyscroll.group import Renderable

log = logging.getLogger(__file__)


Blit2 = tuple[Surface, tuple[int | float, int | float]]


class SpriteRendererProtocol(Protocol):
    def render_sprites(
        self,
        surface: Surface,
        offset: tuple[int, int],
        tile_view: Rect,
        surfaces: list[Renderable],
    ) -> None: ...


class SpriteRenderer(SpriteRendererProtocol):
    def __init__(
        self,
        data: PyscrollDataAdapter,
        layer_quadtree: FastQuadTree,
        tall_sprites: int = 0,
    ):
        """
        data: PyscrollDataAdapter
        layer_quadtree: FastQuadTree for tile hit detection
        tall_sprites: height of tall sprite damage region
        """
        self.data = data
        self.layer_quadtree = layer_quadtree
        self.tall_sprites = tall_sprites

    def render_sprites(
        self,
        surface: Surface,
        offset: tuple[int, int],
        tile_view: Rect,
        surfaces: list[Renderable],
    ) -> None:
        """
        surfaces: list[Renderable]
        offset: (ox, oy) pixel offset for drawing
        """
        ox, oy = offset
        left, top = tile_view.topleft
        tile_layers = tuple(sorted(self.data.visible_tile_layers))
        top_layer = tile_layers[-1]

        blit_list = []
        sprite_damage = set()
        order = 0

        for renderable in surfaces:
            # Damage rect for tile redraw
            if renderable.layer <= top_layer:
                damage_rect = Rect(renderable.rect)
                damage_rect.move_ip(ox, oy)

                if self.tall_sprites:
                    damage_rect = Rect(
                        damage_rect.x,
                        damage_rect.y + (damage_rect.height - self.tall_sprites),
                        damage_rect.width,
                        self.tall_sprites,
                    )

                if self.layer_quadtree is not None:
                    for hit_rect in self.layer_quadtree.hit(damage_rect):
                        sprite_damage.add((renderable.layer, hit_rect))

            # Add sprite to blit list
            x, y, w, h = renderable.rect
            blit_list.append(
                (
                    renderable.layer,
                    1,  # priority: sprites after tiles
                    x,
                    y,
                    order,
                    renderable.surface,
                    renderable.blendmode,
                )
            )
            order += 1

        column = []
        for dl, d_rect in sprite_damage:
            x, y, w, h = d_rect
            tx = x // w + left
            ty = y // h + top
            is_over = False

            for layer in tile_layers:
                tile = self.data.get_tile_image(tx, ty, layer)
                if tile:
                    sx = x - ox
                    sy = y - oy
                    if dl <= layer:
                        is_over = True
                    column.append((layer, 0, sx, sy, order, tile, None))
                    order += 1

            if is_over:
                blit_list.extend(column)
            column.clear()

        blit_list.sort()

        normal_blits: list[Blit2] = []

        for layer, priority, x, y, order, surf, blend in blit_list:
            if surf is None:
                continue

            if blend is None:
                # safe for blits()
                normal_blits.append((surf, (x, y)))
            else:
                # must use individual blit() for blend flags
                surface.blit(surf, (x, y), special_flags=int(blend))

        if normal_blits:
            surface.blits(normal_blits, doreturn=False)


class IsometricSpriteRenderer(SpriteRendererProtocol):
    """Isometric sprite renderer with simple depth sorting."""

    def render_sprites(
        self,
        surface: Surface,
        offset: tuple[int, int],
        tile_view: Rect,
        surfaces: list[Renderable],
    ) -> None:
        if not surfaces:
            return

        ox, oy = offset

        blit_list: list[tuple[int, int, Surface, tuple[int, int], Optional[int]]] = []
        order = 0

        for renderable in surfaces:
            if renderable.surface is None:
                continue

            rx, ry, rw, rh = renderable.rect
            sx = int(rx) - ox
            sy = int(ry) - oy

            depth = sy
            position = (sx, sy)

            blit_list.append(
                (
                    depth,
                    order,
                    renderable.surface,
                    position,
                    renderable.blendmode,
                )
            )
            order += 1

        blit_list.sort()

        for depth, order, surf, pos, blend in blit_list:
            if blend is None:
                surface.blit(surf, pos)
            else:
                surface.blit(surf, pos, special_flags=int(blend))
