from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from pygame.rect import Rect
    from pygame.surface import Surface

    from pyscroll.tile_renderer import TileRendererProtocol


log = logging.getLogger(__file__)


class SmallScrollStrategy:
    """
    Handles small scrolls by shifting the existing buffer and drawing only
    the newly exposed edge tiles.
    """

    def apply(
        self,
        dx: int,
        dy: int,
        buffer: Surface,
        tile_view: Rect,
        tile_renderer: TileRendererProtocol,
        tile_size: tuple[int, int],
    ) -> None:
        tw, th = tile_size

        # Shift the buffer by whole-tile increments
        buffer.scroll(-dx * tw, -dy * th)
        tile_view.move_ip(dx, dy)

        # Queue and flush only the edge tiles
        queue_edge_tiles = tile_renderer.queue_edge_tiles
        flush = tile_renderer.flush_tile_queue

        tile_queue = queue_edge_tiles(tile_view, dx, dy, buffer)
        flush(tile_queue, tile_view, buffer)


class FullRedrawStrategy:
    """
    Handles large scrolls by moving the tile view and redrawing the entire buffer.
    """

    def apply(
        self,
        dx: int,
        dy: int,
        buffer: Surface,
        tile_view: Rect,
        redraw_tiles: Callable[[Surface], None],
    ) -> None:
        tile_view.move_ip(dx, dy)
        redraw_tiles(buffer)
