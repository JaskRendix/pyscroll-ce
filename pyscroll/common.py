from __future__ import annotations

from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from typing import Any, TypeVar

from pygame.math import Vector2
from pygame.rect import Rect
from pygame.surface import Surface

RectLike = Rect | tuple[int, int, int, int]
Vector2D = tuple[float, float] | tuple[int, int] | Vector2


@contextmanager
def surface_clipping_context(
    surface: Surface, clip: RectLike
) -> Generator[None, Any, None]:
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


def rect_difference(a: RectLike, b: RectLike) -> list[Rect]:
    """
    Compute the difference of two rects (a - b).
    Returns up to 4 Rects representing the portions of `a` not overlapped by `b`.
    """
    ra = Rect(a) if not isinstance(a, Rect) else a
    rb = Rect(b) if not isinstance(b, Rect) else b

    inter = ra.clip(rb)
    if inter.width == 0 or inter.height == 0:
        return [ra]

    result: list[Rect] = []

    if inter.top > ra.top:
        result.append(Rect(ra.left, ra.top, ra.width, inter.top - ra.top))

    if inter.bottom < ra.bottom:
        result.append(Rect(ra.left, inter.bottom, ra.width, ra.bottom - inter.bottom))

    if inter.left > ra.left:
        result.append(Rect(ra.left, inter.top, inter.left - ra.left, inter.height))

    if inter.right < ra.right:
        result.append(
            Rect(inter.right, inter.top, ra.right - inter.right, inter.height)
        )

    return result


def rect_to_bb(rect: RectLike) -> tuple[int, int, int, int]:
    if isinstance(rect, Rect):
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
    else:
        x, y, w, h = rect
    return x, y, x + w - 1, y + h - 1


def vector3_to_iso(
    vector3: tuple[int, int, int], offset: tuple[int, int] = (0, 0)
) -> tuple[int, int]:
    """
    Convert 3D cartesian coordinates to isometric coordinates.
    """
    if not isinstance(vector3, tuple) or len(vector3) != 3:
        raise ValueError("Input tuple must have exactly 3 elements")
    return (
        (vector3[0] - vector3[1]) + offset[0],
        ((vector3[0] + vector3[1]) >> 1) - vector3[2] + offset[1],
    )


def vector2_to_iso(
    vector2: tuple[int, int], offset: tuple[int, int] = (0, 0)
) -> tuple[int, int]:
    """
    Convert 2D cartesian coordinates to isometric coordinates.
    """
    if not isinstance(vector2, tuple) or len(vector2) != 2:
        raise ValueError("Input tuple must have exactly 2 elements")
    return (
        (vector2[0] - vector2[1]) + offset[0],
        ((vector2[0] + vector2[1]) >> 1) + offset[1],
    )


T = TypeVar("T")


def rev(seq: Sequence[T], start: int, stop: int) -> Iterable[tuple[int, T]]:
    if start < 0:
        start = 0
    return enumerate(seq[start : stop + 1], start)
