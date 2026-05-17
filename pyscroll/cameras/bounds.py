from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseCamera

if TYPE_CHECKING:
    from pygame.rect import Rect

    from pyscroll.cameras.base import BaseCamera as _BaseCamera


class BoundsCamera(BaseCamera):
    def __init__(
        self,
        base: _BaseCamera,
        world_rect: Rect,
        clamp_shake: bool = True,
    ) -> None:
        super().__init__(base.lerp_factor, base.deadzone)
        self.base: _BaseCamera = base
        self.world_rect: Rect = world_rect
        self.clamp_shake: bool = clamp_shake

    def shake(self, intensity: float) -> None:
        self.base.shake(intensity)

    def update(
        self,
        current_view: Rect,
        target_rect: Rect,
        dt: float,
    ) -> tuple[float, float]:
        """
        Clamp the camera center so it never leaves the world bounds.

        Args:
            current_view: The current camera viewport rectangle.
            target_rect: The target object rectangle.
            dt: Delta time in seconds.

        Returns:
            A tuple (x, y) representing the clamped camera center.
        """
        x, y = self.base.update(current_view, target_rect, dt)

        half_w: int = current_view.width // 2
        half_h: int = current_view.height // 2

        if self.clamp_shake:
            # Horizontal clamp
            if current_view.width > self.world_rect.width:
                x = float(self.world_rect.centerx)
            else:
                x = max(
                    self.world_rect.left + half_w,
                    min(self.world_rect.right - half_w, x),
                )

            # Vertical clamp
            if current_view.height > self.world_rect.height:
                y = float(self.world_rect.centery)
            else:
                y = max(
                    self.world_rect.top + half_h,
                    min(self.world_rect.bottom - half_h, y),
                )

        return float(x), float(y)
