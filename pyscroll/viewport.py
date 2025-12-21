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
    Manages the camera's position, size, and zoom level.
    This class is responsible for all coordinate calculations.
    """

    _size: tuple[int, int]
    _half_width: int
    _half_height: int
    _zoom_level: float
    _x_offset: int
    _y_offset: int
    _real_ratio_x: float
    _real_ratio_y: float
    _anchored_view: bool

    map_rect: Rect
    view_rect: Rect
    _tile_view: Rect

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

        self._size = (0, 0)
        self._half_width = 0
        self._half_height = 0
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
        self.set_size(self._size)

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    def _calculate_buffer_size(
        self, size: tuple[int, int], value: float
    ) -> tuple[int, int]:
        scale = 1.0 / value
        return int(size[0] * scale), int(size[1] * scale)

    def set_size(self, size: tuple[int, int]) -> tuple[int, int]:
        """
        Set the screen size, calculate derived values, and return the required
        internal buffer size. This must be called when screen size or zoom changes.
        """
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

    def center(self, coords: Vector2D) -> tuple[int, int, int, int, int]:
        """
        Center the map on a pixel coordinate and calculate new tile/pixel offsets.

        Returns: (left, top, dx, dy, view_change)
            left, top: new tile-index coordinates of the view's top-left corner.
            dx, dy: Change in tile-index position since last center/scroll.
            view_change: max(abs(dx), abs(dy))
        """
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
        right = new_left + vw
        bottom = new_top + vh

        if not self.clamp_camera:
            self._anchored_view = True
            dx = int(new_left - self._tile_view.left)
            dy = int(new_top - self._tile_view.top)

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

        dx = int(new_left - self._tile_view.left)
        dy = int(new_top - self._tile_view.top)
        view_change = max(abs(dx), abs(dy))

        return new_left, new_top, dx, dy, view_change

    def scroll(self, vector: tuple[int, int]) -> tuple[int, int, int, int, int]:
        """
        Scroll the background by a pixel vector. Calls center internally.

        Returns: (left, top, dx, dy, view_change)
        """
        return self.center(
            (vector[0] + self.view_rect.centerx, vector[1] + self.view_rect.centery)
        )

    def get_center_offset(self) -> tuple[int, int]:
        """Return x, y pair that will change world coords to view coords."""
        return (
            -self.view_rect.centerx + self._half_width,
            -self.view_rect.centery + self._half_height,
        )

    def translate_point(self, point: Vector2D) -> tuple[int, int]:
        """Translate world coordinates and return screen coordinates."""
        mx, my = self.get_center_offset()
        if self._zoom_level == 1.0:
            return int(point[0] + mx), int(point[1] + my)
        else:
            return (
                int(round((point[0] + mx) * self._real_ratio_x)),
                int(round((point[1] + my) * self._real_ratio_y)),
            )

    def translate_rect(self, rect: RectLike) -> Rect:
        """Translate rect position and size to screen coordinates."""
        mx, my = self.get_center_offset()
        rx = self._real_ratio_x
        ry = self._real_ratio_y
        x, y, w, h = rect
        if self._zoom_level == 1.0:
            return Rect(x + mx, y + my, w, h)
        else:
            return Rect(
                round((x + mx) * rx), round((y + my) * ry), round(w * rx), round(h * ry)
            )

    def translate_points(self, points: list[Vector2D]) -> list[tuple[int, int]]:
        """Translate coordinates and return screen coordinates."""
        retval: list[tuple[int, int]] = []
        append = retval.append
        sx, sy = self.get_center_offset()
        if self._zoom_level == 1.0:
            for c in points:
                append((int(c[0]) + sx, int(c[1]) + sy))
        else:
            rx = self._real_ratio_x
            ry = self._real_ratio_y
            for c in points:
                append((int(round((c[0] + sx) * rx)), int(round((c[1] + sy) * ry))))
        return retval

    def translate_rects(self, rects: list[Rect]) -> list[Rect]:
        """Translate rect position and size to screen coordinates."""
        retval: list[Rect] = []
        append = retval.append
        sx, sy = self.get_center_offset()
        if self._zoom_level == 1.0:
            for r in rects:
                x, y, w, h = r
                append(Rect(x + sx, y + sy, w, h))
        else:
            rx = self._real_ratio_x
            ry = self._real_ratio_y
            for r in rects:
                x, y, w, h = r
                append(
                    Rect(
                        round((x + sx) * rx),
                        round((y + sy) * ry),
                        round(w * rx),
                        round(h * ry),
                    )
                )
        return retval


class IsometricViewport(ViewPort):
    """
    Isometric variant of ViewPort.

    - Larger internal tile buffer
    - Custom centering logic
    - Custom offset computation
    """

    def __init__(
        self,
        data: PyscrollDataAdapter,
        size: tuple[int, int],
        zoom: float = 1.0,
        clamp_camera: bool = True,
    ) -> None:
        super().__init__(data=data, size=size, zoom=zoom, clamp_camera=clamp_camera)

    def set_size(self, size: tuple[int, int]) -> tuple[int, int]:
        """
        Set the screen size for an isometric view.

        Uses a larger internal buffer than the orthogonal ViewPort.
        """
        view_size = self._calculate_buffer_size(size, self._zoom_level)

        self._size = size
        tw, th = self.data.tile_size
        mw, mh = self.data.map_size

        # Isometric buffers need extra margin
        buffer_tile_width = int(math.ceil(view_size[0] / tw) + 2) * 2
        buffer_tile_height = int(math.ceil(view_size[1] / th) + 2) * 2
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th

        self.map_rect = Rect(0, 0, mw * tw, mh * th)
        self.view_rect.size = view_size
        self._tile_view = Rect(0, 0, buffer_tile_width, buffer_tile_height)
        self._half_width = view_size[0] // 2
        self._half_height = view_size[1] // 2

        self._real_ratio_x = float(size[0]) / view_size[0] if view_size[0] else 1.0
        self._real_ratio_y = float(size[1]) / view_size[1] if view_size[1] else 1.0

        # Initialize offsets + tile_view position
        self.center(self.view_rect.center)

        return buffer_pixel_size

    def center(self, coords: Vector2D) -> tuple[int, int, int, int, int]:
        """
        Center the map on a 'map pixel' in isometric space.

        Returns: (left, top, dx, dy, view_change)
        """
        x, y = [round(i, 0) for i in coords]
        tw, th = self.data.tile_size
        vw, vh = self._tile_view.size

        self.view_rect.center = x, y

        if self.clamp_camera:
            self._anchored_view = True
            self.view_rect.clamp_ip(self.map_rect)
            x, y = self.view_rect.center

        # Tile index + sub-tile offset
        left, ox = divmod(x, tw)
        top, oy = divmod(y, th)

        # Convert sub-tile offset to isometric projection
        vec = (int(ox / 2), int(oy))
        iso = vector2_to_iso(vec)
        self._x_offset = iso[0]
        self._y_offset = iso[1]

        # Center the isometric buffer in the view
        buffer_pixel_width = self._tile_view.width * tw
        buffer_pixel_height = self._tile_view.height * th

        self._x_offset += (buffer_pixel_width - self.view_rect.width) // 2
        self._y_offset += (buffer_pixel_height - self.view_rect.height) // 4

        # Tile-view movement + view_change calculation
        dx = int(left - self._tile_view.left)
        dy = int(top - self._tile_view.top)
        view_change = max(abs(dx), abs(dy))

        if view_change:
            self._tile_view.move_ip(dx, dy)

        return int(left), int(top), dx, dy, view_change
