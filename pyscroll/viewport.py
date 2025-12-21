from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pygame.rect import Rect

from pyscroll.common import RectLike, Vector2D, vector2_to_iso

if TYPE_CHECKING:
    from pyscroll.data import PyscrollDataAdapter

log = logging.getLogger(__file__)


class ViewportBase(ABC):
    """
    Abstract camera/viewport interface.

    Implementations must handle:
    - Map/view/tile rectangles
    - Centering and scrolling
    - Coordinate translation (world -> screen)
    """

    data: PyscrollDataAdapter
    map_rect: Rect
    view_rect: Rect
    _tile_view: Rect

    _x_offset: int
    _y_offset: int
    _anchored_view: bool

    @property
    def tile_view(self) -> Rect:
        return self._tile_view

    @property
    def x_offset(self) -> int:
        return self._x_offset

    @property
    def y_offset(self) -> int:
        return self._y_offset

    @property
    def anchored_view(self) -> bool:
        return self._anchored_view

    @property
    @abstractmethod
    def zoom(self) -> float: ...

    @zoom.setter
    @abstractmethod
    def zoom(self, value: float) -> None: ...

    @property
    @abstractmethod
    def size(self) -> tuple[int, int]: ...

    @abstractmethod
    def set_size(self, size: tuple[int, int]) -> tuple[int, int]:
        """Return buffer_pixel_size"""
        ...

    @abstractmethod
    def center(self, coords: Vector2D) -> tuple[int, int, int, int, int]:
        """Return (left, top, dx, dy, view_change)"""
        ...

    @abstractmethod
    def scroll(self, vector: tuple[int, int]) -> tuple[int, int, int, int, int]: ...

    @abstractmethod
    def get_center_offset(self) -> tuple[int, int]: ...

    @abstractmethod
    def translate_point(self, point: Vector2D) -> tuple[int, int]: ...

    @abstractmethod
    def translate_rect(self, rect: RectLike) -> Rect: ...

    @abstractmethod
    def translate_points(self, points: list[Vector2D]) -> list[tuple[int, int]]: ...

    @abstractmethod
    def translate_rects(self, rects: list[Rect]) -> list[Rect]: ...


class ViewPort(ViewportBase):
    """
    Optimized viewport:
    - Caches center offset
    - Precomputes zoom flags and ratios
    - Reduces branching inside translate methods
    - Minimizes attribute lookups inside loops
    - Extracts a unified scaling helper
    """

    def __init__(
        self,
        data: PyscrollDataAdapter,
        size: tuple[int, int],
        zoom: float,
        clamp_camera: bool,
    ) -> None:
        self.data = data
        self.clamp_camera = clamp_camera
        self._zoom_level = zoom
        self._anchored_view = True

        self._x_offset = 0
        self._y_offset = 0
        self._real_ratio_x = 1.0
        self._real_ratio_y = 1.0
        self._is_unity_zoom = zoom == 1.0

        self._size = (0, 0)
        self._half_width = 0
        self._half_height = 0
        self._center_offset = (0, 0)

        self.map_rect = Rect(0, 0, 0, 0)
        self.view_rect = Rect(0, 0, 0, 0)
        self._tile_view = Rect(0, 0, 0, 0)

        self.set_size(size)

    @property
    def zoom(self) -> float:
        return self._zoom_level

    @zoom.setter
    def zoom(self, value: float) -> None:
        if value <= 0:
            raise ValueError("zoom level cannot be zero or less")
        self._zoom_level = value
        self._is_unity_zoom = value == 1.0
        self.set_size(self._size)

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    def _calculate_buffer_size(
        self, size: tuple[int, int], zoom: float
    ) -> tuple[int, int]:
        scale = 1.0 / zoom
        return int(size[0] * scale), int(size[1] * scale)

    def set_size(self, size: tuple[int, int]) -> tuple[int, int]:
        view_size = self._calculate_buffer_size(size, self._zoom_level)

        self._size = size
        tw, th = self.data.tile_size
        mw, mh = self.data.map_size

        buffer_tile_width = int(math.ceil(view_size[0] / tw) + 1)
        buffer_tile_height = int(math.ceil(view_size[1] / th) + 1)
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th

        self.map_rect = Rect(0, 0, mw * tw, mh * th)
        self.view_rect.size = view_size
        self._tile_view = Rect(0, 0, buffer_tile_width, buffer_tile_height)

        self._half_width = view_size[0] // 2
        self._half_height = view_size[1] // 2

        self._real_ratio_x = float(size[0]) / view_size[0] if view_size[0] else 1.0
        self._real_ratio_y = float(size[1]) / view_size[1] if view_size[1] else 1.0

        self.center(self.view_rect.center)

        return buffer_pixel_size

    def _update_center_offset(self) -> None:
        """Cache center offset for fast translation."""
        self._center_offset = (
            -self.view_rect.centerx + self._half_width,
            -self.view_rect.centery + self._half_height,
        )

    def center(self, coords: Vector2D) -> tuple[int, int, int, int, int]:
        x, y = round(coords[0]), round(coords[1])
        tw, th = self.data.tile_size
        mw, mh = self.data.map_size
        vw, vh = self._tile_view.size

        self.view_rect.center = x, y

        if self.clamp_camera:
            self._anchored_view = True
            self.view_rect.clamp_ip(self.map_rect)
            x, y = self.view_rect.center

        new_left, self._x_offset = divmod(x - self._half_width, tw)
        new_top, self._y_offset = divmod(y - self._half_height, th)

        if not self.clamp_camera:
            self._anchored_view = True
            old_left = self._tile_view.left
            old_top = self._tile_view.top

            dx = new_left - old_left
            dy = new_top - old_top

            right = new_left + vw
            bottom = new_top + vh

            if mw < vw or new_left < 0:
                new_left = 0
                self._x_offset = x - self._half_width
                self._anchored_view = False
            elif right > mw:
                new_left = mw - vw
                self._x_offset += dx * tw
                self._anchored_view = False

            if mh < vh or new_top < 0:
                new_top = 0
                self._y_offset = y - self._half_height
                self._anchored_view = False
            elif bottom > mh:
                new_top = mh - vh
                self._y_offset += dy * th
                self._anchored_view = False

        dx = new_left - self._tile_view.left
        dy = new_top - self._tile_view.top
        view_change = max(abs(dx), abs(dy))

        self._update_center_offset()

        return new_left, new_top, dx, dy, view_change

    def scroll(self, vector: tuple[int, int]) -> tuple[int, int, int, int, int]:
        cx = self.view_rect.centerx + vector[0]
        cy = self.view_rect.centery + vector[1]
        return self.center((cx, cy))

    def get_center_offset(self) -> tuple[int, int]:
        return self._center_offset

    def _scale(self, x: float, y: float) -> tuple[int, int]:
        if self._is_unity_zoom:
            return int(x), int(y)
        rx = self._real_ratio_x
        ry = self._real_ratio_y
        return int(round(x * rx)), int(round(y * ry))

    def translate_point(self, point: Vector2D) -> tuple[int, int]:
        sx, sy = self._center_offset
        return self._scale(point[0] + sx, point[1] + sy)

    def translate_rect(self, rect: RectLike) -> Rect:
        sx, sy = self._center_offset
        rx = self._real_ratio_x
        ry = self._real_ratio_y
        x, y, w, h = rect

        if self._is_unity_zoom:
            return Rect(x + sx, y + sy, w, h)

        return Rect(
            round((x + sx) * rx),
            round((y + sy) * ry),
            round(w * rx),
            round(h * ry),
        )

    def translate_points(self, points: list[Vector2D]) -> list[tuple[int, int]]:
        sx, sy = self._center_offset
        if self._is_unity_zoom:
            return [(int(p[0]) + sx, int(p[1]) + sy) for p in points]

        rx = self._real_ratio_x
        ry = self._real_ratio_y
        r = round
        return [(r((p[0] + sx) * rx), r((p[1] + sy) * ry)) for p in points]

    def translate_rects(self, rects: list[Rect]) -> list[Rect]:
        sx, sy = self._center_offset
        if self._is_unity_zoom:
            return [Rect(r.x + sx, r.y + sy, r.w, r.h) for r in rects]

        rx = self._real_ratio_x
        ry = self._real_ratio_y
        r = round
        return [
            Rect(
                r((rect.x + sx) * rx),
                r((rect.y + sy) * ry),
                r(rect.w * rx),
                r(rect.h * ry),
            )
            for rect in rects
        ]


