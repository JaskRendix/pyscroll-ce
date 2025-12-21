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
from pyscroll.tile_renderer import IsometricTileRenderer, TileRendererProtocol
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

        viewport = IsometricViewport(data, size, zoom, clamp_camera)

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
            viewport=viewport,
        )
        self.tile_renderer = IsometricTileRenderer(data, self._clear_color)
        self.sprite_renderer = IsometricSpriteRenderer()
        self._redraw_cutoff = 0

    def redraw_tiles(self, surface: Surface) -> None:
        """Redraw the entire visible portion of the isometric tile buffer."""
        self.tile_renderer.redraw_all(self.viewport.tile_view, surface)

    def _render_map(
        self, surface: Surface, rect: Rect, surfaces: list[Renderable]
    ) -> None:
        """Render isometric tiles + sprites to the target surface."""
        if self._buffer is None:
            return

        if self.viewport.anchored_view:
            self.tile_renderer.clear_region(surface, self._previous_blit)

        offset = (
            -self.viewport.x_offset + rect.left,
            -self.viewport.y_offset + rect.top,
        )

        with surface_clipping_context(surface, rect):
            self._previous_blit = surface.blit(self._buffer, offset)
            if surfaces:
                surfaces_offset = -offset[0], -offset[1]
                self.sprite_renderer.render_sprites(
                    surface,
                    surfaces_offset,
                    self.viewport.tile_view,
                    surfaces,
                )
