from __future__ import annotations

from typing import TYPE_CHECKING

from pygame.rect import Rect

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


def get_rect(item: Rect | object) -> Rect:
    """Return a pygame.Rect from a Rect or an object with a Rect .rect attribute."""
    if isinstance(item, Rect):
        return item
    if hasattr(item, "rect"):
        r = item.rect
        if isinstance(r, Rect):
            return r
    raise TypeError("Item must be a Rect or have a .rect attribute of type Rect")


class FastQuadTree:
    """
    High-performance quadtree tuned for pygame.Rect.

    - Stores Rect instances only.
    - Uses rect.collidelistall for fast C-accelerated collision checks.
    - hit() returns hashable rect tuples (x, y, w, h).
    """

    __slots__ = ["items", "cx", "cy", "nw", "ne", "sw", "se", "boundary"]

    def __init__(
        self, items: Sequence[Rect], depth: int = 4, boundary: Rect | None = None
    ) -> None:
        if not items:
            raise ValueError("Items must not be empty")

        rects = [get_rect(item) for item in items]
        self.boundary = Rect(boundary) if boundary else rects[0].unionall(rects[1:])

        self.cx = self.boundary.centerx
        self.cy = self.boundary.centery

        self.items: list[Rect] = []
        self.nw: FastQuadTree | None = None
        self.ne: FastQuadTree | None = None
        self.sw: FastQuadTree | None = None
        self.se: FastQuadTree | None = None

        # bucket cutoff: avoid over-splitting small sets
        if depth <= 0 or len(rects) <= 8:
            self.items = rects
            return

        bl = self.boundary.left
        bt = self.boundary.top
        br = self.boundary.right
        bb = self.boundary.bottom
        cx, cy = self.cx, self.cy

        nw_items: list[Rect] = []
        ne_items: list[Rect] = []
        se_items: list[Rect] = []
        sw_items: list[Rect] = []

        for rect in rects:
            rl, rt, rr, rb = rect.left, rect.top, rect.right, rect.bottom

            # Rect must fit entirely inside a child to go there
            in_nw = rr <= cx and rb <= cy
            in_ne = rl >= cx and rb <= cy
            in_sw = rr <= cx and rt >= cy
            in_se = rl >= cx and rt >= cy

            if in_nw:
                nw_items.append(rect)
            elif in_ne:
                ne_items.append(rect)
            elif in_sw:
                sw_items.append(rect)
            elif in_se:
                se_items.append(rect)
            else:
                # Overlaps split lines → stays in this node
                self.items.append(rect)

        if nw_items:
            self.nw = FastQuadTree(
                nw_items,
                depth - 1,
                Rect(bl, bt, cx - bl, cy - bt),
            )
        if ne_items:
            self.ne = FastQuadTree(
                ne_items,
                depth - 1,
                Rect(cx, bt, br - cx, cy - bt),
            )
        if se_items:
            self.se = FastQuadTree(
                se_items,
                depth - 1,
                Rect(cx, cy, br - cx, bb - cy),
            )
        if sw_items:
            self.sw = FastQuadTree(
                sw_items,
                depth - 1,
                Rect(bl, cy, cx - bl, bb - cy),
            )

    def __iter__(self) -> Iterator[Rect]:
        """Depth-first iteration over all stored Rects."""
        yield from self.items
        if self.nw:
            yield from self.nw
        if self.ne:
            yield from self.ne
        if self.se:
            yield from self.se
        if self.sw:
            yield from self.sw

    def hit(self, rect: Rect | object) -> set[tuple[int, int, int, int]]:
        """
        Return the rect tuples (x, y, w, h) that overlap with the given query rect.
        """
        if not isinstance(rect, Rect):
            rect = get_rect(rect)

        if not self.boundary.colliderect(rect):
            return set()

        items = self.items
        hits = {
            (r.x, r.y, r.w, r.h) for i in rect.collidelistall(items) if (r := items[i])
        }

        rl, rt, rr, rb = rect.left, rect.top, rect.right, rect.bottom
        cx, cy = self.cx, self.cy

        # Region pruning: decide which children can possibly intersect
        if rr <= cx:
            # Entirely on the left side
            if rb <= cy and self.nw:
                hits |= self.nw.hit(rect)
            elif rt >= cy and self.sw:
                hits |= self.sw.hit(rect)
            else:
                if self.nw:
                    hits |= self.nw.hit(rect)
                if self.sw:
                    hits |= self.sw.hit(rect)
        elif rl >= cx:
            # Entirely on the right side
            if rb <= cy and self.ne:
                hits |= self.ne.hit(rect)
            elif rt >= cy and self.se:
                hits |= self.se.hit(rect)
            else:
                if self.ne:
                    hits |= self.ne.hit(rect)
                if self.se:
                    hits |= self.se.hit(rect)
        else:
            # Spans across the vertical split → may touch both sides
            if self.nw and rt <= cy:
                hits |= self.nw.hit(rect)
            if self.sw and rb >= cy:
                hits |= self.sw.hit(rect)
            if self.ne and rt <= cy:
                hits |= self.ne.hit(rect)
            if self.se and rb >= cy:
                hits |= self.se.hit(rect)

        return hits
