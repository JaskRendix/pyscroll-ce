import pytest
from pygame import Rect

from pyscroll.viewport_pipeline import ViewportPipeline


class DummyViewport:
    """Minimal viewport stub for testing ViewportPipeline."""

    def __init__(self):
        self.x_offset = 10
        self.y_offset = 20
        self.tile_view = Rect(5, 5, 100, 80)

        # Track calls for delegation tests
        self.calls = []

    # --- Delegated methods -------------------------------------------------

    def translate_point(self, point):
        self.calls.append(("translate_point", point))
        return (point[0] + 1, point[1] + 2)

    def translate_rect(self, rect):
        self.calls.append(("translate_rect", rect))
        return Rect(rect.x + 3, rect.y + 4, rect.w, rect.h)

    def translate_points(self, points):
        self.calls.append(("translate_points", points))
        return [(p[0] + 5, p[1] + 6) for p in points]

    def translate_rects(self, rects):
        self.calls.append(("translate_rects", rects))
        return [Rect(r.x + 7, r.y + 8, r.w, r.h) for r in rects]


@pytest.fixture
def pipeline():
    vp = DummyViewport()
    return ViewportPipeline(vp), vp


def test_compute_offset_basic(pipeline):
    pipe, vp = pipeline
    rect = Rect(100, 200, 50, 50)

    ox, oy = pipe.compute_offset(rect)

    assert ox == -vp.x_offset + rect.left
    assert oy == -vp.y_offset + rect.top


def test_compute_offset_negative_offsets(pipeline):
    pipe, vp = pipeline
    vp.x_offset = -30
    vp.y_offset = -40
    rect = Rect(10, 10, 10, 10)

    ox, oy = pipe.compute_offset(rect)

    assert ox == 40  # -(-30) + 10
    assert oy == 50  # -(-40) + 10


def test_expanded_tile_view_no_overdraw(pipeline):
    pipe, vp = pipeline

    tv = pipe.expanded_tile_view((0, 0))

    assert tv == vp.tile_view
    assert tv is vp.tile_view  # must return original object when no change


def test_expanded_tile_view_with_overdraw(pipeline):
    pipe, vp = pipeline

    tv = pipe.expanded_tile_view((3, 4))

    assert tv.x == vp.tile_view.x - 3
    assert tv.y == vp.tile_view.y - 4
    assert tv.width == vp.tile_view.width + 6
    assert tv.height == vp.tile_view.height + 8


def test_expanded_tile_view_does_not_mutate_original(pipeline):
    pipe, vp = pipeline
    original = vp.tile_view.copy()

    _ = pipe.expanded_tile_view((10, 10))

    assert vp.tile_view == original  # original must remain unchanged


def test_translate_point_delegates(pipeline):
    pipe, vp = pipeline

    result = pipe.translate_point((1, 2))

    assert result == (2, 4)
    assert vp.calls[-1] == ("translate_point", (1, 2))


def test_translate_rect_delegates(pipeline):
    pipe, vp = pipeline
    rect = Rect(10, 20, 30, 40)

    result = pipe.translate_rect(rect)

    assert result == Rect(13, 24, 30, 40)
    assert vp.calls[-1] == ("translate_rect", rect)


def test_translate_points_delegates(pipeline):
    pipe, vp = pipeline
    pts = [(1, 1), (2, 2)]

    result = pipe.translate_points(pts)

    assert result == [(6, 7), (7, 8)]
    assert vp.calls[-1] == ("translate_points", pts)


def test_translate_rects_delegates(pipeline):
    pipe, vp = pipeline
    rects = [Rect(1, 1, 5, 5), Rect(2, 2, 6, 6)]

    result = pipe.translate_rects(rects)

    assert result == [
        Rect(8, 9, 5, 5),
        Rect(9, 10, 6, 6),
    ]
    assert vp.calls[-1] == ("translate_rects", rects)


def test_pipeline_reflects_viewport_changes(pipeline):
    pipe, vp = pipeline

    vp.x_offset = 100
    vp.y_offset = 200

    ox, oy = pipe.compute_offset(Rect(0, 0, 10, 10))

    assert ox == -100
    assert oy == -200
