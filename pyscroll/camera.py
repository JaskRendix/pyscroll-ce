from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pygame.math import Vector2

if TYPE_CHECKING:
    from collections.abc import Callable

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
        self._shake_amount = min(self._shake_amount + intensity, 100)

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

        if self.deadzone:
            temp_dz = self.deadzone.copy()
            temp_dz.center = current_center
            if temp_dz.contains(target_rect):
                return self._apply_shake(
                    float(current_center[0]), float(current_center[1])
                )

        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_x = current_center[0] + (target_center[0] - current_center[0]) * t
        new_y = current_center[1] + (target_center[1] - current_center[1]) * t

        return self._apply_shake(new_x, new_y)


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

    def shake(self, intensity: int) -> None:
        self.base.shake(intensity)

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        x, y = self.base.update(current_view, target_rect, dt)

        diff = self.target_zoom - self.zoom
        self.zoom = max(0.1, self.zoom + diff * min(1.0, dt * self.zoom_speed))

        # ZoomCamera has no movement of its own, so no shake here
        # shake should be set on the base camera, not on ZoomCamera
        return (x, y)


class CutsceneCamera(BaseCamera):
    """
    Moves along predefined waypoints for cutscenes.
    Supports linear and Catmull-Rom spline interpolation.
    """

    def __init__(
        self,
        waypoints: list[tuple[float, float]],
        duration: float,
        loop: bool = False,
        on_complete: Callable[[], None] | None = None,
        interpolation: str = "linear",
    ) -> None:
        super().__init__(lerp_factor=1.0)
        if interpolation not in ("linear", "catmull_rom"):
            raise ValueError("interpolation must be 'linear' or 'catmull_rom'")
        self.waypoints = waypoints
        self.duration = duration
        self.loop = loop
        self.time = 0.0
        self.on_complete = on_complete
        self._completed = False
        self.interpolation = interpolation

    @staticmethod
    def _catmull_rom(
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        t: float,
    ) -> tuple[float, float]:
        """
        Compute a point on a Catmull-Rom spline between p1 and p2.
        p0 and p3 are the neighbouring control points.
        t is in [0, 1].
        """
        t2 = t * t
        t3 = t2 * t

        def _component(c0: float, c1: float, c2: float, c3: float) -> float:
            return 0.5 * (
                (2 * c1)
                + (-c0 + c2) * t
                + (2 * c0 - 5 * c1 + 4 * c2 - c3) * t2
                + (-c0 + 3 * c1 - 3 * c2 + c3) * t3
            )

        return (
            _component(p0[0], p1[0], p2[0], p3[0]),
            _component(p0[1], p1[1], p2[1], p3[1]),
        )

    def _get_control_points(
        self, seg: int
    ) -> tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]:
        """
        Return (p0, p1, p2, p3) for segment `seg`.
        Clamps for non-looping, wraps for looping.
        """
        n = len(self.waypoints)
        if self.loop:
            p0 = self.waypoints[(seg - 1) % n]
            p1 = self.waypoints[seg % n]
            p2 = self.waypoints[(seg + 1) % n]
            p3 = self.waypoints[(seg + 2) % n]
        else:
            p0 = self.waypoints[max(seg - 1, 0)]
            p1 = self.waypoints[seg]
            p2 = self.waypoints[min(seg + 1, n - 1)]
            p3 = self.waypoints[min(seg + 2, n - 1)]
        return p0, p1, p2, p3

    def _interpolate(self, seg: int, local_t: float) -> tuple[float, float]:
        if self.interpolation == "catmull_rom":
            p0, p1, p2, p3 = self._get_control_points(seg)
            return self._catmull_rom(p0, p1, p2, p3, local_t)
        else:
            x1, y1 = self.waypoints[seg]
            x2, y2 = self.waypoints[seg + 1]
            return x1 + (x2 - x1) * local_t, y1 + (y2 - y1) * local_t

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        if len(self.waypoints) == 1:
            return self._apply_shake(
                float(self.waypoints[0][0]), float(self.waypoints[0][1])
            )

        if self.time / self.duration >= 1.0 and not self.loop:
            if not self._completed and self.on_complete is not None:
                self._completed = True
                self.on_complete()
            wp = self.waypoints[-1]
            return self._apply_shake(float(wp[0]), float(wp[1]))

        self.time += dt
        t = min(self.time / self.duration, 1.0)

        if t >= 1.0:
            if self.loop:
                self.time = self.time - self.duration
                t = self.time / self.duration
            else:
                if not self._completed and self.on_complete is not None:
                    self._completed = True
                    self.on_complete()
                wp = self.waypoints[-1]
                return self._apply_shake(float(wp[0]), float(wp[1]))

        seg_count = len(self.waypoints) - 1
        seg = min(int(t * seg_count), seg_count - 1)
        local_t = (t * seg_count) - seg

        x, y = self._interpolate(seg, local_t)
        return self._apply_shake(x, y)

    def reset(self) -> None:
        self.time = 0.0
        self._completed = False


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
        if ty < cy:
            # target is above — always follow immediately
            new_y = cy + (ty - cy) * t
        else:
            # target is below — only follow if outside deadzone
            new_y = cy + (ty - cy) * t if abs(ty - cy) > self.vertical_deadzone else cy

        new_x, new_y = self._apply_shake(new_x, new_y)
        return (new_x, new_y)


