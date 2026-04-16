from __future__ import annotations

from unittest.mock import Mock

from pyscroll.scroll_strategies import (
    FullRedrawStrategy,
    SmallScrollStrategy,
)


class DummyRect:
    """Minimal stand-in for pygame.Rect with only move_ip()."""

    def __init__(self, x: int = 0, y: int = 0) -> None:
        self.x = x
        self.y = y

    def move_ip(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy


class DummySurface:
    """Minimal stand-in for pygame.Surface with only scroll()."""

    def __init__(self) -> None:
        self.scroll_calls: list[tuple[int, int]] = []

    def scroll(self, dx: int, dy: int) -> None:
        self.scroll_calls.append((dx, dy))


def test_small_scroll_strategy_shifts_buffer_and_moves_tile_view() -> None:
    strategy = SmallScrollStrategy()

    buffer = DummySurface()
    tile_view = DummyRect()
    tile_renderer = Mock()

    # queue_edge_tiles returns a fake queue object
    fake_queue = ["tile1", "tile2"]
    tile_renderer.queue_edge_tiles.return_value = fake_queue

    # tile size
    tile_size = (32, 16)

    # Apply scroll: dx=1, dy=-2
    strategy.apply(
        dx=1,
        dy=-2,
        buffer=buffer,
        tile_view=tile_view,
        tile_renderer=tile_renderer,
        tile_size=tile_size,
    )

    # Buffer scroll should be called with pixel offsets
    assert buffer.scroll_calls == [(-32, 32)]

    # Tile view should move by tile units
    assert (tile_view.x, tile_view.y) == (1, -2)

    # queue_edge_tiles should be called correctly
    tile_renderer.queue_edge_tiles.assert_called_once_with(tile_view, 1, -2, buffer)

    # flush_tile_queue should be called with the returned queue
    tile_renderer.flush_tile_queue.assert_called_once_with(
        fake_queue, tile_view, buffer
    )


def test_full_redraw_strategy_moves_tile_view_and_calls_redraw() -> None:
    strategy = FullRedrawStrategy()

    buffer = DummySurface()
    tile_view = DummyRect()

    redraw_called: list[DummySurface] = []

    def fake_redraw(surface: DummySurface) -> None:
        redraw_called.append(surface)

    # Apply scroll: dx=-3, dy=5
    strategy.apply(
        dx=-3,
        dy=5,
        buffer=buffer,
        tile_view=tile_view,
        redraw_tiles=fake_redraw,
    )

    # Tile view should move
    assert (tile_view.x, tile_view.y) == (-3, 5)

    # Redraw should be called exactly once with the buffer
    assert redraw_called == [buffer]


def test_small_scroll_zero_movement_no_calls() -> None:
    strategy = SmallScrollStrategy()

    buffer = DummySurface()
    tile_view = DummyRect()
    tile_renderer = Mock()
    tile_renderer.queue_edge_tiles.return_value = []

    strategy.apply(
        dx=0,
        dy=0,
        buffer=buffer,
        tile_view=tile_view,
        tile_renderer=tile_renderer,
        tile_size=(32, 32),
    )

    # Zero scroll still produces a scroll(0, 0) call
    assert buffer.scroll_calls == [(0, 0)]

    # Tile view unchanged
    assert (tile_view.x, tile_view.y) == (0, 0)

    # queue_edge_tiles and flush_tile_queue still called once
    tile_renderer.queue_edge_tiles.assert_called_once()
    tile_renderer.flush_tile_queue.assert_called_once()


def test_full_redraw_zero_movement_still_redraws() -> None:
    strategy = FullRedrawStrategy()

    buffer = DummySurface()
    tile_view = DummyRect()

    calls: list[DummySurface] = []

    def fake_redraw(surface: DummySurface) -> None:
        calls.append(surface)

    strategy.apply(
        dx=0,
        dy=0,
        buffer=buffer,
        tile_view=tile_view,
        redraw_tiles=fake_redraw,
    )

    # Tile view unchanged
    assert (tile_view.x, tile_view.y) == (0, 0)

    # Redraw still happens
    assert calls == [buffer]


def test_small_scroll_large_tile_size() -> None:
    strategy = SmallScrollStrategy()

    buffer = DummySurface()
    tile_view = DummyRect()
    tile_renderer = Mock()
    tile_renderer.queue_edge_tiles.return_value = []

    strategy.apply(
        dx=2,
        dy=-1,
        buffer=buffer,
        tile_view=tile_view,
        tile_renderer=tile_renderer,
        tile_size=(256, 512),
    )

    # Pixel scroll = (-dx * tw, -dy * th)
    assert buffer.scroll_calls == [(-512, 512)]

    # Tile view moves by tile units
    assert (tile_view.x, tile_view.y) == (2, -1)


def test_small_scroll_negative_tile_size() -> None:
    strategy = SmallScrollStrategy()

    buffer = DummySurface()
    tile_view = DummyRect()
    tile_renderer = Mock()
    tile_renderer.queue_edge_tiles.return_value = []

    # Negative tile sizes should not crash; math still applies
    strategy.apply(
        dx=1,
        dy=1,
        buffer=buffer,
        tile_view=tile_view,
        tile_renderer=tile_renderer,
        tile_size=(-32, -16),
    )

    # Scroll uses the negative values directly
    assert buffer.scroll_calls == [(32, 16)]

    # Tile view still moves logically
    assert (tile_view.x, tile_view.y) == (1, 1)
