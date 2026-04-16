from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pygame.rect import Rect

    from pyscroll.camera import BaseCamera


class CameraManager:
    def __init__(self, initial_camera: BaseCamera):
        self.current = initial_camera
        self.next_cam: BaseCamera | None = None
        self.transition_time: float = 0
        self.transition_duration: float = 0
        self._last_position: tuple[float, float] | None = None

    @property
    def current_position(self) -> tuple[float, float] | None:
        """Last known camera position. None until first update."""
        return self._last_position

    @property
    def is_transitioning(self) -> bool:
        """True if a camera transition is currently in progress."""
        return self.next_cam is not None

    def set_camera(self, cam: BaseCamera, duration: float = 0.0) -> None:
        if duration <= 0:
            self.current = cam
            self.next_cam = None
            self.transition_time = 0
            return

        self.next_cam = cam
        self.transition_duration = duration
        self.transition_time = 0

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        if not self.next_cam:
            pos = self.current.update(current_view, target_rect, dt)
            self._last_position = pos
            return pos

        # Both cameras update every frame so their internal state stays current
        pos_a = self.current.update(current_view, target_rect, dt)
        pos_b = self.next_cam.update(current_view, target_rect, dt)

        self.transition_time += dt
        t = min(self.transition_time / self.transition_duration, 1.0)
        t = t * t * (3 - 2 * t)  # smoothstep

        x = pos_a[0] + (pos_b[0] - pos_a[0]) * t
        y = pos_a[1] + (pos_b[1] - pos_a[1]) * t

        if t >= 1.0:
            self.current = self.next_cam
            self.next_cam = None

        pos = (x, y)
        self._last_position = pos
        return pos
