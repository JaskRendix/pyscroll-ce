from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from pygame.surface import Surface

if TYPE_CHECKING:
    from pygame.rect import Rect

    from pyscroll.data import PyscrollDataAdapter
    from pyscroll.quadtree import FastQuadTree
    from pyscroll.sprite_manager import SpriteRenderer


class BufferManager:
    """
    Handles creation and initialization of the renderer's internal buffers.
    This includes:
    - computing buffer pixel sizes
    - creating main and zoom buffers
    - applying colorkey or alpha flags
    - converting surfaces when needed
    - rebuilding the sprite quadtree when tile_view size changes
    """

    _rgba_clear_color = (0, 0, 0, 0)

    def compute_buffer_pixel_size(
        self,
        viewport_view_rect: Rect,
        tile_view: Rect,
        tile_size: tuple[int, int],
        map_rect: Rect,
    ) -> tuple[int, int]:
        # Base buffer size on map_rect, override if tile_view is non-empty
        if tile_view.size != (0, 0):
            tw, th = tile_size
            return (tile_view.width * tw, tile_view.height * th)
        return map_rect.size

    def create_buffers(
        self,
        view_size: tuple[int, int],
        buffer_size: tuple[int, int],
        clear_color: tuple[int, int, int] | tuple[int, int, int, int] | None,
        data: PyscrollDataAdapter,
    ) -> tuple[Surface | None, Surface | None]:
        # Determine flags and fill behavior
        if clear_color is None:
            flags = 0
            fill_color = None
        elif clear_color == self._rgba_clear_color:
            flags = pygame.SRCALPHA
            fill_color = None
        else:
            flags = pygame.RLEACCEL
            fill_color = clear_color

        requires_zoom = view_size != buffer_size

        zoom_buffer: Surface | None = None
        if requires_zoom:
            zoom_buffer = Surface(view_size, flags=flags)
            if fill_color is not None:
                zoom_buffer.set_colorkey(fill_color)

        buffer = Surface(buffer_size, flags=flags)
        if fill_color is not None:
            buffer.set_colorkey(fill_color)
            buffer.fill(fill_color)

        # Convert surfaces only for alpha clear color (unchanged behavior)
        if clear_color == self._rgba_clear_color:
            data.convert_surfaces(buffer, True)

        return buffer, zoom_buffer

    def rebuild_quadtree(
        self,
        tile_view_size: tuple[int, int],
        tile_size: tuple[int, int],
        FastQuadTree: type[FastQuadTree],
        data: PyscrollDataAdapter,
        tall_sprites: int,
        SpriteRenderer: type[SpriteRenderer],
    ) -> SpriteRenderer:
        tw, th = tile_size
        width, height = tile_view_size

        rects = [
            pygame.Rect((x * tw, y * th), (tw, th))
            for y in range(height)
            for x in range(width)
        ]

        layer_quadtree = FastQuadTree(items=rects, depth=4)
        return SpriteRenderer(data, layer_quadtree, tall_sprites)
