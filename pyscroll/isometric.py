import logging
import time
from collections.abc import Callable
from typing import Optional

from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.common import RectLike, surface_clipping_context
from pyscroll.data import PyscrollDataAdapter
from pyscroll.group import Renderable
from pyscroll.orthographic import BufferedRenderer, _default_scaler
from pyscroll.sprite_manager import IsometricSpriteRenderer
from pyscroll.viewport import IsometricViewport

log = logging.getLogger(__file__)


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
        self.viewport = IsometricViewport(data, size, zoom, clamp_camera)

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
        self._redraw_cutoff = 0  # always full redraw for isometric

    def redraw_tiles(self, surface: Surface) -> None:
        """Redraw the entire visible portion of the isometric tile buffer."""
        if surface is None:
            return

        if self._clear_color is not None:
            surface.fill(self._clear_color)

        v = self.viewport._tile_view
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

        if self.viewport._anchored_view:
            self._clear_surface(surface, self._previous_blit)

        offset = (
            -self.viewport._x_offset + rect.left,
            -self.viewport._y_offset + rect.top,
        )

        with surface_clipping_context(surface, rect):
            self._previous_blit = surface.blit(self._buffer, offset)
            if surfaces:
                surfaces_offset = -offset[0], -offset[1]
                self.sprite_renderer.render_sprites(
                    surface,
                    surfaces_offset,
                    self.viewport._tile_view,
                    surfaces,
                )

    def _clear_surface(self, surface: Surface, area: Optional[RectLike] = None) -> None:
        """
        Clear the surface using the right clear color.
        """
        clear_color = (
            self._rgb_clear_color if self._clear_color is None else self._clear_color
        )
        surface.fill(clear_color, area)
