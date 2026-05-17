from __future__ import annotations

from typing import TYPE_CHECKING

from pygame.math import Vector2

if TYPE_CHECKING:
    from pygame.rect import Rect

    from pyscroll.camera import BaseCamera


class CameraManager:
    """
    Manages active cameras and smooth transitions between them.
    """

    def __init__(self, initial_camera: BaseCamera):
        self.current = initial_camera
        self.next_cam: BaseCamera | None = None
        self.transition_time: float = 0.0
        self.transition_duration: float = 0.0
        self._last_position: tuple[float, float] | None = None

    @property
    def current_position(self) -> tuple[float, float] | None:
        return self._last_position

    @property
    def is_transitioning(self) -> bool:
        return self.next_cam is not None

    def set_camera(self, cam: BaseCamera, duration: float = 0.0) -> None:
        if duration <= 0.0:
            self.current = cam
            self.next_cam = None
            self.transition_time = 0.0
            return

        self.next_cam = cam
        self.transition_duration = duration
        self.transition_time = 0.0

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        if not self.next_cam:
            pos = self.current.update(current_view, target_rect, dt)
            self._last_position = pos
            return pos

        # Update both cameras to keep internal state in sync
        ax, ay = self.current.update(current_view, target_rect, dt)
        bx, by = self.next_cam.update(current_view, target_rect, dt)

        self.transition_time += dt
        t = min(self.transition_time / self.transition_duration, 1.0)

        # smoothstep
        t_smooth = t * t * (3.0 - 2.0 * t)

        # tuple interpolation is faster than Vector2.lerp on your system
        x = ax + (bx - ax) * t_smooth
        y = ay + (by - ay) * t_smooth

        if t >= 1.0:
            self.current = self.next_cam
            self.next_cam = None

        result = (x, y)
        self._last_position = result
        return result
