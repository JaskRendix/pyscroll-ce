from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseCamera

if TYPE_CHECKING:
    from pygame.rect import Rect

    from pyscroll.cameras.base import BaseCamera as _BaseCamera


class ZoomCamera(BaseCamera):
    def __init__(
        self,
        base: _BaseCamera,
        zoom: float = 1.0,
        zoom_speed: float = 3.0,
    ) -> None:
        super().__init__(base.lerp_factor, base.deadzone)
        self.base: _BaseCamera = base
        self.zoom: float = zoom
        self.target_zoom: float = zoom
        self.zoom_speed: float = zoom_speed

    def set_zoom(self, new_zoom: float) -> None:
        """Set a new zoom target, clamped to a minimum of 0.1."""
        self.target_zoom = max(0.1, new_zoom)

    def shake(self, intensity: float) -> None:
        """Forward shake to the underlying base camera."""
        self.base.shake(intensity)

    def update(
        self,
        current_view: Rect,
        target_rect: Rect,
        dt: float,
    ) -> tuple[float, float]:
        """
        Update zoom smoothly while delegating position to the base camera.

        Args:
            current_view: The current viewport rectangle.
            target_rect: The target object rectangle.
            dt: Delta time in seconds.

        Returns:
            A tuple (x, y) representing the camera center.
        """
        x, y = self.base.update(current_view, target_rect, dt)

        diff: float = self.target_zoom - self.zoom
        self.zoom = max(
            0.1,
            self.zoom + diff * min(1.0, dt * self.zoom_speed),
        )

        return float(x), float(y)
