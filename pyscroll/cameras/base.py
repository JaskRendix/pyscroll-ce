from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pygame.math import Vector2

if TYPE_CHECKING:
    from pygame.rect import Rect


class BaseCamera(ABC):
    def __init__(self, lerp_factor: float = 1.0, deadzone: Rect | None = None):
        self.lerp_factor = lerp_factor
        self.deadzone = deadzone
        self._shake_amount: float = 0.0

    def shake(self, intensity: float) -> None:
        self._shake_amount = min(self._shake_amount + intensity, 100.0)

    def _apply_shake(self, x: float, y: float) -> tuple[float, float]:
        if self._shake_amount > 0.0:
            ox = random.uniform(-self._shake_amount, self._shake_amount)
            oy = random.uniform(-self._shake_amount, self._shake_amount)
            self._shake_amount = max(0.0, self._shake_amount - 1.0)
            v = Vector2(x + ox, y + oy)
            return v.x, v.y
        return float(x), float(y)

    @abstractmethod
    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        raise NotImplementedError
