from __future__ import annotations

from unittest.mock import Mock

from pyscroll.animation_pipeline import AnimationPipeline


class DummySurface:
    pass


class DummyRect:
    pass


def test_animation_pipeline_forwards_calls() -> None:
    pipeline = AnimationPipeline()

    data = Mock()
    tile_renderer = Mock()

    buffer = DummySurface()
    tile_view = DummyRect()
    expanded_tile_view = DummyRect()

    # Fake animation queue
    fake_queue = ["a", "b", "c"]
    data.process_animation_queue.return_value = fake_queue

    pipeline.apply(
        data=data,
        tile_renderer=tile_renderer,
        tile_view=tile_view,
        expanded_tile_view=expanded_tile_view,
        buffer=buffer,
    )

    data.process_animation_queue.assert_called_once_with(expanded_tile_view)
    tile_renderer.flush_tile_queue.assert_called_once_with(
        fake_queue, tile_view, buffer
    )


def test_animation_pipeline_empty_queue() -> None:
    pipeline = AnimationPipeline()

    data = Mock()
    tile_renderer = Mock()

    buffer = DummySurface()
    tile_view = DummyRect()
    expanded_tile_view = DummyRect()

    data.process_animation_queue.return_value = []

    pipeline.apply(
        data=data,
        tile_renderer=tile_renderer,
        tile_view=tile_view,
        expanded_tile_view=expanded_tile_view,
        buffer=buffer,
    )

    tile_renderer.flush_tile_queue.assert_called_once_with([], tile_view, buffer)


def test_animation_pipeline_does_not_mutate_inputs() -> None:
    pipeline = AnimationPipeline()

    data = Mock()
    tile_renderer = Mock()

    buffer = DummySurface()
    tile_view = DummyRect()
    expanded_tile_view = DummyRect()

    pipeline.apply(
        data=data,
        tile_renderer=tile_renderer,
        tile_view=tile_view,
        expanded_tile_view=expanded_tile_view,
        buffer=buffer,
    )

    # Inputs remain untouched
    assert isinstance(buffer, DummySurface)
    assert isinstance(tile_view, DummyRect)
    assert isinstance(expanded_tile_view, DummyRect)
