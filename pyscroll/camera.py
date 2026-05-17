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
        self._shake_amount: float = 0.0

    def shake(self, intensity: float) -> None:
        self._shake_amount = min(self._shake_amount + intensity, 100.0)

    def _apply_shake(self, x: float, y: float) -> tuple[float, float]:
        """
        Apply screen shake to a position (x, y) and decay the shake amount.
        Public signature preserved for compatibility; uses Vector2 internally.
        """
        if self._shake_amount > 0.0:
            offset_x = random.uniform(-self._shake_amount, self._shake_amount)
            offset_y = random.uniform(-self._shake_amount, self._shake_amount)
            self._shake_amount = max(0.0, self._shake_amount - 1.0)
            pos = Vector2(x + offset_x, y + offset_y)
            return pos.x, pos.y
        return float(x), float(y)

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
        current_center = Vector2(current_view.center)
        target_center = Vector2(target_rect.center)

        if self.deadzone:
            # Re-center existing Rect to avoid allocations
            self.deadzone.center = current_view.center
            if self.deadzone.contains(target_rect):
                return self._apply_shake(current_center.x, current_center.y)

        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_pos = current_center.lerp(target_center, min(1.0, t))

        return self._apply_shake(new_pos.x, new_pos.y)


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

    def shake(self, intensity: float) -> None:
        # Forward shake to base; ZoomCamera itself never accumulates shake
        self.base.shake(intensity)

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        x, y = self.base.update(current_view, target_rect, dt)

        diff = self.target_zoom - self.zoom
        self.zoom = max(0.1, self.zoom + diff * min(1.0, dt * self.zoom_speed))

        # No extra shake here; base already applied it
        return float(x), float(y)


class CutsceneCamera(BaseCamera):
    """
    Moves along predefined waypoints for cutscenes.
    Supports linear and Catmull-Rom spline interpolation.
    """

    def __init__(
        self,
        waypoints: list[tuple[float, float] | Vector2],
        duration: float,
        loop: bool = False,
        on_complete: Callable[[], None] | None = None,
        interpolation: str = "linear",
    ) -> None:
        super().__init__(lerp_factor=1.0)
        if interpolation not in ("linear", "catmull_rom"):
            raise ValueError("interpolation must be 'linear' or 'catmull_rom'")

        # Store as Vector2 internally
        self.waypoints: list[Vector2] = [Vector2(wp) for wp in waypoints]
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
        Static API used by tests: tuple in, tuple out.
        Implemented via Vector2 internally.
        """
        v0 = Vector2(p0)
        v1 = Vector2(p1)
        v2 = Vector2(p2)
        v3 = Vector2(p3)

        t2 = t * t
        t3 = t2 * t
        res = 0.5 * (
            (2 * v1)
            + (-v0 + v2) * t
            + (2 * v0 - 5 * v1 + 4 * v2 - v3) * t2
            + (-v0 + 3 * v1 - 3 * v2 + v3) * t3
        )
        return res.x, res.y

    @staticmethod
    def _catmull_rom_vec(
        v0: Vector2, v1: Vector2, v2: Vector2, v3: Vector2, t: float
    ) -> Vector2:
        t2 = t * t
        t3 = t2 * t
        return 0.5 * (
            (2 * v1)
            + (-v0 + v2) * t
            + (2 * v0 - 5 * v1 + 4 * v2 - v3) * t2
            + (-v0 + 3 * v1 - 3 * v2 + v3) * t3
        )

    def _get_control_points(
        self, seg: int
    ) -> tuple[Vector2, Vector2, Vector2, Vector2]:
        n = len(self.waypoints)
        if self.loop:
            return (
                self.waypoints[(seg - 1) % n],
                self.waypoints[seg % n],
                self.waypoints[(seg + 1) % n],
                self.waypoints[(seg + 2) % n],
            )
        return (
            self.waypoints[max(seg - 1, 0)],
            self.waypoints[seg],
            self.waypoints[min(seg + 1, n - 1)],
            self.waypoints[min(seg + 2, n - 1)],
        )

    def _interpolate(self, seg: int, local_t: float) -> Vector2:
        if self.interpolation == "catmull_rom":
            v0, v1, v2, v3 = self._get_control_points(seg)
            return self._catmull_rom_vec(v0, v1, v2, v3, local_t)
        return self.waypoints[seg].lerp(self.waypoints[seg + 1], local_t)

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        if len(self.waypoints) == 1:
            wp = self.waypoints[0]
            return self._apply_shake(wp.x, wp.y)

        if self.time / self.duration >= 1.0 and not self.loop:
            if not self._completed and self.on_complete is not None:
                self._completed = True
                self.on_complete()
            wp = self.waypoints[-1]
            return self._apply_shake(wp.x, wp.y)

        self.time += dt
        t = min(self.time / self.duration, 1.0)

        if t >= 1.0:
            if self.loop:
                self.time -= self.duration
                t = self.time / self.duration
            else:
                if not self._completed and self.on_complete is not None:
                    self._completed = True
                    self.on_complete()
                wp = self.waypoints[-1]
                return self._apply_shake(wp.x, wp.y)

        seg_count = len(self.waypoints) - 1
        seg = min(int(t * seg_count), seg_count - 1)
        local_t = (t * seg_count) - seg

        pos = self._interpolate(seg, local_t)
        return self._apply_shake(pos.x, pos.y)

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

        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_x = cx + (tx - cx) * t

        # Upward always follows; downward only outside deadzone
        if ty < cy or abs(ty - cy) > self.vertical_deadzone:
            new_y = cy + (ty - cy) * t
        else:
            new_y = float(cy)

        return self._apply_shake(new_x, new_y)


class DebugFlyCamera(BaseCamera):
    def __init__(self, speed: float = 600.0):
        super().__init__(1.0)
        self.pos: Vector2 | None = None
        self.speed = speed
        self.move = Vector2(0.0, 0.0)

    def set_position(self, x: float, y: float) -> None:
        """Teleport the camera to a specific position."""
        self.pos = Vector2(x, y)

    def set_input(self, dx: float, dy: float) -> None:
        self.move.xy = Vector2(dx, dy)

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
        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        current = Vector2(current_view.center)
        target = Vector2(target_rect.center)
        new_pos = current.lerp(target, min(1.0, t))
        return self._apply_shake(new_pos.x, new_pos.y)


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

    def shake(self, intensity: float) -> None:
        # Forward shake to base; BoundsCamera itself never accumulates shake
        self.base.shake(intensity)

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        # Base camera handles movement and shake
        x, y = self.base.update(current_view, target_rect, dt)

        half_w = current_view.width // 2
        half_h = current_view.height // 2

        if self.clamp_shake:
            # If view larger than world, center; else clamp
            if current_view.width > self.world_rect.width:
                x = float(self.world_rect.centerx)
            else:
                x = max(
                    self.world_rect.left + half_w,
                    min(self.world_rect.right - half_w, x),
                )

            if current_view.height > self.world_rect.height:
                y = float(self.world_rect.centery)
            else:
                y = max(
                    self.world_rect.top + half_h,
                    min(self.world_rect.bottom - half_h, y),
                )

        return float(x), float(y)


class SplitFollowCamera(BaseCamera):
    """
    Follows the midpoint between multiple targets and zooms out
    as they move apart.
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

    def _get_midpoint(self) -> Vector2:
        total = Vector2(0.0, 0.0)
        for r in self.targets:
            total += Vector2(r.center)
        return total / len(self.targets)

    def _get_max_separation(self) -> float:
        max_dist_sq = 0.0
        targets = self.targets
        n = len(targets)
        for i in range(n):
            v_i = Vector2(targets[i].center)
            for j in range(i + 1, n):
                v_j = Vector2(targets[j].center)
                dist_sq = (v_i - v_j).length_squared()
                if dist_sq > max_dist_sq:
                    max_dist_sq = dist_sq
        return math.sqrt(max_dist_sq)

    def _target_zoom(self, separation: float) -> float:
        t = min(separation / self.max_distance, 1.0)
        return self.max_zoom - (self.max_zoom - self.min_zoom) * t

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        active_targets = self.targets if self.targets else None
        cx, cy = current_view.center
        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)

        if not active_targets or len(active_targets) == 1:
            target = Vector2(
                active_targets[0].center if active_targets else target_rect.center
            )
            new_pos = Vector2(cx, cy).lerp(target, min(1.0, t))
            return self._apply_shake(new_pos.x, new_pos.y)

        # multiple targets: follow midpoint, adjust zoom
        midpoint = self._get_midpoint()
        new_pos = Vector2(cx, cy).lerp(midpoint, min(1.0, t))

        separation = self._get_max_separation()
        target_zoom = self._target_zoom(separation)
        diff = target_zoom - self.zoom
        self.zoom = max(
            self.min_zoom,
            min(self.max_zoom, self.zoom + diff * min(1.0, dt * self.zoom_speed)),
        )

        return self._apply_shake(new_pos.x, new_pos.y)


