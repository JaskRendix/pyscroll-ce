import logging
import math
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.common import Vector2D, surface_clipping_context
from pyscroll.data import PyscrollDataAdapter
from pyscroll.group import Renderable
from pyscroll.orthographic import BufferedRenderer, _default_scaler
from pyscroll.sprite_manager import IsometricSpriteRenderer

if TYPE_CHECKING:

    from pyscroll.quadtree import FastQuadTree

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
    """Isometric map renderer using the BufferedRenderer architecture.

    - No edge-queueing: always full tile redraw
    - Custom isometric tile projection
    - Custom isometric sprite depth sorting
    """

    def __init__(
        self,
        data: PyscrollDataAdapter,
        size: tuple[int, int],
        clamp_camera: bool = True,
        colorkey: Optional[tuple[int, int, int]] = None,
        alpha: bool = False,
        time_source: Callable[[], float] = time.time,
        scaling_function: Callable[
            [Surface, tuple[int, int], Surface], None
        ] = _default_scaler,
        tall_sprites: int = 0,
        sprite_damage_height: int = 0,
        zoom: float = 1.0,
    ) -> None:
        super().__init__(
            data=data,
            size=size,
            clamp_camera=clamp_camera,
            colorkey=colorkey,
            alpha=alpha,
            time_source=time_source,
            scaling_function=scaling_function,
            tall_sprites=tall_sprites,
            sprite_damage_height=sprite_damage_height,
            zoom=zoom,
        )
        self.sprite_renderer = IsometricSpriteRenderer()

    def _initialize_buffers(self, view_size: tuple[int, int]) -> None:
        """Create the buffers to cache tile drawing for isometric maps."""
        tw, th = self.data.tile_size
        mw, mh = self.data.map_size

        buffer_tile_width = int(math.ceil(view_size[0] / tw) + 2) * 2
        buffer_tile_height = int(math.ceil(view_size[1] / th) + 2) * 2
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th

        self.map_rect = Rect(0, 0, mw * tw, mh * th)
        self.view_rect.size = view_size
        self._previous_blit = Rect(self.view_rect)

        self._tile_view = Rect(0, 0, buffer_tile_width, buffer_tile_height)
        self._redraw_cutoff = 0

        self._create_buffers(view_size, buffer_pixel_size)

        assert self._buffer is not None

        self._half_width = view_size[0] // 2
        self._half_height = view_size[1] // 2
        self._x_offset = 0
        self._y_offset = 0
        self._layer_quadtree: Optional[FastQuadTree] = None
        self.redraw_tiles(self._buffer)

    def center(self, coords: Vector2D) -> None:
        """Center the map on a 'map pixel' in isometric space."""
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

        self._x_offset += (self._buffer.get_width() - self.view_rect.width) // 2
        self._y_offset += (self._buffer.get_height() - self.view_rect.height) // 4

        dx = int(left - self._tile_view.left)
        dy = int(top - self._tile_view.top)
        view_change = max(abs(dx), abs(dy))

        if view_change:
            self._tile_view.move_ip(dx, dy)
            self.redraw_tiles(self._buffer)

    def redraw_tiles(self, surface: Surface) -> None:
        """Redraw the entire visible portion of the isometric tile buffer."""
        if surface is None:
            return

        if self._clear_color is not None:
            surface.fill(self._clear_color)

        v = self._tile_view
        tw, th = self.data.tile_size

        twh = tw // 2
        thh = th // 2

        animation_map = getattr(self, "_animation_map", None)
        map_get = animation_map.get if animation_map is not None else None

        surface_blit = surface.blit

        for x in range(v.left, v.right):
            for y in range(v.top, v.bottom):
                for layer in self.data.visible_tile_layers:
                    tile = self.data.get_tile_image(x, y, layer)
                    if not tile:
                        continue

                    gid = 0
                    if map_get is not None:
                        tile = map_get(gid, tile)

                    lx = x - v.left
                    ly = y - v.top

                    iso_x = (lx - ly) * twh
                    iso_y = (lx + ly) * thh

                    surface_blit(tile, (iso_x, iso_y))

    def _render_map(
        self, surface: Surface, rect: Rect, surfaces: list[Renderable]
    ) -> None:
        """Render isometric tiles + sprites to the target surface."""
        if self._buffer is None:
            return

        if not self._anchored_view:
            self._clear_surface(surface, self._previous_blit)

        offset = -self._x_offset + rect.left, -self._y_offset + rect.top

        with surface_clipping_context(surface, rect):
            self._previous_blit = surface.blit(self._buffer, offset)
            if surfaces:
                surfaces_offset = -offset[0], -offset[1]
                self.sprite_renderer.render_sprites(
                    surface,
                    surfaces_offset,
                    self._tile_view,
                    surfaces,
                )
