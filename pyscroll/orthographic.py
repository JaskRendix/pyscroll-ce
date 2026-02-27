from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

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
        colorkey: tuple[int, int, int] | None = None,
        alpha: bool = False,
        time_source: Callable[[], float] = time.time,
        scaling_function: Callable[
            [Surface, tuple[int, int], Surface], None
        ] = _default_scaler,
        tall_sprites: int = 0,
        sprite_damage_height: int = 0,
        zoom: float = 1.0,
        viewport: ViewportBase | None = None,
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
        self._redraw_cutoff: int = 1

        tile_view = self.viewport.tile_view
        self._last_tile_view_size: tuple[int, int] = tile_view.size

        self.tile_renderer: TileRendererProtocol = TileRenderer(
            self.data, colorkey, alpha
        )

        self._buffer: Surface | None = None
        self._zoom_buffer: Surface | None = None

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
        return self.viewport.tile_view

    @property
    def _x_offset(self) -> int:
        return self.viewport.x_offset

    @property
    def _y_offset(self) -> int:
        return self.viewport.y_offset

    def scroll(self, vector: tuple[int, int]) -> None:
        viewport = self.viewport
        _, _, dx, dy, view_change = viewport.scroll(vector)
        self._handle_view_change(dx, dy, view_change)

    def center(self, coords: Vector2D) -> None:
        viewport = self.viewport
        _, _, dx, dy, view_change = viewport.center(coords)
        self._handle_view_change(dx, dy, view_change)

    @property
    def zoom(self) -> float:
        return self.viewport.zoom

    @zoom.setter
    def zoom(self, value: float) -> None:
        self.viewport.zoom = value
        self._initialize_buffers_from_viewport()

    def set_size(self, size: tuple[int, int]) -> None:
        self.viewport.set_size(size)
        self._initialize_buffers_from_viewport()

    def get_center_offset(self) -> tuple[int, int]:
        return self.viewport.get_center_offset()

    def translate_point(self, point: Vector2D) -> tuple[int, int]:
        return self.viewport.translate_point(point)

    def translate_rect(self, rect: RectLike) -> Rect:
        return self.viewport.translate_rect(rect)

    def translate_points(self, points: list[Vector2D]) -> list[tuple[int, int]]:
        return self.viewport.translate_points(points)

    def translate_rects(self, rects: list[Rect]) -> list[Rect]:
        return self.viewport.translate_rects(rects)

    def reload(self) -> None:
        buffer = self._buffer
        if buffer is None:
            return

        data = self.data
        data.reload_data()
        data.reload_animations()
        self.redraw_tiles(buffer)

    def draw(self, surface: Surface, rect: Rect, surfaces: list[Renderable]) -> Rect:
        viewport = self.viewport
        zoom = viewport.zoom

        if zoom == 1.0:
            self._render_map(surface, rect, surfaces)
        else:
            zoom_buffer = self._zoom_buffer
            assert zoom_buffer is not None
            self._render_map(zoom_buffer, zoom_buffer.get_rect(), surfaces)
            self.scaling_function(zoom_buffer, rect.size, surface)

        # Preserve backward compatibility: return a copy
        return self._previous_blit.copy()

    def redraw_tiles(self, surface: Surface) -> None:
        buffer = self._buffer
        if buffer is None:
            return

        log.debug("pyscroll buffer redraw")

        tile_renderer = self.tile_renderer
        viewport = self.viewport
        data = self.data

        tile_view = viewport.tile_view
        tile_queue = data.get_tile_images_by_rect(tile_view)

        tile_renderer.clear_region(buffer)
        tile_renderer.flush_tile_queue(tile_queue, tile_view, buffer)

    def _handle_view_change(self, dx: int, dy: int, view_change: int) -> None:
        buffer = self._buffer
        if buffer is None or view_change == 0:
            return

        data = self.data
        tile_renderer = self.tile_renderer
        viewport = self.viewport
        tile_view = viewport.tile_view
        tw, th = data.tile_size

        if view_change <= self._redraw_cutoff:
            # Small scroll – use buffer scroll
            buffer.scroll(-dx * tw, -dy * th)
            tile_view.move_ip(dx, dy)

            queue_edge_tiles = tile_renderer.queue_edge_tiles
            flush = tile_renderer.flush_tile_queue

            tile_queue = queue_edge_tiles(tile_view, dx, dy, buffer)
            flush(tile_queue, tile_view, buffer)
        else:
            # Large scroll – full redraw
            log.debug("scrolling too quickly. redraw forced")
            tile_view.move_ip(dx, dy)
            self.redraw_tiles(buffer)

    def _render_map(
        self, surface: Surface, rect: Rect, surfaces: list[Renderable]
    ) -> None:
        buffer = self._buffer
        if buffer is None:
            return

        data = self.data
        tile_renderer = self.tile_renderer
        viewport = self.viewport

        tile_view = viewport.tile_view

        # Process tile animations
        tile_queue = data.process_animation_queue(tile_view)
        tile_renderer.flush_tile_queue(tile_queue, tile_view, buffer)

        anchored_view = viewport.anchored_view
        if not anchored_view:
            # Clear the previous blit region on the target surface
            tile_renderer.clear_region(surface, self._previous_blit)

        # Compute offsets once
        vx = viewport.x_offset
        vy = viewport.y_offset
        rect_left = rect.left
        rect_top = rect.top

        ox = -vx + rect_left
        oy = -vy + rect_top
        offset = (ox, oy)

        with surface_clipping_context(surface, rect):
            self._previous_blit = surface.blit(buffer, offset)

            if surfaces:
                # sprites_offset is inverse of map offset
                surfaces_offset = (-ox, -oy)
                self.sprite_renderer.render_sprites(
                    surface, surfaces_offset, tile_view, surfaces
                )

    def _create_buffers(
        self, view_size: tuple[int, int], buffer_size: tuple[int, int]
    ) -> None:
        clear_color = self.tile_renderer.clear_color

        # Reset zoom buffer
        self._zoom_buffer = None

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

        if requires_zoom:
            zoom_buffer = Surface(view_size, flags=flags)
            if fill_color is not None:
                zoom_buffer.set_colorkey(fill_color)
            self._zoom_buffer = zoom_buffer

        buffer = Surface(buffer_size, flags=flags)
        if fill_color is not None:
            buffer.set_colorkey(fill_color)
            buffer.fill(fill_color)

        self._buffer = buffer

        # Convert surfaces only for alpha clear color (unchanged behavior)
        if clear_color == self._rgba_clear_color:
            self.data.convert_surfaces(buffer, True)

    def _initialize_buffers_from_viewport(self) -> None:
        viewport = self.viewport
        data = self.data

        view_rect = viewport.view_rect
        tile_view = viewport.tile_view
        tile_view_size = tile_view.size

        # Base buffer pixel size on map_rect, but override if tile_view is non-empty
        buffer_pixel_size = viewport.map_rect.size
        if tile_view_size != (0, 0):
            tw, th = data.tile_size
            buffer_pixel_size = (
                tile_view.width * tw,
                tile_view.height * th,
            )

        self._create_buffers(view_rect.size, buffer_pixel_size)

        # Only rebuild quadtree when tile_view dimensions change
        if tile_view_size != self._last_tile_view_size:
            self._last_tile_view_size = tile_view_size

            tw, th = data.tile_size
            width, height = tile_view_size

            rects = [
                Rect((x * tw, y * th), (tw, th))
                for y in range(height)
                for x in range(width)
            ]

            layer_quadtree = FastQuadTree(items=rects, depth=4)
            self.sprite_renderer: SpriteRendererProtocol = SpriteRenderer(
                data, layer_quadtree, self.tall_sprites
            )

        # Redraw tiles if buffer exists
        buffer = self._buffer
        if buffer is not None:
            self.redraw_tiles(buffer)
