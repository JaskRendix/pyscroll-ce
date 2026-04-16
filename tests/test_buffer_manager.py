from __future__ import annotations

from unittest.mock import Mock

import pygame

from pyscroll.buffer_manager import BufferManager


class DummyRect:
    def __init__(self, size):
        self.size = size
        self.width, self.height = size


def test_compute_buffer_pixel_size_uses_tile_view_when_non_empty():
    bm = BufferManager()

    viewport_view_rect = DummyRect((800, 600))
    tile_view = DummyRect((10, 5))
    tile_size = (32, 16)
    map_rect = DummyRect((9999, 9999))  # ignored

    result = bm.compute_buffer_pixel_size(
        viewport_view_rect,
        tile_view,
        tile_size,
        map_rect,
    )

    assert result == (10 * 32, 5 * 16)


def test_compute_buffer_pixel_size_falls_back_to_map_rect_when_empty():
    bm = BufferManager()

    viewport_view_rect = DummyRect((800, 600))
    tile_view = DummyRect((0, 0))
    tile_size = (32, 32)
    map_rect = DummyRect((1234, 5678))

    result = bm.compute_buffer_pixel_size(
        viewport_view_rect,
        tile_view,
        tile_size,
        map_rect,
    )

    assert result == (1234, 5678)


def test_create_buffers_no_clear_color_no_zoom(monkeypatch):
    bm = BufferManager()

    data = Mock()
    data.convert_surfaces = Mock()

    view_size = (400, 300)
    buffer_size = (400, 300)

    buffer, zoom_buffer = bm.create_buffers(
        view_size=view_size,
        buffer_size=buffer_size,
        clear_color=None,
        data=data,
    )

    assert isinstance(buffer, pygame.Surface)
    assert zoom_buffer is None
    data.convert_surfaces.assert_not_called()


def test_create_buffers_with_zoom(monkeypatch):
    bm = BufferManager()

    data = Mock()
    data.convert_surfaces = Mock()

    view_size = (400, 300)
    buffer_size = (800, 600)  # zoom buffer required

    buffer, zoom_buffer = bm.create_buffers(
        view_size=view_size,
        buffer_size=buffer_size,
        clear_color=None,
        data=data,
    )

    assert isinstance(buffer, pygame.Surface)
    assert isinstance(zoom_buffer, pygame.Surface)


def test_create_buffers_with_colorkey():
    bm = BufferManager()

    data = Mock()
    data.convert_surfaces = Mock()

    clear_color = (10, 20, 30)

    buffer, zoom_buffer = bm.create_buffers(
        view_size=(200, 200),
        buffer_size=(200, 200),
        clear_color=clear_color,
        data=data,
    )

    assert buffer.get_colorkey() == (10, 20, 30, 255)
    data.convert_surfaces.assert_not_called()


def test_create_buffers_with_alpha_triggers_convert():
    bm = BufferManager()

    data = Mock()
    data.convert_surfaces = Mock()

    clear_color = (0, 0, 0, 0)  # alpha clear color

    buffer, zoom_buffer = bm.create_buffers(
        view_size=(200, 200),
        buffer_size=(200, 200),
        clear_color=clear_color,
        data=data,
    )

    data.convert_surfaces.assert_called_once_with(buffer, True)


def test_rebuild_quadtree_creates_renderer():
    bm = BufferManager()

    FakeQuadTree = Mock()
    FakeSpriteRenderer = Mock()

    data = Mock()
    tall_sprites = 0

    tile_view_size = (3, 2)
    tile_size = (32, 16)

    renderer = bm.rebuild_quadtree(
        tile_view_size=tile_view_size,
        tile_size=tile_size,
        FastQuadTree=FakeQuadTree,
        data=data,
        tall_sprites=tall_sprites,
        SpriteRenderer=FakeSpriteRenderer,
    )

    # Renderer returned
    FakeSpriteRenderer.assert_called_once()
    assert renderer is FakeSpriteRenderer.return_value

    # Quadtree built with correct number of rects
    assert FakeQuadTree.call_count == 1
    args, kwargs = FakeQuadTree.call_args
    rects = kwargs["items"]
    assert len(rects) == 3 * 2  # width * height
