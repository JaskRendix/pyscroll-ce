import pygame
import pytest
from pygame import Rect, Surface

from pyscroll.data import PyscrollDataAdapter
from pyscroll.isometric import IsometricBufferedRenderer
from pyscroll.sprite_manager import IsometricSpriteRenderer


class DummyAdapter(PyscrollDataAdapter):
    """Minimal adapter for testing isometric renderer."""

    def __init__(self):
        super().__init__()
        self._tile = Surface((32, 32))
        self._tile.fill((255, 0, 0))
        self._animation_map = {}
        self._tracked_gids = set()

    @property
    def tile_size(self):
        return (32, 32)

    @property
    def map_size(self):
        return (10, 10)

    @property
    def visible_tile_layers(self):
        return [0]

    def reload_data(self):
        pass

    def _get_tile_image(self, x, y, layer):
        return self._tile

    def _get_tile_image_by_id(self, id):
        return self._tile

    def get_animations(self):
        return []

    def _get_tile_gid(self, x, y, layer):
        return 0


@pytest.fixture
def renderer():
    pygame.init()
    adapter = DummyAdapter()
    r = IsometricBufferedRenderer(adapter, size=(320, 240))
    return r


def test_initialize_buffers(renderer):
    assert renderer._buffer is not None
    assert renderer._tile_view.width > 0
    assert renderer._tile_view.height > 0


def test_redraw_tiles(renderer):
    buf = renderer._buffer
    renderer.redraw_tiles(buf)
    px = buf.get_at((10, 10))
    assert px != (0, 0, 0, 255)


def test_sprite_renderer_draws_sprite(renderer):
    surf = Surface((320, 240))
    sprite = Surface((32, 32))
    sprite.fill((0, 255, 0))

    class DummyRenderable:
        rect = Rect(50, 50, 32, 32)
        surface = sprite
        blendmode = None
        layer = 0

    iso_renderer = IsometricSpriteRenderer()
    iso_renderer.render_sprites(
        surf,
        offset=(0, 0),
        tile_view=renderer._tile_view,
        surfaces=[DummyRenderable()],
    )

    px = surf.get_at((50, 50))
    assert px == (0, 255, 0, 255)


def test_center_updates_offsets(renderer):
    renderer.center((160, 120))
    assert isinstance(renderer._x_offset, int)
    assert isinstance(renderer._y_offset, int)
