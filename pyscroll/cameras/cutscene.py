from __future__ import annotations

from typing import TYPE_CHECKING

from pygame.math import Vector2

from .base import BaseCamera

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from pygame.rect import Rect


class CutsceneCamera(BaseCamera):
    def __init__(
        self,
        waypoints: Iterable[tuple[float, float] | Vector2],
        duration: float,
        loop: bool = False,
        on_complete: Callable[[], None] | None = None,
        interpolation: str = "linear",
    ) -> None:
        super().__init__(1.0)

        if interpolation not in ("linear", "catmull_rom"):
            raise ValueError("interpolation must be 'linear' or 'catmull_rom'")

        self.waypoints: list[Vector2] = [Vector2(w) for w in waypoints]
        self.duration: float = duration
        self.loop: bool = loop
        self.time: float = 0.0
        self.on_complete: Callable[[], None] | None = on_complete
        self._completed: bool = False
        self.interpolation: str = interpolation

    @staticmethod
    def _catmull_rom(
        p0: tuple[float, float] | Vector2,
        p1: tuple[float, float] | Vector2,
        p2: tuple[float, float] | Vector2,
        p3: tuple[float, float] | Vector2,
        t: float,
    ) -> tuple[float, float]:
        v0, v1, v2, v3 = map(Vector2, (p0, p1, p2, p3))
        t2: float = t * t
        t3: float = t2 * t
        r: Vector2 = 0.5 * (
            (2 * v1)
            + (-v0 + v2) * t
            + (2 * v0 - 5 * v1 + 4 * v2 - v3) * t2
            + (-v0 + 3 * v1 - 3 * v2 + v3) * t3
        )
        return r.x, r.y

    @staticmethod
    def _catmull_rom_vec(
        v0: Vector2,
        v1: Vector2,
        v2: Vector2,
        v3: Vector2,
        t: float,
    ) -> Vector2:
        t2: float = t * t
        t3: float = t2 * t
        return 0.5 * (
            (2 * v1)
            + (-v0 + v2) * t
            + (2 * v0 - 5 * v1 + 4 * v2 - v3) * t2
            + (-v0 + 3 * v1 - 3 * v2 + v3) * t3
        )

    def _get_control_points(
        self,
        seg: int,
    ) -> tuple[Vector2, Vector2, Vector2, Vector2]:
        n: int = len(self.waypoints)
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
        self,
        current_view: Rect,
        target_rect: Rect,
        dt: float,
    ) -> tuple[float, float]:
        if len(self.waypoints) == 1:
            wp: Vector2 = self.waypoints[0]
            return self._apply_shake(wp.x, wp.y)

        # End of non-looping cutscene
        if self.time / self.duration >= 1.0 and not self.loop:
            if not self._completed and self.on_complete is not None:
                self._completed = True
                self.on_complete()
            wp = self.waypoints[-1]
            return self._apply_shake(wp.x, wp.y)

        # Advance time
        self.time += dt
        t: float = min(self.time / self.duration, 1.0)

        # Looping or final completion
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

        seg_count: int = len(self.waypoints) - 1
        seg: int = min(int(t * seg_count), seg_count - 1)
        local_t: float = (t * seg_count) - seg

        pos: Vector2 = self._interpolate(seg, local_t)
        return self._apply_shake(pos.x, pos.y)

    def reset(self) -> None:
        self.time = 0.0
        self._completed = False
