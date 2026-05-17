from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame.math import Vector2

from .base import BaseCamera

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pygame.rect import Rect


class RailCamera(BaseCamera):
    def __init__(
        self,
        rail: Iterable[tuple[float, float] | Vector2],
        lerp_factor: float = 0.1,
        loop: bool = False,
    ) -> None:
        if len(list(rail)) < 2:
            raise ValueError("Rail must have at least 2 points.")

        super().__init__(lerp_factor)
        self.rail: list[Vector2] = [Vector2(p) for p in rail]
        self.loop: bool = loop

    @staticmethod
    def _closest_point_on_segment(
        a: tuple[float, float] | Vector2,
        b: tuple[float, float] | Vector2,
        p: tuple[float, float] | Vector2,
    ) -> tuple[float, float]:
        va: Vector2 = Vector2(a)
        vb: Vector2 = Vector2(b)
        vp: Vector2 = Vector2(p)

        ab: Vector2 = vb - va
        l2: float = ab.length_squared()
        if l2 == 0.0:
            return va.x, va.y

        t: float = max(0.0, min(1.0, (vp - va).dot(ab) / l2))
        r: Vector2 = va + t * ab
        return r.x, r.y

    @staticmethod
    def _closest_point_on_segment_vec(
        a: Vector2,
        b: Vector2,
        p: Vector2,
    ) -> Vector2:
        ab: Vector2 = b - a
        l2: float = ab.length_squared()
        if l2 == 0.0:
            return a

        t: float = max(0.0, min(1.0, (p - a).dot(ab) / l2))
        return a + t * ab

    def _closest_point_on_rail(self, target: Vector2) -> Vector2:
        best: Vector2 = self.rail[0]
        best_d: float = float("inf")

        segments: list[tuple[Vector2, Vector2]] = list(zip(self.rail, self.rail[1:]))
        if self.loop:
            segments.append((self.rail[-1], self.rail[0]))

        for a, b in segments:
            cp: Vector2 = self._closest_point_on_segment_vec(a, b, target)
            d: float = (cp - target).length_squared()
            if d < best_d:
                best_d = d
                best = cp

        return best

    def update(
        self,
        current_view: Rect,
        target_rect: Rect,
        dt: float,
    ) -> tuple[float, float]:
        cx: float
        cy: float
        cx, cy = current_view.center

        target: Vector2 = Vector2(target_rect.center)
        rail_target: Vector2 = self._closest_point_on_rail(target)

        t: float = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_pos: Vector2 = Vector2(cx, cy).lerp(rail_target, min(1.0, t))

        return self._apply_shake(new_pos.x, new_pos.y)
