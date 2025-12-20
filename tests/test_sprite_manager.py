import pygame
import pytest
from pygame import Rect, Surface

from pyscroll.data import PyscrollDataAdapter
from pyscroll.orthographic import SpriteRenderer
from pyscroll.quadtree import FastQuadTree


class DummyRenderable:
    def __init__(self, rect, surface, layer=0, blendmode=None):
        self.rect = rect
        self.surface = surface
        self.layer = layer
        self.blendmode = blendmode


class DummyAdapter(PyscrollDataAdapter):
    tile_size = (32, 32)
    map_size = (10, 10)
    visible_tile_layers = [0, 1]

    def __init__(self):
        super().__init__()
        self._tile = Surface((32, 32))
        self._tile.fill((255, 0, 0))

        self._animation_map = {}
        self._animated_tile = {}
        self._tracked_gids = set()

    def reload_data(self):
        pass

    def get_animations(self):
        return []

    def _get_tile_image(self, x, y, l):
        return self._tile

    def _get_tile_image_by_id(self, id):
        return self._tile

    def _get_tile_gid(self, x, y, l):
        return 0


@pytest.fixture
def adapter():
    pygame.init()
    return DummyAdapter()


@pytest.fixture
def quadtree():
    rects = [
        Rect(0, 0, 32, 32),
        Rect(32, 0, 32, 32),
        Rect(0, 32, 32, 32),
        Rect(32, 32, 32, 32),
    ]
    return FastQuadTree(rects, depth=2)


@pytest.fixture
def renderer(adapter, quadtree):
    return SpriteRenderer(adapter, quadtree, tall_sprites=0)


@pytest.fixture
def surface():
    return Surface((200, 200))


@pytest.fixture
def tile_view():
    return Rect(0, 0, 10, 10)


def test_basic_sprite_blit(renderer, surface, tile_view):
    sprite = Surface((20, 20))
    sprite.fill((0, 255, 0))  # green
    r = DummyRenderable(Rect(50, 50, 20, 20), sprite, layer=1)
    renderer.render_sprites(surface, offset=(0, 0), tile_view=tile_view, surfaces=[r])
    px = surface.get_at((50, 50))
    assert px == (0, 255, 0, 255)


def test_blendmode(renderer, surface, tile_view):
    sprite = Surface((20, 20), pygame.SRCALPHA)
    sprite.fill((0, 0, 255, 255))
    r = DummyRenderable(
        Rect(10, 10, 20, 20), sprite, layer=2, blendmode=pygame.BLEND_ADD
    )
    renderer.render_sprites(surface, offset=(0, 0), tile_view=tile_view, surfaces=[r])
    px = surface.get_at((10, 10))
    assert px[2] > 0


def test_tile_redraw(renderer, surface, tile_view, adapter):
    sprite = Surface((32, 32))
    sprite.fill((0, 255, 0))
    r = DummyRenderable(Rect(0, 0, 32, 32), sprite, layer=0)
    renderer.render_sprites(surface, offset=(0, 0), tile_view=tile_view, surfaces=[r])
    px_under = surface.get_at((5, 5))
    assert px_under in [(0, 255, 0, 255), (255, 0, 0, 255)]


def test_tall_sprite_damage_region(adapter, quadtree, surface, tile_view):
    renderer = SpriteRenderer(adapter, quadtree, tall_sprites=16)
    sprite = Surface((32, 32))
    sprite.fill((0, 255, 0))
    r = DummyRenderable(Rect(0, 0, 32, 32), sprite, layer=0)
    renderer.render_sprites(surface, offset=(0, 0), tile_view=tile_view, surfaces=[r])
    px = surface.get_at((0, 0))
    assert px != (0, 0, 0, 255)


def test_sprite_sorting(renderer, surface, tile_view):
    s1 = Surface((20, 20))
    s1.fill((255, 0, 0))  # red
    s2 = Surface((20, 20))
    s2.fill((0, 255, 0))  # green
    r1 = DummyRenderable(Rect(10, 10, 20, 20), s1, layer=0)
    r2 = DummyRenderable(Rect(10, 10, 20, 20), s2, layer=1)
    renderer.render_sprites(
        surface, offset=(0, 0), tile_view=tile_view, surfaces=[r1, r2]
    )
    px = surface.get_at((10, 10))
    assert px == (0, 255, 0, 255)
