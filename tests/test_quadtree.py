import pytest
from pygame.rect import Rect
from pyscroll.quadtree import FastQuadTree


@pytest.mark.parametrize(
    "rectangles, query, expected_count",
    [
        (
            [Rect(0, 0, 10, 10), Rect(5, 5, 10, 10), Rect(10, 10, 10, 10)],
            Rect(2, 2, 12, 12),
            ">0",
        ),
        (
            [Rect(0, 0, 10, 10), Rect(20, 20, 10, 10), Rect(30, 30, 10, 10)],
            Rect(5, 5, 5, 5),
            1,
        ),
        ([Rect(0, 0, 10, 10)], Rect(0, 0, 10, 10), 1),
        ([Rect(0, 0, 10, 10), Rect(20, 20, 10, 10)], Rect(100, 100, 10, 10), 0),
    ],
)
def test_hit(rectangles, query, expected_count):
    qt = FastQuadTree(rectangles)
    collisions = qt.hit(query)
    if expected_count == ">0":
        assert len(collisions) > 0
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


def test_exact_match():
    target = Rect(10, 10, 10, 10)
    rectangles = [Rect(0, 0, 10, 10), target, Rect(20, 20, 10, 10)]
    qt = FastQuadTree(rectangles)
    collisions = qt.hit(target)
    assert tuple(target) in collisions


def test_boundary_collision():
    rectangles = [Rect(0, 0, 10, 10)]
    qt = FastQuadTree(rectangles)
    collisions = qt.hit(Rect(10, 0, 5, 5))
    assert len(collisions) == 0


def test_no_overlap_far_away():
    rectangles = [Rect(0, 0, 10, 10)]
    qt = FastQuadTree(rectangles)
    collisions = qt.hit(Rect(1000, 1000, 10, 10))
    assert collisions == set()


def test_multiple_hits():
    rectangles = [Rect(0, 0, 10, 10), Rect(5, 5, 10, 10), Rect(8, 8, 10, 10)]
    qt = FastQuadTree(rectangles)
    collisions = qt.hit(Rect(6, 6, 5, 5))
    assert len(collisions) >= 2


def test_iter_returns_all_items():
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
