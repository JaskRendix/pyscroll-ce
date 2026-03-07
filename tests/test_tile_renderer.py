import pytest
from pygame import SRCALPHA, Rect, Surface

from pyscroll.data import PyscrollDataAdapter
from pyscroll.tile_renderer import TileRenderer


class TileRendererDummyAdapter(PyscrollDataAdapter):
    tile_size = (32, 32)
    map_size = (32, 32)
    visible_tile_layers = [1]

    def __init__(self):
        super().__init__()
        self._tile = Surface((32, 32))
        self._tile.fill((255, 0, 0))
        self._animation_map = {}
        self._tracked_gids = set()

    def reload_data(self):
        pass

    def get_animations(self):
        return []

    def _get_tile_image(self, x, y, layer):
        return self._tile

    def _get_tile_image_by_id(self, id):
        return self._tile

    def _get_tile_gid(self, x, y, layer):
        return 0

    def get_tile_images_by_rect(self, rect):
        x, y, w, h = rect
        return [(i, j, 0, self._tile) for i in range(x, x + w) for j in range(y, y + h)]

    def prepare_tiles(self, tile_view):
        pass


@pytest.fixture
def tile_renderer():
    adapter = TileRendererDummyAdapter()
    return TileRenderer(adapter, (0, 0, 0, 0))


@pytest.fixture
def tile_view():
    return Rect(2, 2, 2, 2)  # left=2, top=2, width=2, height=2


@pytest.mark.parametrize(
    "dx, dy, expected_tiles",
    [
        pytest.param(-1, 0, {(2, 2), (2, 3)}, id="left"),
        pytest.param(1, 0, {(3, 2), (3, 3)}, id="right"),
        pytest.param(0, -1, {(2, 2), (3, 2)}, id="top"),
        pytest.param(0, 1, {(2, 3), (3, 3)}, id="bottom"),
        pytest.param(0, 0, set(), id="no_movement"),
        pytest.param(-5, 0, None, id="large_left"),
        pytest.param(5, 0, None, id="large_right"),
        pytest.param(0, -5, None, id="large_up"),
        pytest.param(0, 5, None, id="large_down"),
        pytest.param(-100, 0, None, id="extreme_left"),
        pytest.param(0, 100, None, id="extreme_down"),
    ],
)
def test_queue_edge_tiles_comprehensive(
    tile_renderer, tile_view, dx, dy, expected_tiles
):
    buffer_surface = Surface((128, 128))
    queue = tile_renderer.queue_edge_tiles(tile_view, dx, dy, buffer_surface)

    if expected_tiles is not None:
        coords = {(x, y) for (x, y, layer, img) in queue}
        assert coords == expected_tiles
    else:
        # Just verify structure
        for item in queue:
            x, y, layer, img = item
            assert all(isinstance(v, (int, type(None))) for v in [x, y, layer])


@pytest.mark.parametrize(
    "use_alpha,area,size,check_outside",
    [
        pytest.param(True, (16, 16, 32, 32), (64, 64), True, id="alpha_partial"),
        pytest.param(True, None, (32, 32), False, id="alpha_full"),
        pytest.param(False, (0, 0, 32, 32), (32, 32), False, id="rgb_surface"),
    ],
)
def test_clear_region_behavior(tile_renderer, use_alpha, area, size, check_outside):
    flags = SRCALPHA if use_alpha else 0
    fill_color = (255, 255, 255, 255) if use_alpha else (200, 200, 200)
    expected_clear = (0, 0, 0, 0) if use_alpha else (0, 0, 0)

    surface = Surface(size, flags=flags)
    surface.fill(fill_color)
    tile_renderer.clear_region(surface, area)

    if area:
        x, y, w, h = area
        for px in range(x, x + w):
            for py in range(y, y + h):
                assert surface.get_at((px, py)) == expected_clear
        if check_outside:
            assert surface.get_at((0, 0)) == fill_color
            assert surface.get_at((size[0] - 1, size[1] - 1)) == fill_color
    else:
        # Full surface
        for px in range(size[0]):
            for py in range(size[1]):
                assert surface.get_at((px, py)) == expected_clear


class ClearSpy:
    def __init__(self):
        self.calls = []

    def __call__(self, surface, area):
        self.calls.append(area)


@pytest.mark.parametrize(
    "dx, dy, expected_clear",
    [
        pytest.param(-1, 0, [(0, 0, 32, 64)], id="moving_left"),
        pytest.param(1, 0, [(32, 0, 32, 64)], id="moving_right"),
        pytest.param(0, -1, [(0, 0, 64, 32)], id="moving_up"),
        pytest.param(0, 1, [(0, 32, 64, 32)], id="moving_down"),
    ],
)
def test_queue_edge_tiles_clears_correct_regions(tile_view, dx, dy, expected_clear):
    spy = ClearSpy()
    adapter = TileRendererDummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    renderer.clear_region = spy  # monkeypatch
    buffer_surface = Surface((128, 128))
    renderer.queue_edge_tiles(tile_view, dx, dy, buffer_surface)
    assert spy.calls == expected_clear


