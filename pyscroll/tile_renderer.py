from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional, Protocol

from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.common import RectLike

if TYPE_CHECKING:
    from pyscroll.data import PyscrollDataAdapter

log = logging.getLogger(__file__)

ColorRGB = tuple[int, int, int]
ColorRGBA = tuple[int, int, int, int]


class TileRendererProtocol(Protocol):
    """
    Protocol for any object responsible for drawing map tiles onto a buffer.
    """

    def queue_edge_tiles(
        self,
        tile_view: Rect,
        dx: int,
        dy: int,
        buffer_surface: Surface,
    ) -> list[tuple[int, int, int, Surface]]: ...

    def flush_tile_queue(
        self,
        tile_queue: Iterable[tuple[int, int, int, Surface]],
        tile_view: Rect,
        buffer_surface: Surface,
    ) -> None: ...

    def redraw_all(
        self,
        tile_view: Rect,
        buffer_surface: Surface,
    ) -> None: ...
    def clear_region(
        self, surface: Surface, area: Optional[RectLike] = None
    ) -> None: ...


class TileRenderer(TileRendererProtocol):
    def __init__(
        self,
        data: PyscrollDataAdapter,
        clear_color: Optional[ColorRGB | ColorRGBA],
    ):
        """
        data: PyscrollDataAdapter
        clear_surface: function(surface, area) -> None
        """
        self.data = data
        self._clear_color = clear_color
        # Define internal defaults
        self._rgba_clear_color: ColorRGBA = (0, 0, 0, 0)
        self._rgb_clear_color: ColorRGB = (0, 0, 0)

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

            self.clear_region(buffer_surface, (px, py, pw, ph))

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

    def clear_region(self, surface: Surface, area: Optional[RectLike] = None) -> None:
        """Clear the surface using the appropriate clear color."""
        if self._clear_color is not None:
            clear_color = self._clear_color
        else:
            # Choose RGB or RGBA based on surface format
            has_alpha = surface.get_masks()[3] != 0
            clear_color = self._rgba_clear_color if has_alpha else self._rgb_clear_color

        surface.fill(clear_color, area)
