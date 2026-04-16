from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Rect

if TYPE_CHECKING:
    from pyscroll.common import RectLike, Vector2D
    from pyscroll.viewport import ViewportBase


class ViewportPipeline:
    """Pure viewport math and coordinate transforms.

    BufferedRenderer delegates all viewport-related calculations here.
    """

    def __init__(self, viewport: ViewportBase):
        self.viewport = viewport

    def compute_offset(self, rect: Rect) -> tuple[int, int]:
        """Return (ox, oy) for blitting the buffer into target rect."""
        vx = self.viewport.x_offset
        vy = self.viewport.y_offset
        return (-vx + rect.left, -vy + rect.top)

    def expanded_tile_view(self, overdraw: tuple[int, int]) -> Rect:
        """Return tile_view expanded by tile overdraw."""
        tv = self.viewport.tile_view
        ox, oy = overdraw
        if ox == 0 and oy == 0:
            return tv
        return Rect(tv.x - ox, tv.y - oy, tv.width + ox * 2, tv.height + oy * 2)

    def translate_point(self, point: Vector2D) -> tuple[int, int]:
        return self.viewport.translate_point(point)

    def translate_rect(self, rect: RectLike) -> Rect:
        return self.viewport.translate_rect(rect)

    def translate_points(self, points: list[Vector2D]) -> list[tuple[int, int]]:
        return self.viewport.translate_points(points)

    def translate_rects(self, rects: list[Rect]) -> list[Rect]:
        return self.viewport.translate_rects(rects)
