from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame.math import Vector2

from .base import BaseCamera

if TYPE_CHECKING:
    from pygame.rect import Rect


class SplitFollowCamera(BaseCamera):
    def __init__(
        self,
        lerp_factor: float = 0.1,
        zoom_speed: float = 2.0,
        min_zoom: float = 0.5,
        max_zoom: float = 2.0,
        max_distance: float = 400.0,
    ) -> None:
        super().__init__(lerp_factor)
        self.zoom_speed: float = zoom_speed
        self.min_zoom: float = min_zoom
        self.max_zoom: float = max_zoom
        self.max_distance: float = max_distance
        self.zoom: float = max_zoom
        self.targets: list[Rect] = []

    def _get_midpoint(self) -> Vector2:
        total: Vector2 = Vector2(0.0, 0.0)
        for r in self.targets:
            total += Vector2(r.center)
        return total / len(self.targets)

    def _get_max_separation(self) -> float:
        max_dist_sq: float = 0.0
        n: int = len(self.targets)

        for i in range(n):
            vi: Vector2 = Vector2(self.targets[i].center)
            for j in range(i + 1, n):
                vj: Vector2 = Vector2(self.targets[j].center)
                d: float = (vi - vj).length_squared()
                if d > max_dist_sq:
                    max_dist_sq = d

        return math.sqrt(max_dist_sq)

    def _target_zoom(self, sep: float) -> float:
        t: float = min(sep / self.max_distance, 1.0)
        return self.max_zoom - (self.max_zoom - self.min_zoom) * t

    def update(
        self,
        current_view: Rect,
        target_rect: Rect,
        dt: float,
    ) -> tuple[float, float]:
        cx: float
        cy: float
        cx, cy = current_view.center

        t: float = 1.0 - math.pow(1.0 - self.lerp_factor, dt)

        # Single-target or fallback mode
        if not self.targets or len(self.targets) == 1:
            target: Vector2 = Vector2(
                self.targets[0].center if self.targets else target_rect.center
            )
            new_pos: Vector2 = Vector2(cx, cy).lerp(target, min(1.0, t))
            return self._apply_shake(new_pos.x, new_pos.y)

        # Multi-target midpoint follow
        midpoint: Vector2 = self._get_midpoint()
        new_pos = Vector2(cx, cy).lerp(midpoint, min(1.0, t))

        # Dynamic zoom based on separation
        sep: float = self._get_max_separation()
        tz: float = self._target_zoom(sep)
        diff: float = tz - self.zoom

        self.zoom = max(
            self.min_zoom,
            min(self.max_zoom, self.zoom + diff * min(1.0, dt * self.zoom_speed)),
        )

        return self._apply_shake(new_pos.x, new_pos.y)