class DebugFlyCamera(BaseCamera):
    def __init__(self, speed: int = 600):
        super().__init__(1.0)
        self.pos: Vector2 | None = None
        self.speed = speed
        self.move = Vector2(0, 0)

    def set_position(self, x: float, y: float) -> None:
        """Teleport the camera to a specific position."""
        self.pos = Vector2(x, y)

    def set_input(self, dx: float, dy: float) -> None:
        self.move.x = dx
        self.move.y = dy

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        if self.pos is None:
            self.pos = Vector2(current_view.center)

        self.pos += self.move * self.speed * dt
        return self._apply_shake(self.pos.x, self.pos.y)


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

    def __init__(self, base: BaseCamera, world_rect: Rect, clamp_shake: bool = True):
        super().__init__(base.lerp_factor, base.deadzone)
        self.base = base
        self.world_rect = world_rect
        self.clamp_shake = clamp_shake

    def shake(self, intensity: int) -> None:
        self.base.shake(intensity)

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        x, y = self.base.update(current_view, target_rect, dt)
        x, y = self._apply_shake(x, y)

        half_w = current_view.width // 2
        half_h = current_view.height // 2

        min_x = self.world_rect.left + half_w
        max_x = self.world_rect.right - half_w
        min_y = self.world_rect.top + half_h
        max_y = self.world_rect.bottom - half_h

        if self.clamp_shake:
            # if world is narrower than view, center it instead of pinning to edge
            if max_x >= min_x:
                x = max(min_x, min(max_x, x))
            else:
                x = float(self.world_rect.centerx)

            if max_y >= min_y:
                y = max(min_y, min(max_y, y))
            else:
                y = float(self.world_rect.centery)

        return (x, y)


