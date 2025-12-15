from collections.abc import Iterable
from typing import Optional

import pytest
from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.data import PyscrollDataAdapter


class DummyAdapter(PyscrollDataAdapter):
    def __init__(self):
        super().__init__()
        self._animated_tile = {}
        self._animation_map = {}
        self._animation_queue = []
        self._tracked_gids = set()

    @property
    def tile_size(self) -> tuple[int, int]:
        return (32, 32)

    @property
    def map_size(self) -> tuple[int, int]:
        return (32, 32)

    @property
    def visible_tile_layers(self) -> list[int]:
        return [0]

    def reload_data(self) -> None:
        raise NotImplementedError

    def _get_tile_image(self, x: int, y: int, l: int) -> Optional[Surface]:
        return None

    def _get_tile_image_by_id(self, id: int) -> Optional[Surface]:
        raise NotImplementedError

    def get_animations(self) -> Iterable[tuple[int, list[tuple[int, int]]]]:
        raise NotImplementedError

    def _get_tile_gid(self, x: int, y: int, l: int) -> Optional[int]:
        raise NotImplementedError


@pytest.fixture
def adapter():
    return DummyAdapter()


@pytest.mark.parametrize(
    "method,args",
    [
        ("reload_animations", []),
        ("_get_tile_image_by_id", [0]),
        ("get_animations", []),
        ("_get_tile_gid", [0, 0, 0]),
    ],
)
def test_not_implemented_methods(adapter, method, args):
    with pytest.raises(NotImplementedError):
        getattr(adapter, method)(*args)


def test_process_animation_queue_empty(adapter):
    tile_view = Rect(0, 0, 10, 10)
    assert adapter.process_animation_queue(tile_view) == []


def test_prepare_tiles(adapter):
    tiles = Rect(0, 0, 10, 10)
    adapter.prepare_tiles(tiles)


def test_get_tile_images_by_rect_empty(adapter):
    rect = Rect(0, 0, 10, 10)
    assert list(adapter.get_tile_images_by_rect(rect)) == []


def test_pause_and_resume(adapter):
    adapter.pause_animations()
    assert adapter._is_paused
    paused_time = adapter._paused_time
    adapter.resume_animations()
    assert not adapter._is_paused
    assert adapter._paused_time == 0.0 or adapter._paused_time != paused_time


@pytest.mark.parametrize("skip_ahead", [False, True])
def test_update_time_modes(adapter, skip_ahead):
    adapter._pause_mode_skip_ahead = skip_ahead
    before = adapter._last_time
    adapter._update_time()
    assert adapter._last_time >= before


def test_set_animation_speed_multiplier_invalid(adapter):
    with pytest.raises(ValueError):
        adapter.set_animation_speed_multiplier(0)


def test_pixel_to_tile(adapter):
    assert adapter.pixel_to_tile(64, 96) == (2, 3)
    assert adapter.pixel_to_tile(0, 0) == (0, 0)
    assert adapter.pixel_to_tile(63.9, 31.9) == (1, 0)


def test_is_on_map(adapter):
    assert adapter.is_on_map(0, 0)
    assert adapter.is_on_map(31, 31)
    assert not adapter.is_on_map(-1, 0)
    assert not adapter.is_on_map(0, 32)
    assert not adapter.is_on_map(32, 0)
