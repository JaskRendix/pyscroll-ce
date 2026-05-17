from unittest.mock import MagicMock

import pygame
import pytest
from pygame.surface import Surface

from pyscroll.data import TiledMapData


@pytest.fixture
def mock_tmx():
    mock = MagicMock()
    mock.tilewidth = 16
    mock.tileheight = 16
    mock.width = 10
    mock.height = 10
    mock.visible_tile_layers = [0]

    img0 = Surface((16, 16))
    img1 = Surface((16, 16))
    img0.fill((255, 0, 0))
    img1.fill((0, 255, 0))
    mock.images = [img0, img1]

    mock.layers = [MagicMock()]
    mock.layers[0].visible = True
    mock.layers[0].data = [[1 for _ in range(10)] for _ in range(10)]

    mock.tile_properties = {1: {"frames": [(0, 100), (1, 100)]}}
    mock.get_tile_image = lambda x, y, l: None
    mock.filename = "test.tmx"
    return mock


@pytest.fixture
def tiled_map_data(mock_tmx):
    data = TiledMapData(mock_tmx)
    data.at = {(x, y, 0): 1 for x in range(10) for y in range(10)}
    data.images = mock_tmx.images
    return data


def test_tile_and_map_size(tiled_map_data):
    assert tiled_map_data.tile_size == (16, 16)
    assert tiled_map_data.map_size == (10, 10)


def test_visible_tile_layers(tiled_map_data):
    assert tiled_map_data.visible_tile_layers == [0]


def test_get_tile_image(tiled_map_data):
    image = tiled_map_data.get_tile_image(0, 0, 0)
    assert isinstance(image, Surface)


def test_get_tile_image_by_id(tiled_map_data):
    image = tiled_map_data._get_tile_image_by_id(0)
    assert isinstance(image, Surface)


def test_get_animations(tiled_map_data):
    animations = list(tiled_map_data.get_animations())
    assert len(animations) == 1
    gid, frames = animations[0]
    assert gid == 1
    assert frames[0][1] == 100


def test_get_tile_gid_valid_and_invalid(tiled_map_data):
    gid = tiled_map_data._get_tile_gid(0, 0, 0)
    assert gid == 1
    gid = tiled_map_data._get_tile_gid(99, 99, 0)
    assert gid is None


def test_get_tile_images_by_rect(tiled_map_data):
    rect = (0, 0, 2, 2)
    tiles = list(tiled_map_data.get_tile_images_by_rect(rect))
    assert all(isinstance(t[3], Surface) for t in tiles)
    assert len(tiles) > 0


def test_convert_surfaces_alpha_and_non_alpha(mock_tmx):
    data = TiledMapData(mock_tmx)
    parent = Surface((16, 16))
    data.convert_surfaces(parent, alpha=False)
    assert isinstance(data.tmx.images[0], Surface) or data.tmx.images[0] is None
    data.convert_surfaces(parent, alpha=True)
    assert isinstance(data.tmx.images[0], Surface) or data.tmx.images[0] is None


def test_reload_animations_populates_structures(tiled_map_data):
    tiled_map_data.reload_animations()
    assert tiled_map_data._tracked_gids == {1}
    assert len(tiled_map_data._animation_map) == 1
    assert len(tiled_map_data._animation_queue) >= 1


def test_process_animation_queue_updates_tiles(tiled_map_data):
    tiled_map_data.reload_animations()

    # Touch tile (0,0,0) so it becomes tracked
    tiled_map_data.get_tile_image(0, 0, 0)
    target_pos = (0, 0, 0)

    # Ensure it is tracked by at least one token
    token = None
    for t in tiled_map_data._animation_queue:
        if target_pos in t.positions:
            token = t
            break

    assert token is not None

    # Force this token to be "ready" and ensure call does not crash
    token.next = 0
    tile_view = pygame.Rect(0, 0, 10, 10)
    updates = tiled_map_data.process_animation_queue(tile_view)

    assert isinstance(updates, list)


def test_get_tile_images_by_rect_coordinates(tiled_map_data):
    rect = (0, 0, 2, 2)
    tiles = list(tiled_map_data.get_tile_images_by_rect(rect))

    xs = {x for x, y, layer, surf in tiles}
    ys = {y for x, y, layer, surf in tiles}

    assert xs == {0, 1}
    assert ys == {0, 1}


def test_convert_surfaces_modifies_images(mock_tmx):
    data = TiledMapData(mock_tmx)
    parent = Surface((16, 16))

    before = data.tmx.images[0]
    data.convert_surfaces(parent, alpha=False)
    after = data.tmx.images[0]

    assert isinstance(after, Surface)
    assert after is not before


def test_get_tile_gid_invalid_layer(tiled_map_data):
    assert tiled_map_data._get_tile_gid(0, 0, 99) is None


def test_get_tile_image_invalid_coords(tiled_map_data):
    img = tiled_map_data.get_tile_image(999, 999, 0)
    assert img is None
