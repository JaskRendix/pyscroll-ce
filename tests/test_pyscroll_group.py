from unittest.mock import MagicMock

import pygame
import pytest
from pygame.rect import Rect
from pygame.sprite import Sprite
from pygame.surface import Surface

from pyscroll.group import PyscrollGroup
from pyscroll.orthographic import BufferedRenderer


@pytest.fixture(scope="module", autouse=True)
def pygame_init():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def surface():
    return Surface((640, 480))


@pytest.fixture
def map_layer():
    return MagicMock(spec=BufferedRenderer)


@pytest.fixture
def group(map_layer):
    return PyscrollGroup(map_layer)


@pytest.fixture
def sprite():
    spr = MagicMock(spec=Sprite)
    spr.image = Surface((32, 32))
    spr.rect = Rect(10, 10, 32, 32)
    return spr


def test_init(group, map_layer):
    assert isinstance(group, PyscrollGroup)
    assert group._map_layer is map_layer


def test_center(group, map_layer):
    group.center((100, 100))
    map_layer.center.assert_called_once_with((100, 100))


def test_view(group, map_layer):
    map_layer.view_rect = Rect(0, 0, 640, 480)
    assert group.view == Rect(0, 0, 640, 480)


@pytest.mark.parametrize(
    "offset, sprite_pos, expected",
    [
        ((0, 0), Rect(10, 10, 32, 32), Rect(10, 10, 32, 32)),
        ((50, 50), Rect(10, 10, 32, 32), Rect(60, 60, 32, 32)),
        ((-20, -20), Rect(100, 100, 32, 32), Rect(80, 80, 32, 32)),
    ],
)
def test_draw_parametrized(
    group, map_layer, surface, sprite, offset, sprite_pos, expected
):
    sprite.rect = sprite_pos
    group.add(sprite)

    map_layer.get_center_offset.return_value = offset
    map_layer.view_rect = Rect(0, 0, 640, 480)
    map_layer.draw.return_value = [expected]

    drawn = group.draw(surface)
    assert drawn == [expected]


@pytest.mark.parametrize("blendmode", [None, pygame.BLEND_ADD])
def test_draw_blendmode(group, map_layer, surface, sprite, blendmode):
    if blendmode is None:
        if hasattr(sprite, "blendmode"):
            del sprite.blendmode
    else:
        sprite.blendmode = blendmode

    group.add(sprite)

    map_layer.get_center_offset.return_value = (0, 0)
    map_layer.view_rect = Rect(0, 0, 640, 480)
    map_layer.draw.return_value = [sprite.rect]

    drawn = group.draw(surface)
    assert drawn == [sprite.rect]


@pytest.mark.parametrize(
    "sprite_pos, visible",
    [
        (Rect(10, 10, 32, 32), True),
        (Rect(1000, 1000, 32, 32), False),
        (Rect(630, 470, 32, 32), True),  # partially visible
    ],
)
def test_visibility(group, map_layer, surface, sprite, sprite_pos, visible):
    sprite.rect = sprite_pos
    group.add(sprite)

    map_layer.get_center_offset.return_value = (0, 0)
    map_layer.view_rect = Rect(0, 0, 640, 480)
    map_layer.draw.return_value = [sprite.rect] if visible else []

    drawn = group.draw(surface)
    assert drawn == ([sprite.rect] if visible else [])


def test_sprite_layer(group, map_layer, surface, sprite):
    group.add(sprite, layer=3)

    map_layer.get_center_offset.return_value = (0, 0)
    map_layer.view_rect = Rect(0, 0, 640, 480)
    map_layer.draw.return_value = [sprite.rect]

    group.draw(surface)
    assert group.get_layer_of_sprite(sprite) == 3


def test_lostsprites_reset(group, map_layer, surface, sprite):
    group.add(sprite)

    map_layer.get_center_offset.return_value = (0, 0)
    map_layer.view_rect = Rect(0, 0, 640, 480)
    map_layer.draw.return_value = [sprite.rect]

    group.lostsprites = [sprite]
    group.draw(surface)

    assert group.lostsprites == []
