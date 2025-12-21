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
        self.data = data
        self._clear_color = clear_color
        self._rgba_clear_color: ColorRGBA = (0, 0, 0, 0)
        self._rgb_clear_color: ColorRGB = (0, 0, 0)

    def queue_edge_tiles(
        self, tile_view: Rect, dx: int, dy: int, buffer_surface: Surface
    ) -> list[tuple[int, int, int, Surface]]:
        # Early exit: no movement
        if dx == 0 and dy == 0:
            return []

        tw, th = self.data.tile_size
        v_left = tile_view.left
        v_top = tile_view.top
        v_right = tile_view.right
        v_bottom = tile_view.bottom
        v_width = tile_view.width
        v_height = tile_view.height

        get_images = self.data.get_tile_images_by_rect
        clear_region = self.clear_region

        queue: list[tuple[int, int, int, Surface]] = []

        # Horizontal movement
        if dx > 0:
            rect = (v_right - 1, v_top, dx, v_height)
            queue.extend(get_images(rect))
            if buffer_surface is not None:
                px = (rect[0] - v_left) * tw
                py = 0
                pw = rect[2] * tw
                ph = v_height * th
                clear_region(buffer_surface, (px, py, pw, ph))

        elif dx < 0:
            rect = (v_left, v_top, -dx, v_height)
            queue.extend(get_images(rect))
            if buffer_surface is not None:
                px = 0
                py = 0
                pw = rect[2] * tw
                ph = v_height * th
                clear_region(buffer_surface, (px, py, pw, ph))

        # Vertical movement
        if dy > 0:
            rect = (v_left, v_bottom - 1, v_width, dy)
            queue.extend(get_images(rect))
            if buffer_surface is not None:
                px = 0
                py = (rect[1] - v_top) * th
                pw = v_width * tw
                ph = rect[3] * th
                clear_region(buffer_surface, (px, py, pw, ph))

        elif dy < 0:
            rect = (v_left, v_top, v_width, -dy)
            queue.extend(get_images(rect))
            if buffer_surface is not None:
                px = 0
                py = 0
                pw = v_width * tw
                ph = rect[3] * th
                clear_region(buffer_surface, (px, py, pw, ph))

        return queue

    def flush_tile_queue(
        self,
        tile_queue: Iterable[tuple[int, int, int, Surface]],
        tile_view: Rect,
        buffer_surface: Surface,
    ) -> None:
        tw, th = self.data.tile_size
        ltw = tile_view.left * tw
        tth = tile_view.top * th

        self.data.prepare_tiles(tile_view)

        # Precompute generator outside the C call
        blit_items = (
            (image, (x * tw - ltw, y * th - tth)) for x, y, layer, image in tile_queue
        )

        buffer_surface.blits(blit_items, doreturn=False)

    def redraw_all(self, tile_view: Rect, buffer_surface: Surface) -> None:
        tile_queue = self.data.get_tile_images_by_rect(tile_view)
        self.flush_tile_queue(tile_queue, tile_view, buffer_surface)

    def clear_region(self, surface: Surface, area: Optional[RectLike] = None) -> None:
        if self._clear_color is not None:
            clear_color = self._clear_color
        else:
            has_alpha = surface.get_masks()[3] != 0
            clear_color = self._rgba_clear_color if has_alpha else self._rgb_clear_color

        surface.fill(clear_color, area)
