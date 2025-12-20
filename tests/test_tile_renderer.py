import pytest
from pygame import Rect, Surface

from pyscroll.data import PyscrollDataAdapter
from pyscroll.orthographic import TileRenderer


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
    return TileRenderer(adapter, lambda surf, area=None: None)


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

    # Extract only (x, y) from queue
    coords = {(x, y) for (x, y, layer, img) in queue}

    assert coords == expected
