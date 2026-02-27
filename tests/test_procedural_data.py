import pygame
import pytest
from pygame.surface import Surface
from pyscroll.data import ProceduralData


@pytest.fixture
def proc():
    pygame.init()
    return ProceduralData()


def test_tile_size_and_map_size(proc):
    assert proc.tile_size == (32, 32)
    assert proc.map_size == (40, 30)
    assert proc.visible_tile_layers == [0, 1, 2]


def test_pixel_to_tile(proc):
    assert proc.pixel_to_tile(64, 96) == (2, 3)
    assert proc.pixel_to_tile(0, 0) == (0, 0)
    assert proc.pixel_to_tile(31.9, 31.9) == (0, 0)


def test_is_on_map(proc):
    assert proc.is_on_map(0, 0)
    assert proc.is_on_map(39, 29)
    assert not proc.is_on_map(-1, 0)
    assert not proc.is_on_map(40, 0)
    assert not proc.is_on_map(0, 30)


def test_get_tile_gid_ground(proc):
    assert proc._get_tile_gid(0, 0, 0) == proc._GID_GRASS
    assert proc._get_tile_gid(1, 0, 0) == proc._GID_WATER


def test_get_tile_gid_detail(proc):
    assert proc._get_tile_gid(5, 5, 1) == proc._GID_ROCK
    assert proc._get_tile_gid(6, 5, 1) is None


def test_get_tile_gid_overlay(proc):
    assert proc._get_tile_gid(0, 0, 2) is None


def test_get_tile_image(proc):
    img = proc._get_tile_image(0, 0, 0)
    assert isinstance(img, Surface)
    assert img.get_size() == proc.tile_size


def test_get_tile_image_by_id(proc):
    img = proc._get_tile_image_by_id(proc._GID_GRASS)
    assert isinstance(img, Surface)


def test_get_animations(proc):
    animations = proc.get_animations()
    assert isinstance(animations, list)
    gid, frames = animations[0]
    assert gid == proc._GID_WATER
    assert all(isinstance(f[0], int) and isinstance(f[1], int) for f in frames)
