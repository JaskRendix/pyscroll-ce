from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import Optional

from pygame.rect import Rect


def get_rect(item) -> Rect:
    """Helper to consistently get a pygame.Rect from item."""
    return item.rect if hasattr(item, "rect") else item


class FastQuadTree:
    """
    High-performance quadtree tuned for pygame.Rect.
    - Stores rects only.
    - Uses collidelistall for fast collision checks.
    - Returns rect tuples (x, y, w, h).
    """

    __slots__ = ["items", "cx", "cy", "nw", "ne", "sw", "se", "boundary"]

    def __init__(
        self, items: Sequence[Rect], depth: int = 4, boundary: Optional[Rect] = None
    ) -> None:
        if not items:
            raise ValueError("Items must not be empty")

        rects = [get_rect(item) for item in items]
        boundary = Rect(boundary) if boundary else rects[0].unionall(rects[1:])

        self.cx, self.cy = boundary.centerx, boundary.centery
        self.boundary = boundary
        self.items: list[Rect] = []
        self.nw = self.ne = self.sw = self.se = None

        if depth <= 0:
            self.items = rects
            return

        nw_items, ne_items, se_items, sw_items = [], [], [], []
        for rect in rects:
            in_nw = rect.left <= self.cx and rect.top <= self.cy
            in_sw = rect.left <= self.cx and rect.bottom >= self.cy
            in_ne = rect.right >= self.cx and rect.top <= self.cy
            in_se = rect.right >= self.cx and rect.bottom >= self.cy

            if in_nw and in_ne and in_se and in_sw:
                self.items.append(rect)
            else:
                if in_nw:
                    nw_items.append(rect)
                if in_ne:
                    ne_items.append(rect)
                if in_se:
                    se_items.append(rect)
                if in_sw:
                    sw_items.append(rect)

        if nw_items:
            self.nw = FastQuadTree(
                nw_items, depth - 1, (boundary.left, boundary.top, self.cx, self.cy)
            )
        if ne_items:
            self.ne = FastQuadTree(
                ne_items, depth - 1, (self.cx, boundary.top, boundary.right, self.cy)
            )
        if se_items:
            self.se = FastQuadTree(
                se_items, depth - 1, (self.cx, self.cy, boundary.right, boundary.bottom)
            )
        if sw_items:
            self.sw = FastQuadTree(
                sw_items, depth - 1, (boundary.left, self.cy, self.cx, boundary.bottom)
            )

    def __iter__(self):
        return itertools.chain(
            self.items, self.nw or [], self.ne or [], self.se or [], self.sw or []
        )

    def hit(self, rect: Rect) -> set[tuple[int, int, int, int]]:
        """
        Return the rect tuples that overlap with the given rect.
        """
        if not isinstance(rect, Rect):
            rect = get_rect(rect)
        if not self.boundary.colliderect(rect):
            return set()

        # Fast C-optimized collision check
        hits = {tuple(self.items[i]) for i in rect.collidelistall(self.items)}

        if rect.left <= self.cx:
            if rect.top <= self.cy and self.nw:
                hits |= self.nw.hit(rect)
            if rect.bottom >= self.cy and self.sw:
                hits |= self.sw.hit(rect)
        if rect.right >= self.cx:
            if rect.top <= self.cy and self.ne:
                hits |= self.ne.hit(rect)
            if rect.bottom >= self.cy and self.se:
                hits |= self.se.hit(rect)

        return hits
