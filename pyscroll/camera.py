from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod

from pygame.math import Vector2
from pygame.rect import Rect


class BaseCamera(ABC):
    """
    Abstract base class for all camera types.
    """

    def __init__(self, lerp_factor: float = 1.0, deadzone: Rect | None = None):
        self.lerp_factor = lerp_factor
        self.deadzone = deadzone
        self._shake_amount = 0

    def shake(self, intensity: int) -> None:
        """Add screenshake intensity (decays automatically)."""
        self._shake_amount = intensity

    def _apply_shake(self, x: float, y: float) -> tuple[float, float]:
        if self._shake_amount > 0:
            x += random.uniform(-self._shake_amount, self._shake_amount)
            y += random.uniform(-self._shake_amount, self._shake_amount)
            self._shake_amount = max(0, self._shake_amount - 1)
        return x, y

    @abstractmethod
    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        """
        Calculate the next camera center position.
        Must be implemented by subclasses.
        """
        raise NotImplementedError


class FollowCamera(BaseCamera):
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

        new_x, new_y = self._apply_shake(new_x, new_y)
        return (new_x, new_y)


class ZoomCamera(BaseCamera):
    """
    Wraps another camera and adds smooth zooming.
    """

    def __init__(self, base: BaseCamera, zoom: float = 1.0, zoom_speed: float = 3.0):
        super().__init__(base.lerp_factor, base.deadzone)
        self.base = base
        self.zoom = zoom
        self.target_zoom = zoom
        self.zoom_speed = zoom_speed

    def set_zoom(self, new_zoom: float) -> None:
        self.target_zoom = max(0.1, new_zoom)

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        x, y = self.base.update(current_view, target_rect, dt)

        diff = self.target_zoom - self.zoom
        self.zoom += diff * min(1.0, dt * self.zoom_speed)

        x, y = self._apply_shake(x, y)
        return (x, y)


class CutsceneCamera(BaseCamera):
    """
    Moves along predefined waypoints for cutscenes.
    """

    def __init__(
        self, waypoints: list[tuple[float, float]], duration: float, loop: bool = False
    ):
        super().__init__(lerp_factor=1.0)
        self.waypoints = waypoints
        self.duration = duration
        self.loop = loop
        self.time = 0.0

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        if len(self.waypoints) == 1:
            return self.waypoints[0]

        self.time += dt
        t = self.time / self.duration

        if t >= 1.0:
            if self.loop:
                self.time = 0.0
                t = 0.0
            else:
                return self.waypoints[-1]

        seg_count = len(self.waypoints) - 1
        seg = min(int(t * seg_count), seg_count - 1)

        local_t = (t * seg_count) - seg

        x1, y1 = self.waypoints[seg]
        x2, y2 = self.waypoints[seg + 1]

        x = x1 + (x2 - x1) * local_t
        y = y1 + (y2 - y1) * local_t

        x, y = self._apply_shake(x, y)
        return (x, y)


class PlatformerCamera(BaseCamera):
    """
    A camera tuned for 2D platformers.
    """

    def __init__(self, lerp_factor: float = 0.15, vertical_deadzone: int = 80):
        super().__init__(lerp_factor)
        self.vertical_deadzone = vertical_deadzone

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        cx, cy = current_view.center
        tx, ty = target_rect.center

        # Horizontal follow (always)
        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_x = cx + (tx - cx) * t

        # Vertical follow only if outside deadzone
        if abs(ty - cy) > self.vertical_deadzone:
            new_y = cy + (ty - cy) * t
        else:
            new_y = cy

        new_x, new_y = self._apply_shake(new_x, new_y)
        return (new_x, new_y)


class DebugFlyCamera(BaseCamera):
    def __init__(self, speed: int = 600):
        super().__init__(1.0)
        self.pos = Vector2(400, 400)
        self.speed = speed
        self.move = Vector2(0, 0)

    def set_input(self, dx: float, dy: float) -> None:
        self.move.x = dx
        self.move.y = dy

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        self.pos += self.move * self.speed * dt
        new_x, new_y = self._apply_shake(self.pos.x, self.pos.y)
        return (new_x, new_y)


class BasicCamera(BaseCamera):
    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        cx, cy = current_view.center
        tx, ty = target_rect.center

        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_x = cx + (tx - cx) * t
        new_y = cy + (ty - cy) * t

        new_x, new_y = self._apply_shake(new_x, new_y)
        return (new_x, new_y)


class BoundsCamera(BaseCamera):
    """
    Wraps another camera and clamps the final camera center
    so it never leaves the world bounds.
    """

    def __init__(self, base: BaseCamera, world_rect: Rect):
        super().__init__(base.lerp_factor, base.deadzone)
        self.base = base
        self.world_rect = world_rect

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:

        x, y = self.base.update(current_view, target_rect, dt)

        half_w = current_view.width // 2
        half_h = current_view.height // 2

        min_x = self.world_rect.left + half_w
        max_x = self.world_rect.right - half_w
        min_y = self.world_rect.top + half_h
        max_y = self.world_rect.bottom - half_h

        clamped_x = max(min_x, min(max_x, x))
        clamped_y = max(min_y, min(max_y, y))

        clamped_x, clamped_y = self._apply_shake(clamped_x, clamped_y)
        return (clamped_x, clamped_y)