class RailCamera(BaseCamera):
    """
    A camera constrained to move along a predefined rail (polyline).
    Finds the closest point on the rail to the target and lerps toward it.
    """

    def __init__(
        self,
        rail: list[tuple[float, float] | Vector2],
        lerp_factor: float = 0.1,
        loop: bool = False,
    ) -> None:
        if len(rail) < 2:
            raise ValueError("Rail must have at least 2 points.")
        super().__init__(lerp_factor)
        self.rail: list[Vector2] = [Vector2(pt) for pt in rail]
        self.loop = loop

    @staticmethod
    def _closest_point_on_segment(
        a: tuple[float, float],
        b: tuple[float, float],
        p: tuple[float, float],
    ) -> tuple[float, float]:
        """
        Static API used by tests: tuple in, tuple out.
        Implemented via Vector2 internally.
        """
        va = Vector2(a)
        vb = Vector2(b)
        vp = Vector2(p)

        ab = vb - va
        seg_len_sq = ab.length_squared()
        if seg_len_sq == 0.0:
            return va.x, va.y

        t = max(0.0, min(1.0, (vp - va).dot(ab) / seg_len_sq))
        res = va + t * ab
        return res.x, res.y

    @staticmethod
    def _closest_point_on_segment_vec(a: Vector2, b: Vector2, p: Vector2) -> Vector2:
        ab = b - a
        seg_len_sq = ab.length_squared()
        if seg_len_sq == 0.0:
            return a
        t = max(0.0, min(1.0, (p - a).dot(ab) / seg_len_sq))
        return a + t * ab

    def _closest_point_on_rail(self, target: Vector2) -> Vector2:
        best_point = self.rail[0]
        best_dist_sq = float("inf")

        segments = list(zip(self.rail, self.rail[1:]))
        if self.loop:
            segments.append((self.rail[-1], self.rail[0]))

        for a, b in segments:
            cp = self._closest_point_on_segment_vec(a, b, target)
            dist_sq = (cp - target).length_squared()
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_point = cp

        return best_point

    def update(
        self, current_view: Rect, target_rect: Rect, dt: float
    ) -> tuple[float, float]:
        cx, cy = current_view.center
        target = Vector2(target_rect.center)
        rail_target = self._closest_point_on_rail(target)

        t = 1.0 - math.pow(1.0 - self.lerp_factor, dt)
        new_pos = Vector2(cx, cy).lerp(rail_target, min(1.0, t))

        return self._apply_shake(new_pos.x, new_pos.y)
