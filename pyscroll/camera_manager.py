from __future__ import annotations

from pygame.rect import Rect

from pyscroll.camera import BaseCamera


class CameraManager:
    def __init__(self, initial_camera: BaseCamera):
        self.current = initial_camera
        self.next_cam: BaseCamera | None = None
        self.transition_time: float = 0
        self.transition_duration: float = 0
        self.start_pos: tuple[float, float] | None = None

    def set_camera(self, cam: BaseCamera, duration: float = 0.0) -> None:
        if duration <= 0:
            self.current = cam
            self.next_cam = None
            return

        self.next_cam = cam
        self.transition_duration = duration
        self.transition_time = 0
        self.start_pos = None

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        if not self.next_cam:
            return self.current.update(current_view, target_rect, dt)

        if self.start_pos is None:
            self.start_pos = self.current.update(current_view, target_rect, dt)

        pos_a = self.start_pos
        pos_b = self.next_cam.update(current_view, target_rect, dt)

        self.transition_time += dt
        t = min(self.transition_time / self.transition_duration, 1.0)
        t = t * t * (3 - 2 * t)

        x = pos_a[0] + (pos_b[0] - pos_a[0]) * t
        y = pos_a[1] + (pos_b[1] - pos_a[1]) * t

        if t >= 1.0:
            self.current = self.next_cam
            self.next_cam = None

        return (x, y)
