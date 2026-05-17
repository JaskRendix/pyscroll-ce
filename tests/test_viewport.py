import pytest
from pygame import Rect

from pyscroll.viewport import IsometricViewport, ViewPort


class DummyData:
    def __init__(self, tile_size=(32, 32), map_size=(100, 80)):
        self.tile_size = tile_size
        self.map_size = map_size


@pytest.fixture
def data():
    return DummyData()


@pytest.fixture
def viewport(data):
    return ViewPort(data=data, size=(640, 480), zoom=1.0, clamp_camera=True)


@pytest.fixture
def iso_viewport(data):
    return IsometricViewport(data=data, size=(640, 480), zoom=1.0, clamp_camera=True)


def test_initial_state(viewport, data):
    assert viewport.zoom == 1.0
    assert viewport.size == (640, 480)
    assert viewport.tile_view.width > 0
    assert viewport.tile_view.height > 0
    assert viewport.map_rect.width == data.map_size[0] * data.tile_size[0]
    assert viewport.map_rect.height == data.map_size[1] * data.tile_size[1]


def test_zoom_changes_buffer_size(viewport):
    before = viewport.view_rect.size
    viewport.zoom = 2.0
    after = viewport.view_rect.size
    assert after[0] < before[0]
    assert after[1] < before[1]


def test_zoom_cannot_be_zero(viewport):
    with pytest.raises(ValueError):
        viewport.zoom = 0


def test_set_size_updates_tile_view(viewport):
    viewport.set_size((800, 600))
    assert viewport.size == (800, 600)
    assert viewport.tile_view.width > 0
    assert viewport.tile_view.height > 0


def test_center_clamps_inside_map(viewport, data):
    # Move far outside map
    viewport.center((999999, 999999))
    cx, cy = viewport.view_rect.center
    assert 0 <= cx <= data.map_size[0] * data.tile_size[0]
    assert 0 <= cy <= data.map_size[1] * data.tile_size[1]


def test_center_reports_tile_view_change(viewport):
    viewport.clamp_camera = False
    new_left, new_top, dx, dy, view_change = viewport.center((2000, 2000))
    assert view_change >= 0
    assert new_left >= 0
    assert new_top >= 0


def test_scroll_moves_center(viewport):
    cx0, cy0 = viewport.view_rect.center
    viewport.scroll((50, 25))
    cx1, cy1 = viewport.view_rect.center
    assert (cx1, cy1) == (cx0 + 50, cy0 + 25)


def test_get_center_offset(viewport):
    viewport.center((200, 150))
    ox, oy = viewport.get_center_offset()
    assert isinstance(ox, int)
    assert isinstance(oy, int)


def test_translate_point(viewport):
    viewport.center((300, 200))
    sx, sy = viewport.get_center_offset()
    px, py = viewport.translate_point((10, 20))
    assert px == int(10 + sx)
    assert py == int(20 + sy)


def test_translate_rect(viewport):
    viewport.center((300, 200))
    sx, sy = viewport.get_center_offset()
    r = viewport.translate_rect((10, 20, 30, 40))
    assert r.x == 10 + sx
    assert r.y == 20 + sy
    assert r.w == 30
    assert r.h == 40


def test_translate_points(viewport):
    viewport.center((300, 200))
    sx, sy = viewport.get_center_offset()
    pts = viewport.translate_points([(0, 0), (10, 10)])
    assert pts[0] == (sx, sy)
    assert pts[1] == (10 + sx, 10 + sy)


def test_translate_rects(viewport):
    viewport.center((300, 200))
    sx, sy = viewport.get_center_offset()
    rects = viewport.translate_rects([Rect(0, 0, 5, 5), Rect(10, 10, 6, 6)])
    assert rects[0].x == sx
    assert rects[0].y == sy
    assert rects[1].x == 10 + sx
    assert rects[1].y == 10 + sy


def test_center_on_negative_coords(viewport):
    viewport.center((-100, -100))
    cx, cy = viewport.view_rect.center
    assert cx >= 0
    assert cy >= 0


def test_tiny_map(data):
    data.map_size = (1, 1)
    vp = ViewPort(data=data, size=(640, 480), zoom=1.0, clamp_camera=True)
    vp.center((0, 0))
    cx, cy = vp.view_rect.center
    assert cx >= 0
    assert cy >= 0


def test_huge_map(data):
    data.map_size = (10000, 8000)
    vp = ViewPort(data=data, size=(640, 480), zoom=1.0, clamp_camera=True)
    vp.center((500000, 500000))
    cx, cy = vp.view_rect.center
    assert cx <= data.map_size[0] * data.tile_size[0]
    assert cy <= data.map_size[1] * data.tile_size[1]


def test_iso_center_updates_offsets(iso_viewport):
    iso_viewport.center((300, 200))
    ox, oy = iso_viewport.get_center_offset()
    assert isinstance(ox, int)
    assert isinstance(oy, int)


def test_iso_translate_point(iso_viewport):
    iso_viewport.center((300, 200))
    px, py = iso_viewport.translate_point((10, 20))
    assert isinstance(px, int)
    assert isinstance(py, int)


def test_iso_tile_view_moves(iso_viewport):
    left0, top0 = iso_viewport.tile_view.topleft
    iso_viewport.center((400, 300))
    left1, top1 = iso_viewport.tile_view.topleft
    assert (left0, top0) != (left1, top1)
