import pytest
from pygame.rect import Rect

from pyscroll.quadtree import FastQuadTree


@pytest.mark.parametrize(
    "rectangles, query, expected_count",
    [
        pytest.param(
            [Rect(0, 0, 10, 10), Rect(5, 5, 10, 10), Rect(10, 10, 10, 10)],
            Rect(2, 2, 12, 12),
            ">0",
            id="overlap_multiple",
        ),
        pytest.param(
            [Rect(0, 0, 10, 10), Rect(20, 20, 10, 10), Rect(30, 30, 10, 10)],
            Rect(5, 5, 5, 5),
            1,
            id="single_hit",
        ),
        pytest.param([Rect(0, 0, 10, 10)], Rect(0, 0, 10, 10), 1, id="exact_match"),
        pytest.param(
            [Rect(0, 0, 10, 10), Rect(20, 20, 10, 10)],
            Rect(100, 100, 10, 10),
            0,
            id="no_hit",
        ),
        pytest.param(
            [Rect(0, 0, 10, 10)], Rect(10, 0, 5, 5), 0, id="boundary_collision"
        ),
        pytest.param(
            [Rect(0, 0, 10, 10), Rect(5, 5, 10, 10), Rect(8, 8, 10, 10)],
            Rect(6, 6, 5, 5),
            ">=2",
            id="multiple_hits",
        ),
    ],
)
def test_hit(rectangles, query, expected_count):
    qt = FastQuadTree(rectangles)
    collisions = qt.hit(query)
    if expected_count == ">0":
        assert len(collisions) > 0
    elif isinstance(expected_count, str) and expected_count.startswith(">="):
        min_count = int(expected_count[2:])
        assert len(collisions) >= min_count
    else:
        assert len(collisions) == expected_count


def test_init_nonempty():
    rectangles = [Rect(0, 0, 10, 10), Rect(5, 5, 10, 10)]
    qt = FastQuadTree(rectangles)
    assert qt is not None


def test_empty_tree_raises():
    with pytest.raises(ValueError):
        FastQuadTree([])


def test_overlap_multiple_quadrants():
    rectangles = [
        Rect(0, 0, 50, 50),  # overlaps all quadrants
        Rect(60, 0, 10, 10),  # NE
        Rect(0, 60, 10, 10),  # SW
    ]
    qt = FastQuadTree(rectangles)
    collisions = qt.hit(Rect(25, 25, 10, 10))
    assert (0, 0, 50, 50) in collisions


def test_deep_tree_structure():
    rectangles = [Rect(i * 5, i * 5, 4, 4) for i in range(50)]
    qt = FastQuadTree(rectangles, depth=6)
    assert len(list(qt)) == 50


def test_iter_returns_all_items():
    rectangles = [Rect(i, i, 5, 5) for i in range(10)]
    qt = FastQuadTree(rectangles)
    all_items = list(qt)
    assert len(all_items) == len(rectangles)
    for r in rectangles:
        assert r in all_items
    rectangles = [Rect(i, i, 5, 5) for i in range(10)]
    qt = FastQuadTree(rectangles)
    all_items = list(qt)
    assert len(all_items) == len(rectangles)
    for r in rectangles:
        assert r in all_items


def test_large_depth_does_not_crash():
    rectangles = [Rect(i, i, 2, 2) for i in range(100)]
    qt = FastQuadTree(rectangles, depth=50)
    assert len(list(qt)) == 100


def test_hit_with_non_rect_object():
    class Dummy:
        def __init__(self, rect):
            self.rect = rect

    dummy = Dummy(Rect(0, 0, 10, 10))
    qt = FastQuadTree([dummy])
    collisions = qt.hit(Rect(0, 0, 10, 10))
    assert (0, 0, 10, 10) in collisions
