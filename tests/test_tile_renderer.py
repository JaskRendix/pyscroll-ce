import pytest
from pygame import SRCALPHA, Rect, Surface

from pyscroll.data import PyscrollDataAdapter
from pyscroll.tile_renderer import TileRenderer


class DummyAdapter(PyscrollDataAdapter):
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

    def _get_tile_image(self, x, y, l):
        return self._tile

    def _get_tile_image_by_id(self, id):
        return self._tile

    def _get_tile_gid(self, x, y, l):
        return 0

    def get_tile_images_by_rect(self, rect):
        x, y, w, h = rect
        return [(i, j, 0, self._tile) for i in range(x, x + w) for j in range(y, y + h)]

    def prepare_tiles(self, tile_view):
        pass


@pytest.fixture
def tile_renderer():
    adapter = DummyAdapter()
    return TileRenderer(adapter, (0, 0, 0, 0))


@pytest.fixture
def tile_view():
    return Rect(2, 2, 2, 2)  # left=2, top=2, width=2, height=2


@pytest.mark.parametrize(
    "dx, dy, expected",
    [
        (-1, 0, {(2, 2), (2, 3)}),  # left
        (1, 0, {(3, 2), (3, 3)}),  # right
        (0, -1, {(2, 2), (3, 2)}),  # top
        (0, 1, {(2, 3), (3, 3)}),  # bottom
    ],
)
def test_queue_edge_tiles(tile_renderer, tile_view, dx, dy, expected):
    buffer_surface = Surface((128, 128))

    queue = tile_renderer.queue_edge_tiles(
        tile_view,
        dx,
        dy,
        buffer_surface,
    )

    coords = {(x, y) for (x, y, layer, img) in queue}
    assert coords == expected


def test_clear_region_clears_only_area(tile_renderer):
    surface = Surface((64, 64), flags=SRCALPHA)
    surface.fill((255, 255, 255, 255))
    tile_renderer.clear_region(surface, (16, 16, 32, 32))

    for x in range(16, 48):
        for y in range(16, 48):
            assert surface.get_at((x, y)) == (0, 0, 0, 0)

    assert surface.get_at((0, 0)) == (255, 255, 255, 255)
    assert surface.get_at((63, 63)) == (255, 255, 255, 255)


def test_clear_region_full_surface(tile_renderer):
    surface = Surface((32, 32), flags=SRCALPHA)
    surface.fill((10, 20, 30, 255))
    tile_renderer.clear_region(surface, None)
    for x in range(32):
        for y in range(32):
            assert surface.get_at((x, y)) == (0, 0, 0, 0)


def test_clear_region_rgb_surface(tile_renderer):
    surface = Surface((32, 32))
    surface.fill((200, 200, 200))
    tile_renderer.clear_region(surface, (0, 0, 32, 32))
    assert surface.get_at((10, 10)) == (0, 0, 0)


class ClearSpy:
    def __init__(self):
        self.calls = []

    def __call__(self, surface, area):
        self.calls.append(area)


@pytest.mark.parametrize(
    "dx, dy, expected_clear",
    [
        (-1, 0, [(0, 0, 32, 64)]),  # moving left → clear left column
        (1, 0, [(32, 0, 32, 64)]),  # moving right → clear right column
        (0, -1, [(0, 0, 64, 32)]),  # moving up → clear top row
        (0, 1, [(0, 32, 64, 32)]),  # moving down → clear bottom row
    ],
)
def test_queue_edge_tiles_clears_correct_regions(tile_view, dx, dy, expected_clear):
    spy = ClearSpy()
    adapter = DummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    renderer.clear_region = spy  # monkeypatch
    buffer_surface = Surface((128, 128))
    renderer.queue_edge_tiles(tile_view, dx, dy, buffer_surface)
    assert spy.calls == expected_clear


def test_flush_tile_queue_places_tiles_correctly(tile_view):
    adapter = DummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    buffer_surface = Surface((128, 128))
    buffer_surface.fill((0, 0, 0, 0))
    tile = adapter._tile
    queue = [(2, 2, 0, tile), (3, 2, 0, tile)]
    renderer.flush_tile_queue(queue, tile_view, buffer_surface)
    assert buffer_surface.get_at((0, 0)) == (255, 0, 0, 255)
    assert buffer_surface.get_at((32, 0)) == (255, 0, 0, 255)


def test_redraw_all_golden(tile_view):
    adapter = DummyAdapter()
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    buffer_surface = Surface((64, 64), flags=SRCALPHA)
    buffer_surface.fill((0, 0, 0, 0))
    renderer.redraw_all(tile_view, buffer_surface)

    for x in range(64):
        for y in range(64):
            expected = (255, 0, 0, 255)
            assert buffer_surface.get_at((x, y)) == expected


@pytest.mark.parametrize(
    "dx, dy",
    [
        (0, 0),  # no movement
        (-5, 0),  # large left movement
        (5, 0),  # large right movement
        (0, -5),  # large up movement
        (0, 5),  # large down movement
        (-100, 0),  # extreme movement
        (0, 100),
    ],
)
def test_queue_edge_tiles_edge_cases(tile_renderer, tile_view, dx, dy):
    buffer_surface = Surface((128, 128))
    queue = tile_renderer.queue_edge_tiles(tile_view, dx, dy, buffer_surface)

    for item in queue:
        x, y, layer, img = item
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert isinstance(layer, int)
        assert isinstance(img, Surface)


def test_large_map():
    adapter = DummyAdapter()
    adapter.map_size = (500, 500)
    renderer = TileRenderer(adapter, (0, 0, 0, 0))
    tile_view = Rect(100, 100, 10, 10)
    buffer_surface = Surface((320, 320))
    queue = renderer.queue_edge_tiles(tile_view, 1, 0, buffer_surface)
    assert len(queue) == 10  # one column of 10 tiles