class IsometricViewport(ViewPort):

    def __init__(
        self,
        data: PyscrollDataAdapter,
        size: tuple[int, int],
        zoom: float = 1.0,
        clamp_camera: bool = True,
    ) -> None:
        super().__init__(data=data, size=size, zoom=zoom, clamp_camera=clamp_camera)

    def set_size(self, size: tuple[int, int]) -> tuple[int, int]:
        view_size = self._calculate_buffer_size(size, self._zoom_level)

        self._size = size
        tw, th = self.data.tile_size
        mw, mh = self.data.map_size

        vw0, vh0 = view_size

        buffer_tile_width = (int(math.ceil(vw0 / tw)) + 2) * 2
        buffer_tile_height = (int(math.ceil(vh0 / th)) + 2) * 2
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th

        self.map_rect = Rect(0, 0, mw * tw, mh * th)
        self.view_rect.size = view_size
        self._tile_view = Rect(0, 0, buffer_tile_width, buffer_tile_height)

        self._half_width = vw0 // 2
        self._half_height = vh0 // 2

        self._real_ratio_x = float(size[0]) / vw0 if vw0 else 1.0
        self._real_ratio_y = float(size[1]) / vh0 if vh0 else 1.0

        self.center(self.view_rect.center)

        return buffer_pixel_size

    def center(self, coords: Vector2D) -> tuple[int, int, int, int, int]:
        tw, th = self.data.tile_size
        tile_view = self._tile_view

        x = int(round(coords[0]))
        y = int(round(coords[1]))

        self.view_rect.center = x, y

        if self.clamp_camera:
            self._anchored_view = True
            self.view_rect.clamp_ip(self.map_rect)
            x, y = self.view_rect.center

        left, ox = divmod(x, tw)
        top, oy = divmod(y, th)

        iso = vector2_to_iso((ox >> 1, oy))  # ox/2 → bitshift

        self._x_offset = iso[0]
        self._y_offset = iso[1]

        vw = self.view_rect.width
        vh = self.view_rect.height

        bw = tile_view.width * tw
        bh = tile_view.height * th

        self._x_offset += (bw - vw) // 2
        self._y_offset += (bh - vh) // 4

        dx = left - tile_view.left
        dy = top - tile_view.top
        view_change = max(abs(dx), abs(dy))

        if view_change:
            tile_view.move_ip(dx, dy)

        self._update_center_offset()

        return left, top, dx, dy, view_change
