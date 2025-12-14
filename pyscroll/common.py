from __future__ import annotations

from contextlib import contextmanager
from typing import Union

from pygame.math import Vector2
from pygame.rect import Rect
from pygame.surface import Surface

RectLike = Union[Rect, tuple[int, int, int, int]]
Vector2D = Union[tuple[float, float], tuple[int, int], Vector2]
Vector2DInt = tuple[int, int]
Vector3DInt = tuple[int, int, int]


@contextmanager
def surface_clipping_context(surface: Surface, clip: RectLike):
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
