from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import BaseCamera

if TYPE_CHECKING:
    from pygame.rect import Rect


class PlatformerCamera(BaseCamera):
    def __init__(
        self,
        lerp_factor: float = 0.15,
        vertical_deadzone: int = 80,
    ) -> None:
        super().__init__(lerp_factor)
        self.vertical_deadzone: int = vertical_deadzone

    def update(
        self,
        current_view: Rect,
        target_rect: Rect,
        dt: float,
    ) -> tuple[float, float]:
        """
        A camera tuned for 2D platformers:
        - Horizontal smoothing always applies.
        - Vertical smoothing only applies when moving upward or leaving the deadzone.
        """
        cx: float
        cy: float
        tx: float
        ty: float

        cx, cy = current_view.center
        tx, ty = target_rect.center

        # Exponential smoothing
        t: float = 1.0 - math.pow(1.0 - self.lerp_factor, dt)

        # Horizontal follow always active
        new_x: float = cx + (tx - cx) * t

        # Vertical follow only when:
        # - target is above camera, OR
        # - target is outside vertical deadzone
        if ty < cy or abs(ty - cy) > self.vertical_deadzone:
            new_y: float = cy + (ty - cy) * t
        else:
            new_y = float(cy)

        return self._apply_shake(new_x, new_y)
