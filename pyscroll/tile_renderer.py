from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Optional

from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.common import RectLike
from pyscroll.quadtree import FastQuadTree

if TYPE_CHECKING:
    from pyscroll.data import PyscrollDataAdapter
    from pyscroll.group import Renderable

log = logging.getLogger(__file__)


Blit2 = tuple[Surface, tuple[int | float, int | float]]


class TileRenderer:
    def __init__(
        self,
        data: PyscrollDataAdapter,
        clear_surface: Callable[[Surface, Optional[RectLike]], None],
    ):
        """
        data: PyscrollDataAdapter
        clear_surface: function(surface, area) -> None
        """
        self.data = data
        self.clear_surface = clear_surface

    def queue_edge_tiles(
        self, tile_view: Rect, dx: int, dy: int, buffer_surface: Surface
    ) -> list[tuple[int, int, int, Surface]]:
        """
        Returns a list of (x, y, layer, image) tuples.
        Also clears the buffer regions where new tiles will be drawn.
        """
        tw, th = self.data.tile_size
        v = tile_view
        queue: list[tuple[int, int, int, Surface]] = []

        def append(rect: RectLike) -> None:
            # rect = (x, y, w, h) in tile coords
            queue.extend(self.data.get_tile_images_by_rect(rect))

            if buffer_surface is None:
                return

            # Convert tile rect → pixel rect
            px = (rect[0] - v.left) * tw
            py = (rect[1] - v.top) * th
            pw = rect[2] * tw
            ph = rect[3] * th

            self.clear_surface(buffer_surface, (px, py, pw, ph))

        # Horizontal movement
        if dx > 0:
            append((v.right - 1, v.top, dx, v.height))
        elif dx < 0:
            append((v.left, v.top, -dx, v.height))

        # Vertical movement
        if dy > 0:
            append((v.left, v.bottom - 1, v.width, dy))
        elif dy < 0:
            append((v.left, v.top, v.width, -dy))

        return queue

    def flush_tile_queue(
        self,
        tile_queue: Iterable[tuple[int, int, int, Surface]],
        tile_view: Rect,
        buffer_surface: Surface,
    ) -> None:
        """
        Draws all tiles in the queue onto the buffer surface.
        """
        tw, th = self.data.tile_size
        ltw = tile_view.left * tw
        tth = tile_view.top * th

        self.data.prepare_tiles(tile_view)

        buffer_surface.blits(
            (
                (image, (x * tw - ltw, y * th - tth))
                for x, y, layer, image in tile_queue
            ),
            doreturn=False,
        )

    def redraw_all(self, tile_view: Rect, buffer_surface: Surface) -> None:
        """
        Full redraw of all tiles in the tile_view.
        """
        tile_queue = self.data.get_tile_images_by_rect(tile_view)
        self.flush_tile_queue(tile_queue, tile_view, buffer_surface)


from typing import Protocol


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
