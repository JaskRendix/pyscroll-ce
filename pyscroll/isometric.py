import logging
import math
from typing import TYPE_CHECKING

from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.common import Vector2D
from pyscroll.group import Renderable
from pyscroll.orthographic import BufferedRenderer

log = logging.getLogger(__file__)


def vector3_to_iso(
    vector3: tuple[int, int, int], offset: tuple[int, int] = (0, 0)
) -> tuple[int, int]:
    """
    Convert 3D cartesian coordinates to isometric coordinates.
    """
    if not isinstance(vector3, tuple) or len(vector3) != 3:
        raise ValueError("Input tuple must have exactly 3 elements")
    return (
        (vector3[0] - vector3[1]) + offset[0],
        ((vector3[0] + vector3[1]) >> 1) - vector3[2] + offset[1],
    )


def vector2_to_iso(
    vector2: tuple[int, int], offset: tuple[int, int] = (0, 0)
) -> tuple[int, int]:
    """
    Convert 2D cartesian coordinates to isometric coordinates.
    """
    if not isinstance(vector2, tuple) or len(vector2) != 2:
        raise ValueError("Input tuple must have exactly 2 elements")
    return (
        (vector2[0] - vector2[1]) + offset[0],
        ((vector2[0] + vector2[1]) >> 1) + offset[1],
    )


class IsometricBufferedRenderer(BufferedRenderer):
    """TEST ISOMETRIC

    here be dragons.  lots of odd, untested, and unoptimised stuff.

    - coalescing of surfaces is not supported
    - drawing may have depth sorting issues
    """

    def _draw_surfaces(
        self, surface: Surface, offset: tuple[int, int], surfaces: list[Renderable]
    ) -> None:

        if not surfaces:
            return

        ox, oy = offset

        blit_list = []
        order = 0

        for renderable in surfaces:
            if renderable.surface is None:
                continue

            # Convert sprite position into isometric space
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

        # Sort by depth, then by insertion order
        blit_list.sort()

        # Final blit
        for depth, order, surf, pos, blend in blit_list:
            if blend is None:
                surface.blit(surf, pos)
            else:
                surface.blit(surf, pos, special_flags=int(blend))

    def _initialize_buffers(self, view_size: tuple[int, int]) -> None:
        """
        Create the buffers to cache tile drawing.

        Args:
            view_size: size of the draw area in pixels
        """
        tw, th = self.data.tile_size
        mw, mh = self.data.map_size

        buffer_tile_width = int(math.ceil(view_size[0] / tw) + 2) * 2
        buffer_tile_height = int(math.ceil(view_size[1] / th) + 2) * 2
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th

        self.map_rect = Rect(0, 0, mw * tw, mh * th)
        self.view_rect.size = view_size
        self._tile_view = Rect(0, 0, buffer_tile_width, buffer_tile_height)
        self._redraw_cutoff = 1  # TODO: optimize this value

        self._create_buffers(view_size, buffer_pixel_size)

        assert self._buffer is not None

        self._half_width = view_size[0] // 2
        self._half_height = view_size[1] // 2
        self._x_offset = 0
        self._y_offset = 0

        self.redraw_tiles(self._buffer)

    def _flush_tile_queue(self, surface: Surface) -> None:
        """
        Blit (x, y, layer) tuples to buffer from iterator.
        """
        assert self._buffer is not None

        # animation map may not be used in all adapters
        animation_map = getattr(self, "_animation_map", None)
        map_get = animation_map.get if animation_map is not None else None

        bw, bh = self._buffer.get_size()
        bw_half = bw / 2

        tw, th = self.data.tile_size
        twh = tw // 2
        thh = th // 2

        for item in self._tile_queue:
            if len(item) == 4:
                x, y, l, tile = item
                gid = 0
            else:
                x, y, l, tile, gid = item
            if map_get is not None:
                tile = map_get(gid, tile)

            x -= self._tile_view.left
            y -= self._tile_view.top

            # cart -> iso projection
            iso_x = ((x - y) * twh) + bw_half
            iso_y = (x + y) * thh
            self._buffer.blit(tile, (iso_x, iso_y))

    def center(self, coords: Vector2D) -> None:
        """Center the map on a 'map pixel'."""
        x, y = [round(i, 0) for i in coords]
        self.view_rect.center = x, y

        tw, th = self.data.tile_size

        left, ox = divmod(x, tw)
        top, oy = divmod(y, th)

        vec = int(ox / 2), int(oy)
        iso = vector2_to_iso(vec)
        self._x_offset = iso[0]
        self._y_offset = iso[1]

        assert self._buffer is not None

        # center the buffer on the screen
        self._x_offset += (self._buffer.get_width() - self.view_rect.width) // 2
        self._y_offset += (self._buffer.get_height() - self.view_rect.height) // 4

        dx = int(left - self._tile_view.left)
        dy = int(top - self._tile_view.top)
        view_change = max(abs(dx), abs(dy))

        self._redraw_cutoff = 0  # edge queuing not supported yet

        if view_change and (view_change <= self._redraw_cutoff):
            self._buffer.scroll(-dx * tw, -dy * th)
            self._tile_view.move_ip(dx, dy)
            self._queue_edge_tiles(dx, dy)
            self._flush_tile_queue(self._buffer)
        elif view_change > self._redraw_cutoff:
            self._tile_view.move_ip(dx, dy)
            self.redraw_tiles(self._buffer)

    def redraw_tiles(self, surface: Surface) -> None:
        """
        Redraw the entire visible portion of the isometric tile buffer
        into the given surface.

        This is slower than edge-queueing but required for isometric maps,
        since partial redraws are not yet supported.
        """
        # Clear buffer if needed
        if self._clear_color is not None:
            surface.fill(self._clear_color)

        v = self._tile_view
        tw, th = self.data.tile_size

        # Precompute iso projection constants
        twh = tw // 2
        thh = th // 2

        # Prepare tile queue
        queue: list[tuple[int, int, int, Surface, int]] = []
        append = queue.append

        # Collect all tiles in tile-view space
        for x in range(v.left, v.right):
            for y in range(v.top, v.bottom):
                for layer in self.data.visible_tile_layers:
                    tile = self.data.get_tile_image(x, y, layer)
                    if tile:
                        # gid is 0 for non-animated tiles
                        append((x, y, layer, tile, 0))

        # Flush queue directly
        surface_blit = surface.blit
        animation_map = getattr(self, "_animation_map", None)
        map_get = animation_map.get if animation_map is not None else None

        for x, y, layer, tile, gid in queue:
            if map_get is not None:
                tile = map_get(gid, tile)

            # Convert tile coords to local buffer coords
            lx = x - v.left
            ly = y - v.top

            # cart -> iso projection
            iso_x = (lx - ly) * twh
            iso_y = (lx + ly) * thh

            surface_blit(tile, (iso_x, iso_y))
