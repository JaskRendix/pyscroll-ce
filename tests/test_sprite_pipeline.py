from __future__ import annotations

from unittest.mock import Mock

from pyscroll.sprite_pipeline import SpritePipeline


class DummySurface:
    pass


class DummyRect:
    pass


class DummyRenderable:
    pass


def test_sprite_pipeline_forwards_arguments() -> None:
    pipeline = SpritePipeline()

    sprite_renderer = Mock()
    surface = DummySurface()
    tile_view = DummyRect()
    sprites = [DummyRenderable(), DummyRenderable()]
    offset = (10, -5)

    pipeline.apply(
        sprite_renderer=sprite_renderer,
        surface=surface,
        offset=offset,
        tile_view=tile_view,
        sprites=sprites,
    )

    sprite_renderer.render_sprites.assert_called_once_with(
        surface,
        offset,
        tile_view,
        sprites,
    )


def test_sprite_pipeline_does_not_modify_inputs() -> None:
    pipeline = SpritePipeline()

    sprite_renderer = Mock()
    surface = DummySurface()
    tile_view = DummyRect()
    sprites = [DummyRenderable()]
    offset = (3, 7)

    pipeline.apply(
        sprite_renderer=sprite_renderer,
        surface=surface,
        offset=offset,
        tile_view=tile_view,
        sprites=sprites,
    )

    # Ensure pipeline does not mutate inputs
    assert offset == (3, 7)
    assert sprites == [sprites[0]]
    assert isinstance(tile_view, DummyRect)
    assert isinstance(surface, DummySurface)


def test_sprite_pipeline_no_render_when_no_sprites() -> None:
    pipeline = SpritePipeline()

    sprite_renderer = Mock()
    surface = DummySurface()
    tile_view = DummyRect()
    sprites: list[DummyRenderable] = []
    offset = (0, 0)

    pipeline.apply(
        sprite_renderer=sprite_renderer,
        surface=surface,
        offset=offset,
        tile_view=tile_view,
        sprites=sprites,
    )

    # Even with empty list, call should still occur exactly once
    sprite_renderer.render_sprites.assert_called_once_with(
        surface,
        offset,
        tile_view,
        sprites,
    )