class SplitFollowCamera(BaseCamera):
    """
    Follows the midpoint between multiple targets and zooms out
    as they move apart.

    Targets are set via the `targets` list. Falls back to
    `target_rect` in update() if no targets are set.
    """

    def __init__(
        self,
        lerp_factor: float = 0.1,
        zoom_speed: float = 2.0,
        min_zoom: float = 0.5,
        max_zoom: float = 2.0,
        max_distance: float = 400.0,
    ) -> None:
        super().__init__(lerp_factor)
        self.zoom_speed = zoom_speed
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.max_distance = max_distance
        self.zoom: float = max_zoom
        self.targets: list[Rect] = []

    def _get_midpoint(self) -> tuple[int, int]:
        """Return the midpoint of all targets."""
        tx = sum(r.centerx for r in self.targets) / len(self.targets)
        ty = sum(r.centery for r in self.targets) / len(self.targets)
        return int(tx), int(ty)

    def _get_max_separation(self) -> float:
        """Return the maximum distance between any two targets."""
        max_dist = 0.0
        targets = self.targets
        for i in range(len(targets)):
            for j in range(i + 1, len(targets)):
                dx = targets[i].centerx - targets[j].centerx
                dy = targets[i].centery - targets[j].centery
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > max_dist:
                    max_dist = dist
        return max_dist

    def _target_zoom(self, separation: float) -> float:
        """Map separation distance to a zoom level."""
        t = min(separation / self.max_distance, 1.0)
        return self.max_zoom - (self.max_zoom - self.min_zoom) * t

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        active_targets = self.targets if self.targets else None

        if not active_targets:
            # fallback: behave like a basic follow camera
            cx, cy = current_view.center
            tx, ty = target_rect.center
            t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
            new_x = cx + (tx - cx) * t
            new_y = cy + (ty - cy) * t
            return self._apply_shake(new_x, new_y)

        if len(active_targets) == 1:
            # single target: follow without zoom adjustment
            cx, cy = current_view.center
            tx, ty = active_targets[0].center
            t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
            new_x = cx + (tx - cx) * t
            new_y = cy + (ty - cy) * t
            return self._apply_shake(new_x, new_y)

        # multiple targets: follow midpoint, adjust zoom
        cx, cy = current_view.center
        tx, ty = self._get_midpoint()

        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_x = cx + (tx - cx) * t
        new_y = cy + (ty - cy) * t

        separation = self._get_max_separation()
        target_zoom = self._target_zoom(separation)
        diff = target_zoom - self.zoom
        self.zoom = max(
            self.min_zoom,
            min(self.max_zoom, self.zoom + diff * min(1.0, dt * self.zoom_speed)),
        )

        return self._apply_shake(new_x, new_y)


class RailCamera(BaseCamera):
    """
    A camera constrained to move along a predefined rail (polyline).
    Finds the closest point on the rail to the target and lerps toward it.
    """

    def __init__(
        self,
        rail: list[tuple[float, float]],
        lerp_factor: float = 0.1,
        loop: bool = False,
    ) -> None:
        if len(rail) < 2:
            raise ValueError("Rail must have at least 2 points.")
        super().__init__(lerp_factor)
        self.rail = rail
        self.loop = loop

    @staticmethod
    def _closest_point_on_segment(
        a: tuple[float, float],
        b: tuple[float, float],
        p: tuple[float, float],
    ) -> tuple[float, float]:
        """Return the closest point on segment (a, b) to point p."""
        ax, ay = a
        bx, by = b
        px, py = p

        dx, dy = bx - ax, by - ay
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq == 0.0:
            return a  # degenerate segment, a == b

        t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
        t = max(0.0, min(1.0, t))

        return (ax + t * dx, ay + t * dy)

    def _closest_point_on_rail(
        self, target: tuple[float, float]
    ) -> tuple[float, float]:
        """Return the closest point on the entire rail to target."""
        best_point = self.rail[0]
        best_dist_sq = float("inf")

        segments = list(zip(self.rail, self.rail[1:]))
        if self.loop:
            segments.append((self.rail[-1], self.rail[0]))

        for a, b in segments:
            cp = self._closest_point_on_segment(a, b, target)
            dx = cp[0] - target[0]
            dy = cp[1] - target[1]
            dist_sq = dx * dx + dy * dy
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_point = cp

        return best_point

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        cx, cy = current_view.center
        tx, ty = target_rect.center

        rx, ry = self._closest_point_on_rail((tx, ty))

        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_x = cx + (rx - cx) * t
        new_y = cy + (ry - cy) * t

        return self._apply_shake(new_x, new_y)
