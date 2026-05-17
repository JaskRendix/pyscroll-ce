from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame.math import Vector2

from .base import BaseCamera

if TYPE_CHECKING:
    from pygame.rect import Rect


class BasicCamera(BaseCamera):
    def update(
        self,
        current_view: Rect,
        target_rect: Rect,
        dt: float,
    ) -> tuple[float, float]:
        """
        Smoothly lerps the camera center toward the target center.

        Args:
            current_view: The current camera viewport rectangle.
            target_rect: The target object rectangle.
            dt: Delta time in seconds.

        Returns:
            A tuple (x, y) representing the new camera center.
        """
        t: float = 1.0 - math.pow(1.0 - self.lerp_factor, dt)

        current: Vector2 = Vector2(current_view.center)
        target: Vector2 = Vector2(target_rect.center)

        new_pos: Vector2 = current.lerp(target, min(1.0, t))

        return self._apply_shake(new_pos.x, new_pos.y)
