from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

import pygame
from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.common import RectLike, Vector2D, surface_clipping_context
from pyscroll.quadtree import FastQuadTree
from pyscroll.sprite_manager import SpriteRenderer, SpriteRendererProtocol
from pyscroll.tile_renderer import TileRenderer, TileRendererProtocol
from pyscroll.viewport import ViewPort, ViewportBase

if TYPE_CHECKING:
    from pyscroll.data import PyscrollDataAdapter
    from pyscroll.group import Renderable

log = logging.getLogger(__file__)


ColorRGB = tuple[int, int, int]
ColorRGBA = tuple[int, int, int, int]


def _default_scaler(src: Surface, size: tuple[int, int], dest: Surface) -> None:
    scaled = pygame.transform.scale(src, size)
    dest.blit(scaled, (0, 0))


class BufferedRenderer:
    """
    Buffered tilemap renderer with support for scrolling, zooming,
    animated tiles, and sprite layering.

    The renderer maintains an off-screen buffer of the visible map region
    and delegates all camera and coordinate calculations to a
    `ViewportBase` implementation. Tile images, animation data, and map
    metadata are provided by a `PyscrollDataAdapter`.

    This renderer is projection-agnostic: orthographic, isometric, or
    custom projections can be implemented by supplying an appropriate
    viewport and sprite renderer.
    """

    _rgba_clear_color: ColorRGBA = (0, 0, 0, 0)
    _rgb_clear_color: ColorRGB = (0, 0, 0)

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
        viewport: Optional[ViewportBase] = None,
    ) -> None:
        """
        Create a buffered tilemap renderer.

        This renderer maintains an off-screen buffer of the visible map region
        and supports scrolling, zooming, animated tiles, and sprite rendering.
        All camera and coordinate calculations are delegated to a `ViewportBase`
        implementation.

        Parameters
        ----------
        data:
            Tile and map data provider.
        size:
            Displayed viewport size in pixels.
        clamp_camera:
            Restrict camera movement to map bounds.
        colorkey:
            Optional RGB transparency key for the buffer.
        alpha:
            Use an RGBA buffer instead of colorkey transparency.
        time_source:
            Time function used for animation updates.
        scaling_function:
            Function used to scale the buffer when zoom != 1.0.
        tall_sprites:
            Deprecated; kept for compatibility.
        sprite_damage_height:
            Adjusts layering for tall sprites.
        zoom:
            Initial zoom level.
        viewport:
            Optional custom viewport. If omitted, a standard orthographic
            `ViewPort` is created.

        Notes
        -----
        The renderer creates one or two internal buffers depending on zoom.
        """
        self.data = data
        self.time_source = time_source
        self.scaling_function = scaling_function
        self.tall_sprites = tall_sprites
        self.sprite_damage_height = sprite_damage_height

        self.viewport: ViewportBase
        if viewport is None:
            self.viewport = ViewPort(data, size, zoom, clamp_camera)
        else:
            self.viewport = viewport

        self._previous_blit = Rect(0, 0, 0, 0)
        self._redraw_cutoff: int = 1  # Keep this simple for now

        # Handle color/alpha options
        self._clear_color: Optional[ColorRGB | ColorRGBA]
        if colorkey and alpha:
            log.error("cannot select both colorkey and alpha")
            raise ValueError
        elif colorkey:
            self._clear_color = colorkey
        elif alpha:
            self._clear_color = self._rgba_clear_color
        else:
            self._clear_color = None

        self.tile_renderer: TileRendererProtocol = TileRenderer(
            self.data, self._clear_color
        )

        self._buffer: Optional[Surface] = None
        self._zoom_buffer: Optional[Surface] = None

        self._initialize_buffers_from_viewport()

        if self.tall_sprites != 0:
            log.warning("using tall_sprites feature is not supported")

    @property
    def view_rect(self) -> Rect:
        return self.viewport.view_rect

    @property
    def map_rect(self) -> Rect:
        return self.viewport.map_rect

    @property
    def _tile_view(self) -> Rect:
        return self.viewport._tile_view

    @property
    def _x_offset(self) -> int:
        return self.viewport._x_offset

    @property
    def _y_offset(self) -> int:
        return self.viewport._y_offset

    def scroll(self, vector: tuple[int, int]) -> None:
        """Delegate to viewport, then update surfaces if needed."""
        _, _, dx, dy, view_change = self.viewport.scroll(vector)
        self._handle_view_change(dx, dy, view_change)

    def center(self, coords: Vector2D) -> None:
        """Delegate to viewport, then update surfaces if needed."""
        _, _, dx, dy, view_change = self.viewport.center(coords)
        self._handle_view_change(dx, dy, view_change)

    @property
    def zoom(self) -> float:
        """Delegate to viewport."""
        return self.viewport.zoom

    @zoom.setter
    def zoom(self, value: float) -> None:
        """Delegate to viewport and re-initialize all buffers."""
        self.viewport.zoom = value
        self._initialize_buffers_from_viewport()

    def set_size(self, size: tuple[int, int]) -> None:
        """Delegate to viewport and re-initialize all buffers."""
        self.viewport.set_size(size)
        self._initialize_buffers_from_viewport()

    def get_center_offset(self) -> tuple[int, int]:
        """Delegate to viewport."""
        return self.viewport.get_center_offset()

    def translate_point(self, point: Vector2D) -> tuple[int, int]:
        """Delegate to viewport."""
        return self.viewport.translate_point(point)

    def translate_rect(self, rect: RectLike) -> Rect:
        """Delegate to viewport."""
        return self.viewport.translate_rect(rect)

    def translate_points(self, points: list[Vector2D]) -> list[tuple[int, int]]:
        """Delegate to viewport."""
        return self.viewport.translate_points(points)

    def translate_rects(self, rects: list[Rect]) -> list[Rect]:
        """Delegate to viewport."""
        return self.viewport.translate_rects(rects)

    def reload(self) -> None:
        """Reload tiles and animations for the data source."""
        if self._buffer is None:
            return
        self.data.reload_data()
        self.data.reload_animations()
        self.redraw_tiles(self._buffer)

    def draw(self, surface: Surface, rect: Rect, surfaces: list[Renderable]) -> Rect:
        """Draw map and sprites onto the destination surface."""
        if self.viewport.zoom == 1.0:
            self._render_map(surface, rect, surfaces)
        else:
            assert self._zoom_buffer
            self._render_map(self._zoom_buffer, self._zoom_buffer.get_rect(), surfaces)
            self.scaling_function(self._zoom_buffer, rect.size, surface)
        return self._previous_blit.copy()

    def redraw_tiles(self, surface: Surface) -> None:
        """Redraw the visible portion of the buffer."""
        if self._buffer is None:
            return
        log.debug("pyscroll buffer redraw")
        self.tile_renderer.clear_region(self._buffer)
        tile_queue = self.data.get_tile_images_by_rect(self.viewport._tile_view)
        self.tile_renderer.flush_tile_queue(
            tile_queue, self.viewport._tile_view, self._buffer
        )

    def _handle_view_change(self, dx: int, dy: int, view_change: int) -> None:
        """Internal logic to update the buffer when the ViewPort moves."""
        if self._buffer is None or view_change == 0:
            return

        tw, th = self.data.tile_size

        if view_change <= self._redraw_cutoff:
            # Scroll the buffer surface
            self._buffer.scroll(-dx * tw, -dy * th)
            self.viewport._tile_view.move_ip(dx, dy)
            tile_queue = self.tile_renderer.queue_edge_tiles(
                self.viewport._tile_view, dx, dy, self._buffer
            )
            self.tile_renderer.flush_tile_queue(
                tile_queue, self.viewport._tile_view, self._buffer
            )
        else:
            # Redraw the entire buffer
            log.debug("scrolling too quickly. redraw forced")
            self.viewport._tile_view.move_ip(dx, dy)
            self.redraw_tiles(self._buffer)

    def _render_map(
        self, surface: Surface, rect: Rect, surfaces: list[Renderable]
    ) -> None:
        """Render the tilemap and interleave sprites."""
        if self._buffer is None:
            return

        tile_queue = self.data.process_animation_queue(self.viewport._tile_view)
        self.tile_renderer.flush_tile_queue(
            tile_queue, self.viewport._tile_view, self._buffer
        )

        # Clear space outside the map area if view is unanchored
        if not self.viewport._anchored_view:
            self.tile_renderer.clear_region(surface, self._previous_blit)

        offset = (
            -self.viewport._x_offset + rect.left,
            -self.viewport._y_offset + rect.top,
        )

        with surface_clipping_context(surface, rect):
            self._previous_blit = surface.blit(self._buffer, offset)
            if surfaces:
                surfaces_offset = -offset[0], -offset[1]
                self.sprite_renderer.render_sprites(
                    surface, surfaces_offset, self.viewport._tile_view, surfaces
                )

    def _create_buffers(
        self, view_size: tuple[int, int], buffer_size: tuple[int, int]
    ) -> None:
        """Create the Pygame Surface buffers based on viewport size."""
        requires_zoom = view_size != buffer_size
        self._zoom_buffer = None

        if self._clear_color is None:
            flags = 0
            fill_color = None
        elif self._clear_color == self._rgba_clear_color:
            flags = pygame.SRCALPHA
            fill_color = None
        else:
            flags = pygame.RLEACCEL
            fill_color = self._clear_color

        if requires_zoom:
            self._zoom_buffer = Surface(view_size, flags=flags)
            if fill_color is not None:
                self._zoom_buffer.set_colorkey(fill_color)

        self._buffer = Surface(buffer_size, flags=flags)
        if fill_color is not None:
            self._buffer.set_colorkey(fill_color)
            self._buffer.fill(fill_color)

        if self._clear_color == self._rgba_clear_color:
            self.data.convert_surfaces(self._buffer, True)

    def _initialize_buffers_from_viewport(self) -> None:
        """
        Setup the surfaces and supporting structures based on ViewPort state.
        This runs after init, set_size, or zoom change.
        """
        buffer_pixel_size = self.viewport.map_rect.size
        if self.viewport._tile_view.size != (0, 0):
            buffer_pixel_size = (
                self.viewport._tile_view.width * self.data.tile_size[0],
                self.viewport._tile_view.height * self.data.tile_size[1],
            )

        self._create_buffers(self.viewport.view_rect.size, buffer_pixel_size)

        tw, th = self.data.tile_size
        rects = [
            Rect((x * tw, y * th), (tw, th))
            for y in range(self.viewport._tile_view.height)
            for x in range(self.viewport._tile_view.width)
        ]

        layer_quadtree = FastQuadTree(items=rects, depth=4)
        self.sprite_renderer: SpriteRendererProtocol = SpriteRenderer(
            self.data, layer_quadtree, self.tall_sprites
        )

        if self._buffer:
            self.redraw_tiles(self._buffer)
