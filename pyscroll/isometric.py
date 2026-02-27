import logging
import time
from collections.abc import Callable

from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.common import surface_clipping_context
from pyscroll.data import PyscrollDataAdapter
from pyscroll.group import Renderable
from pyscroll.orthographic import BufferedRenderer, _default_scaler
from pyscroll.sprite_manager import IsometricSpriteRenderer
from pyscroll.tile_renderer import IsometricTileRenderer
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
        colorkey: tuple[int, int, int] | None = None,
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

        self.tile_renderer = IsometricTileRenderer(data, colorkey, alpha)
        self.sprite_renderer = IsometricSpriteRenderer()

        self._last_offset: tuple[int, int] | None = None
        self._redraw_cutoff: int = 0

    def redraw_tiles(self, surface: Surface) -> None:
        """Redraw the entire visible portion of the isometric tile buffer."""
        tile_view = self.viewport.tile_view
        self.tile_renderer.redraw_all(tile_view, surface)

    def _render_map(
        self, surface: Surface, rect: Rect, surfaces: list[Renderable]
    ) -> None:
        """Render isometric tiles + sprites to the target surface."""
        if self._buffer is None:
            return

        viewport = self.viewport
        tile_renderer = self.tile_renderer
        sprite_renderer = self.sprite_renderer
        tile_view = viewport.tile_view

        # Compute offsets once
        vx = viewport.x_offset
        vy = viewport.y_offset
        ox = -vx + rect.left
        oy = -vy + rect.top
        offset = (ox, oy)

        # Only clear region if offset changed
        if viewport.anchored_view:
            current_offset = (vx, vy)
            if current_offset != self._last_offset:
                if self._previous_blit:
                    tile_renderer.clear_region(surface, self._previous_blit)
                self._last_offset = current_offset

        # Blit buffer BEFORE clipping context (faster)
        self._previous_blit = surface.blit(self._buffer, offset)

        # Clip only for sprite rendering
        if not surfaces:
            return

        # Skip sprite rendering if none intersect viewport
        if not any(s.rect.colliderect(rect) for s in surfaces):
            return

        surfaces_offset = (-ox, -oy)

        with surface_clipping_context(surface, rect):
            sprite_renderer.render_sprites(
                surface,
                surfaces_offset,
                tile_view,
                surfaces,
            )
