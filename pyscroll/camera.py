from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import Optional

from pygame.rect import Rect


class BaseCamera(ABC):
    """
    Abstract base class for all camera types.
    """

    def __init__(self, lerp_factor: float = 1.0, deadzone: Optional[Rect] = None):
        self.lerp_factor = lerp_factor
        self.deadzone = deadzone
        self._shake_amount = 0

    def shake(self, intensity: int) -> None:
        """Add screenshake intensity (decays automatically)."""
        self._shake_amount = intensity

    @abstractmethod
    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        """
        Calculate the next camera center position.
        Must be implemented by subclasses.
        """
        raise NotImplementedError


class Camera(BaseCamera):
    """
    A smooth-follow camera with optional deadzone and screen shake.
    """

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:

        current_center = current_view.center
        target_center = target_rect.center

        # Deadzone logic
        if self.deadzone:
            temp_dz = self.deadzone.copy()
            temp_dz.center = current_center

            if temp_dz.contains(target_rect):
                return current_center

        # Frame‑rate independent lerp
        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)

        new_x = current_center[0] + (target_center[0] - current_center[0]) * t
        new_y = current_center[1] + (target_center[1] - current_center[1]) * t

        # Screen shake
        if self._shake_amount > 0:
            new_x += random.uniform(-self._shake_amount, self._shake_amount)
            new_y += random.uniform(-self._shake_amount, self._shake_amount)
            self._shake_amount = max(0, self._shake_amount - 1)

        return (new_x, new_y)
