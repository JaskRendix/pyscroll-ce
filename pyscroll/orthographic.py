from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import pygame
from pygame.rect import Rect

from pyscroll.animation_pipeline import AnimationPipeline
from pyscroll.buffer_manager import BufferManager
from pyscroll.common import (
    ColorRGB,
    ColorRGBA,
    RectLike,
    Vector2D,
    surface_clipping_context,
)
from pyscroll.quadtree import FastQuadTree
from pyscroll.renderer_state import RendererState
from pyscroll.scroll_strategies import FullRedrawStrategy, SmallScrollStrategy
from pyscroll.sprite_manager import SpriteRenderer, SpriteRendererProtocol
from pyscroll.sprite_pipeline import SpritePipeline
from pyscroll.tile_renderer import TileRenderer, TileRendererProtocol
from pyscroll.viewport import ViewPort, ViewportBase

if TYPE_CHECKING:
    from collections.abc import Callable

    from pygame.surface import Surface

    from pyscroll.data import PyscrollDataAdapter
    from pyscroll.group import Renderable

log = logging.getLogger(__file__)


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

        if viewport is None:
            self.viewport: ViewportBase = ViewPort(data, size, zoom, clamp_camera)
        else:
            self.viewport = viewport

        # Renderer state (single source of truth)
        self.state = RendererState(
            buffer=None,
            zoom_buffer=None,
            tile_view=self.viewport.tile_view,
            last_tile_view_size=self.viewport.tile_view.size,
            previous_blit=Rect(0, 0, 0, 0),
            redraw_cutoff=1,
            anchored_view=self.viewport.anchored_view,
        )

        # Pipelines and buffer manager (NOT part of state)
        self._buffer_manager = BufferManager()
        self._animation_pipeline = AnimationPipeline()
        self._sprite_pipeline = SpritePipeline()

        # Core fields
        self.data = data
        self.time_source = time_source
        self.scaling_function = scaling_function
        self.tall_sprites = tall_sprites
        self.sprite_damage_height = sprite_damage_height

        self.tile_renderer = TileRenderer(self.data, colorkey, alpha)

        # Sprite renderer created lazily when quadtree rebuilds
        self.sprite_renderer: SpriteRendererProtocol | None = None

        # Initialize buffers
        self._initialize_buffers_from_viewport()

        # Scroll strategies
        self._small_scroll = SmallScrollStrategy()
        self._full_redraw = FullRedrawStrategy()

        # Pipelines ready
        self.state.mark_pipelines_ready()

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

    def _create_tile_renderer(
        self, colorkey: ColorRGB | None = None, alpha: bool = False
    ) -> TileRendererProtocol:
        return TileRenderer(self.data, colorkey, alpha)

    def _create_sprite_renderer(
        self, data: PyscrollDataAdapter, layer_quadtree: FastQuadTree
    ) -> SpriteRendererProtocol:
        return SpriteRenderer(data, layer_quadtree, self.tall_sprites)

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
        buffer = self.state.buffer
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
            zoom_buffer = self.state.zoom_buffer
            assert zoom_buffer is not None
            self._render_map(zoom_buffer, zoom_buffer.get_rect(), surfaces)
            self.scaling_function(zoom_buffer, rect.size, surface)

        # Preserve backward compatibility: return a copy
        return self.state.previous_blit.copy()

    def _expanded_tile_view(self) -> Rect:
        ox, oy = self.data.tile_overdraw
        if ox == 0 and oy == 0:
            return self.viewport.tile_view
        tv = self.viewport.tile_view
        return Rect(tv.x - ox, tv.y - oy, tv.width + ox * 2, tv.height + oy * 2)

    def redraw_tiles(self, surface: Surface) -> None:
        buffer = self.state.buffer
        if buffer is None:
            return

        log.debug("pyscroll buffer redraw")

        tile_renderer = self.tile_renderer
        viewport = self.viewport
        data = self.data

        tile_view = viewport.tile_view
        tile_queue = data.get_tile_images_by_rect(self._expanded_tile_view())

        tile_renderer.clear_region(buffer)
        tile_renderer.flush_tile_queue(tile_queue, tile_view, buffer)

    def _handle_view_change(self, dx: int, dy: int, view_change: int) -> None:
        buffer = self.state.buffer
        if buffer is None or view_change == 0:
            return

        viewport = self.viewport
        tile_view = viewport.tile_view
        tile_renderer = self.tile_renderer
        data = self.data

        if view_change <= self.state.redraw_cutoff:
            # Small scroll strategy
            self._small_scroll.apply(
                dx=dx,
                dy=dy,
                buffer=buffer,
                tile_view=tile_view,
                tile_renderer=tile_renderer,
                tile_size=data.tile_size,
            )
        else:
            # Full redraw strategy
            log.debug("scrolling too quickly. redraw forced")
            self._full_redraw.apply(
                dx=dx,
                dy=dy,
                buffer=buffer,
                tile_view=tile_view,
                redraw_tiles=self.redraw_tiles,
            )

    def _render_map(
        self, surface: Surface, rect: Rect, surfaces: list[Renderable]
    ) -> None:
        buffer = self.state.buffer
        if buffer is None:
            return

        data = self.data
        tile_renderer = self.tile_renderer
        viewport = self.viewport

        tile_view = viewport.tile_view

        # Process tile animations
        self._animation_pipeline.apply(
            data=data,
            tile_renderer=tile_renderer,
            tile_view=tile_view,
            expanded_tile_view=self._expanded_tile_view(),
            buffer=buffer,
        )

        anchored_view = viewport.anchored_view
        if not anchored_view:
            # Clear the previous blit region on the target surface
            tile_renderer.clear_region(surface, self.state.previous_blit)

        # Compute offsets once
        vx = viewport.x_offset
        vy = viewport.y_offset
        rect_left = rect.left
        rect_top = rect.top

        ox = -vx + rect_left
        oy = -vy + rect_top
        offset = (ox, oy)

        with surface_clipping_context(surface, rect):
            self.state.set_previous_blit(surface.blit(buffer, offset))

            if surfaces:
                assert self.sprite_renderer is not None
                surfaces_offset = (-ox, -oy)
                self._sprite_pipeline.apply(
                    sprite_renderer=self.sprite_renderer,
                    surface=surface,
                    offset=surfaces_offset,
                    tile_view=tile_view,
                    sprites=surfaces,
                )

    def _initialize_buffers_from_viewport(self) -> None:
        viewport = self.viewport
        data = self.data
        bm = self._buffer_manager

        view_rect = viewport.view_rect
        tile_view = viewport.tile_view
        tile_view_size = tile_view.size

        buffer_pixel_size = bm.compute_buffer_pixel_size(
            viewport_view_rect=view_rect,
            tile_view=tile_view,
            tile_size=data.tile_size,
            map_rect=viewport.map_rect,
        )

        buffer, zoom_buffer = bm.create_buffers(
            view_size=view_rect.size,
            buffer_size=buffer_pixel_size,
            clear_color=self.tile_renderer.clear_color,
            data=data,
        )

        assert buffer is not None
        self.state.set_buffers(buffer, zoom_buffer)

        # Rebuild quadtree only when tile_view dimensions change
        if self.state.update_tile_view(tile_view):
            self.sprite_renderer = bm.rebuild_quadtree(
                tile_view_size=tile_view_size,
                tile_size=data.tile_size,
                FastQuadTree=FastQuadTree,
                data=data,
                tall_sprites=self.tall_sprites,
                SpriteRenderer=SpriteRenderer,
            )

        # Redraw tiles if buffer exists
        if buffer is not None:
            self.redraw_tiles(buffer)