def test_flush_tile_queue_places_tiles_correctly(tile_view):
    adapter = TileRendererDummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    buffer_surface = Surface((128, 128))
    buffer_surface.fill((0, 0, 0, 0))
    tile = adapter._tile
    queue = [(2, 2, 0, tile), (3, 2, 0, tile)]
    renderer.flush_tile_queue(queue, tile_view, buffer_surface)
    assert buffer_surface.get_at((0, 0)) == (255, 0, 0, 255)
    assert buffer_surface.get_at((32, 0)) == (255, 0, 0, 255)


def test_redraw_all_golden(tile_view):
    adapter = TileRendererDummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    buffer_surface = Surface((64, 64), flags=SRCALPHA)
    buffer_surface.fill((0, 0, 0, 0))
    renderer.redraw_all(tile_view, buffer_surface)

    for x in range(64):
        for y in range(64):
            expected = (255, 0, 0, 255)
            assert buffer_surface.get_at((x, y)) == expected


def test_large_map():
    adapter = TileRendererDummyAdapter()
    adapter.map_size = (500, 500)
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    tile_view = Rect(100, 100, 10, 10)
    buffer_surface = Surface((320, 320))
    queue = renderer.queue_edge_tiles(tile_view, 1, 0, buffer_surface)
    assert len(queue) == 10  # one column of 10 tiles


def test_queue_edge_tiles_no_buffer_surface(tile_renderer, tile_view):
    spy = []
    tile_renderer.clear_region = lambda *args, **kwargs: spy.append(True)

    queue = tile_renderer.queue_edge_tiles(tile_view, 1, 0, None)

    assert spy == []  # no clear calls
    assert len(queue) > 0  # still returns tiles


def test_queue_edge_tiles_no_movement_no_clear(tile_renderer, tile_view):
    spy = []
    tile_renderer.clear_region = lambda *args, **kwargs: spy.append(True)

    queue = tile_renderer.queue_edge_tiles(tile_view, 0, 0, Surface((128, 128)))

    assert spy == []  # nothing cleared
    assert queue == []  # no tiles added


def test_clear_region_accepts_rect(tile_renderer):
    surface = Surface((64, 64), flags=SRCALPHA)
    surface.fill((255, 255, 255, 255))

    area = Rect(10, 10, 20, 20)
    tile_renderer.clear_region(surface, area)

    for x in range(10, 30):
        for y in range(10, 30):
            assert surface.get_at((x, y)) == (0, 0, 0, 0)


def test_flush_tile_queue_does_not_mutate_queue(tile_view):
    adapter = TileRendererDummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    buffer_surface = Surface((128, 128))

    original = [(2, 2, 0, adapter._tile), (3, 2, 0, adapter._tile)]
    queue = list(original)

    renderer.flush_tile_queue(queue, tile_view, buffer_surface)

    assert queue == original  # unchanged


def test_flush_tile_queue_calls_prepare_once(tile_view):
    adapter = TileRendererDummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))

    calls = []
    adapter.prepare_tiles = lambda tv: calls.append(tv)

    queue = [(2, 2, 0, adapter._tile)]
    buffer_surface = Surface((128, 128))

    renderer.flush_tile_queue(queue, tile_view, buffer_surface)

    assert calls == [tile_view]


def test_flush_tile_queue_empty_queue(tile_view):
    adapter = TileRendererDummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    buffer_surface = Surface((128, 128))

    renderer.flush_tile_queue([], tile_view, buffer_surface)  # should not crash


def test_redraw_all_calls_flush_correctly(tile_view):
    adapter = TileRendererDummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))

    captured = {}

    def fake_flush(queue, view, surface):
        captured["queue"] = list(queue)
        captured["view"] = view

    renderer.flush_tile_queue = fake_flush

    buffer_surface = Surface((64, 64))
    renderer.redraw_all(tile_view, buffer_surface)

    expected_queue = adapter.get_tile_images_by_rect(tile_view)

    assert captured["view"] == tile_view
    assert captured["queue"] == expected_queue


def test_redraw_all_rgb_surface(tile_view):
    adapter = TileRendererDummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0))  # RGB clear color
    buffer_surface = Surface((64, 64))  # no alpha

    renderer.redraw_all(tile_view, buffer_surface)

    for x in range(64):
        for y in range(64):
            assert buffer_surface.get_at((x, y)) == (255, 0, 0)
