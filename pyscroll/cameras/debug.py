from __future__ import annotations

from typing import TYPE_CHECKING

from pygame.math import Vector2

from .base import BaseCamera

if TYPE_CHECKING:
    from pygame.rect import Rect


class DebugFlyCamera(BaseCamera):
    def __init__(self, speed: float = 600.0) -> None:
        super().__init__(1.0)
        self.pos: Vector2 | None = None
        self.speed: float = speed
        self.move: Vector2 = Vector2(0.0, 0.0)

    def set_position(self, x: float, y: float) -> None:
        """Teleport the camera to a specific position."""
        self.pos = Vector2(x, y)

    def set_input(self, dx: float, dy: float) -> None:
        """Set movement direction (normalized or raw)."""
        self.move.xy = Vector2(dx, dy)

    def update(
        self,
        current_view: Rect,
        target_rect: Rect,
        dt: float,
    ) -> tuple[float, float]:
        """
        Free‑fly camera controlled by directional input.

        Args:
            current_view: The current viewport rectangle.
            target_rect: Unused, but kept for API compatibility.
            dt: Delta time in seconds.

        Returns:
            A tuple (x, y) representing the new camera center.
        """
        if self.pos is None:
            self.pos = Vector2(current_view.center)

        self.pos += self.move * self.speed * dt

        return self._apply_shake(self.pos.x, self.pos.y)
