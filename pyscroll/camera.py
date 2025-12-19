from __future__ import annotations

import math
import random
from typing import Optional

from pygame.rect import Rect


class Camera:
    def __init__(self, lerp_factor: float = 1.0, deadzone: Optional[Rect] = None):
        self.lerp_factor = lerp_factor
        self.deadzone = deadzone
        self._shake_amount = 0

    def shake(self, intensity: int) -> None:
        """Add screenshake intensity (decays automatically)."""
        self._shake_amount = intensity

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        """
        Calculates the next center position for the camera.
        """
        current_center = current_view.center
        target_center = target_rect.center

        if self.deadzone:
            # Move deadzone to current camera position
            temp_dz = self.deadzone.copy()
            temp_dz.center = current_center

            # If the target (Hero) is still inside the deadzone, don't move
            if temp_dz.contains(target_rect):
                return current_center

        # Frame-rate independent Lerp math
        # Use target_center to find the direction and distance to move
        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)

        new_x = current_center[0] + (target_center[0] - current_center[0]) * t
        new_y = current_center[1] + (target_center[1] - current_center[1]) * t

        # Apply screen shake if active
        if self._shake_amount > 0:
            new_x += random.uniform(-self._shake_amount, self._shake_amount)
            new_y += random.uniform(-self._shake_amount, self._shake_amount)
            self._shake_amount = max(0, self._shake_amount - 1)

        return (new_x, new_y)
