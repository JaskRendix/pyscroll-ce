"""
This file contains a few classes for accessing data

If you are developing your own map format, please use this
as a template.  Just fill in values that work for your game.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from heapq import heappop, heappush
from itertools import product
from typing import Any, Optional

import pygame
from pygame.rect import Rect
from pygame.surface import Surface

try:
    # optional pytmx support
    import pytmx
except ImportError:
    pass

from pyscroll.animation import AnimationFrame, AnimationToken
from pyscroll.common import RectLike, Vector2DInt, Vector3DInt, rect_to_bb

__all__ = (
    "PyscrollDataAdapter",
    "TiledMapData",
    "MapAggregator",
)


class PyscrollDataAdapter:
    """
    Use this as a template for data adapters

    Contains logic for handling animated tiles.  Animated tiles
    are a WIP feature, and while in theory will work with any data
    source, it is only tested using Tiled maps, loaded with pytmx.

    """

    # the following can be class/instance attributes
    # or properties.  they are listed here as class
    # instances, but use as properties is fine, too.

    # (int, int): size of each tile in pixels
    tile_size: Vector2DInt = (0, 0)
    # (int, int): size of map in tiles
    map_size: Vector2DInt = (0, 0)
    # list of visible layer integers
    visible_tile_layers: list[int] = []

    def __init__(self) -> None:
        # list of animation tokens
        self._animation_queue: list[AnimationToken] = []
        # mapping of tile substitutions when animated
        self._animated_tile: dict[Vector3DInt, Surface] = {}
        # track the tiles on screen with animations
        self._tracked_tiles = set()
        # Animation Control
        self._is_paused: bool = False
        self._last_time: float = 0.0
        # Time when pause was initiated
        self._paused_time: float = 0.0
        # False = freeze, True = skip-ahead
        self._pause_mode_skip_ahead: bool = False

    def reload_data(self) -> None:
        raise NotImplementedError

    def process_animation_queue(
        self,
        tile_view: Rect,
    ) -> list[tuple[int, int, int, Surface]]:
        """
        Given the time and the tile view, process tile changes and return them

        Args:
            tile_view: Rect representing tiles on the screen

        """
        new_tiles = list()

        # verify that there are tile substitutions ready
        self._update_time()
        try:
            if self._animation_queue[0].next > self._last_time:
                return new_tiles

        # raised with the animation queue is empty (no animations at all)
        except IndexError:
            return new_tiles

        new_tiles_append = new_tiles.append
        tile_layers = tuple(self.visible_tile_layers)
        get_tile_image = self.get_tile_image

        # test if the next scheduled tile change is ready
        while self._animation_queue[0].next <= self._last_time:

            # get the next tile/frame which is ready to be changed
            token = heappop(self._animation_queue)
            next_frame = token.advance(self._last_time)
            heappush(self._animation_queue, token)

            # following line for when all gid positions are known
            # for position in self._tracked_tiles & token.positions:

            for position in token.positions.copy():
                x, y, l = position

                # if this tile is on the buffer (checked by using the tile view)
                if tile_view.collidepoint(x, y):

                    # record the location of this tile, in case of a screen wipe, or sprite cover
                    self._animated_tile[position] = next_frame.image

                    # redraw the entire column of tiles
                    for layer in tile_layers:
                        if layer == l:

                            # queue the new animated tile
                            new_tiles_append((x, y, layer, next_frame.image))
                        else:

                            # queue the normal tile
                            image = get_tile_image(x, y, layer)
                            if image:
                                new_tiles_append((x, y, layer, image))

                # not on screen, but was previously.  clear it.
                else:
                    token.positions.remove(position)

        return new_tiles

    def _update_time(self) -> None:
        if not self._is_paused:
            current_time = time.time()
            if self._pause_mode_skip_ahead:
                # Skip-ahead mode: catch up to real time
                if self._paused_time > 0.0:
                    time_offset = current_time - self._paused_time
                    self._last_time += time_offset
                    self._paused_time = 0.0
                else:
                    self._last_time = current_time
            else:
                # Freeze mode: resume exactly where you left off
                self._last_time = current_time

    def prepare_tiles(self, tiles: RectLike) -> None:
        """
        Somewhat experimental: The renderer will advise data layer of its view

        For some data providers, it would be useful to know what tiles will be drawn
        before they are ready to draw.  This exposes the tile view to the data.

        * A draw will happen immediately after this returns.
        * Do not hold on to this reference or change it.

        Args:
            tiles: Reference to the tile view

        """
        pass

    def reload_animations(self) -> None:
        """
        Reload animation information.

        PyscrollDataAdapter.get_animations must be implemented

        """
        self._update_time()
        self._tracked_gids: set[int] = set()
        self._animation_map: dict[int, AnimationToken] = {}

        for gid, frame_data in self.get_animations():
            self._tracked_gids.add(gid)

            frames: list[AnimationFrame] = []
            for frame_gid, frame_duration in frame_data:
                image = self._get_tile_image_by_id(frame_gid)
                # Convert ms → seconds
                frames.append(AnimationFrame(image, frame_duration / 1000.0))

            # the following line is slow when loading maps, but avoids overhead when rendering
            # positions = set(self.tmx.get_tile_locations_by_gid(gid))

            # ideally, positions would be populated with all the known
            # locations of an animation, but searching for their locations
            # is slow. so it will be updated as the map is drawn.

            positions: set[Vector3DInt] = set()
            ani = AnimationToken(positions, frames, self._last_time)
            self._animation_map[gid] = ani
            heappush(self._animation_queue, ani)

    def get_tile_image(self, x: int, y: int, l: int) -> Surface:
        """
        Get a tile image, respecting current animations.

        Args:
            x: x coordinate
            y: y coordinate
            l: layer

        """
        position: Vector3DInt = (x, y, l)

        try:
            return self._animated_tile[position]

        except KeyError:
            image = self._get_tile_image(x, y, l)

            if self._animation_map:
                gid = self._get_tile_gid(x, y, l)
                if gid in self._animation_map:
                    token = self._animation_map[gid]
                    token.positions.add(position)

                    self._animated_tile[position] = token.frames[0].image
                    return self._animated_tile[position]

                return image

            return image

    def _get_tile_image(self, x: int, y: int, l: int) -> Surface:
        """
        Return tile at the coordinates, or None is empty.

        This is used to query the data source directly, without
        checking for animations or any other tile transformations.

        You must override this to support other data sources

        Args:
            x: x coordinate
            y: y coordinate
            l: layer

        """
        raise NotImplementedError

    def _get_tile_image_by_id(self, id: int) -> Any:
        """
        Return Image by a custom ID.

        Used for animations.  Not required for static maps.

        Args:
            id:

        """
        raise NotImplementedError

    def get_animations(self) -> Iterable[tuple[int, list[tuple[int, int]]]]:
        """
        Get tile animation data.

        This method is subject to change in the future.

        Must yield tuples that in the following format:
          ( ID, Frames )

          Where Frames is:
          [ (ID, Duration), ... ]

          [tuple[int, tuple[int, float]]]
          [tuple[gid, tuple[frame_gid, frame_duration]]]

          And ID is a reference to a tile image.
          This will be something accessible using _get_tile_image_by_id

          Duration should be in milliseconds

        """
        raise NotImplementedError

    def _get_tile_gid(self, x: int, y: int, l: int) -> Optional[int]:
        """
        Return the Global ID (GID) of the tile at the coordinates, or None if empty.

        This is required for dynamic animation tracking.
        Concrete implementations (e.g., TiledMapData) must override this.

        Args:
            x: x coordinate
            y: y coordinate
            l: layer

        """
        raise NotImplementedError

    def get_tile_images_by_rect(self, rect: RectLike):
        """
        Given a 2d area, return generator of tile images inside.

        Given the coordinates, yield the following tuple for each tile:
          X, Y, Layer Number, pygame Surface

        This method also defines render order by re arranging the
        positions of each tile as it is yielded to the renderer.

        There is an optimization that you can make for your data:
        If you can provide access to tile information in a batch,
        then pyscroll can access data faster and render quicker.

        To implement this optimization, override this method.

        Not like python 'Range': should include the end index!

        Args:
            rect: Rect-like object that defines tiles to draw

        """
        x1, y1, x2, y2 = rect_to_bb(rect)
        for layer in self.visible_tile_layers:
            for y, x in product(range(y1, y2 + 1), range(x1, x2 + 1)):
                tile = self.get_tile_image(x, y, layer)
                if tile:
                    yield x, y, layer, tile

    def pause_animations(self) -> None:
        """
        Halt all map tile animations.
        """
        if not self._is_paused:
            self._is_paused = True
            self._paused_time = time.time()

    def resume_animations(self) -> None:
        """
        Resume all map tile animations from where they left off.
        """
        if self._is_paused:
            self._is_paused = False
            self._paused_time = 0.0
            self._update_time()

    def set_animation_speed_multiplier(self, multiplier: float) -> None:
        """
        Adjust the speed of all active animations.

        Args:
            multiplier: A factor to scale the animation speed (e.g., 0.5 for half speed).
        """
        if multiplier <= 0:
            raise ValueError("Multiplier must be greater than zero.")

        for token in self._animation_queue:
            token.speed_multiplier = multiplier


class TiledMapData(PyscrollDataAdapter):
    """
    For data loaded from pytmx.

    """

    def __init__(self, tmx: pytmx.TiledMap) -> None:
        super(TiledMapData, self).__init__()
        self.tmx = tmx
        self.reload_animations()

    def reload_data(self) -> None:
        self.tmx = pytmx.load_pygame(self.tmx.filename)

    def get_animations(self):
        for gid, d in self.tmx.tile_properties.items():
            try:
                frames = d["frames"]
            except KeyError:
                continue

            if frames:
                yield gid, frames

    def convert_surfaces(self, parent: Surface, alpha: bool = False) -> None:
        """
        Convert all TMX images to match the display format.

        Args:
            parent: A reference surface (usually the display surface).
            alpha: If True, use convert_alpha; otherwise use convert.
        """
        images = []
        for i in self.tmx.images:
            try:
                if alpha:
                    images.append(i.convert_alpha())
                else:
                    images.append(i.convert(parent))
            except AttributeError:
                images.append(None)
        self.tmx.images = images

    @property
    def tile_size(self) -> Vector2DInt:
        return self.tmx.tilewidth, self.tmx.tileheight

    @property
    def map_size(self) -> Vector2DInt:
        return self.tmx.width, self.tmx.height

    @property
    def visible_tile_layers(self):
        return self.tmx.visible_tile_layers

    @property
    def visible_object_layers(self) -> Iterable[pytmx.TiledObjectGroup]:
        return (
            layer
            for layer in self.tmx.visible_layers
            if isinstance(layer, pytmx.TiledObjectGroup)
        )

    def _get_tile_gid(self, x: int, y: int, l: int) -> Optional[int]:
        try:
            return self.tmx.layers[l].data[y][x]
        except (IndexError, AttributeError):
            return None

    def _get_tile_image(self, x: int, y: int, l: int):
        try:
            return self.tmx.get_tile_image(x, y, l)
        except ValueError:
            return None

    def _get_tile_image_by_id(self, id: int) -> Surface:
        return self.tmx.images[id]

    def get_tile_images_by_rect(self, rect: RectLike):
        def rev(seq: list[int], start: int, stop: int) -> enumerate[int]:
            if start < 0:
                start = 0
            return enumerate(seq[start : stop + 1], start)

        x1, y1, x2, y2 = rect_to_bb(rect)
        images = self.tmx.images
        layers = self.tmx.layers
        at = self._animated_tile
        tracked_gids = self._tracked_gids
        anim_map = self._animation_map
        track = bool(self._animation_queue)

        for l in self.tmx.visible_tile_layers:
            for y, row in rev(layers[l].data, y1, y2):
                for x, gid in [i for i in rev(row, x1, x2) if i[1]]:
                    # since the tile has been queried, assume it wants
                    # to be checked for animations sometime in the future
                    if track and gid in tracked_gids:
                        anim_map[gid].positions.add((x, y, l))
                    try:
                        # animated, so return the correct frame
                        tile = at[(x, y, l)]
                    except KeyError:
                        # not animated, so return surface from data, if any
                        tile = images[gid]
                    if tile:
                        yield x, y, l, tile


class MapAggregator(PyscrollDataAdapter):
    """
    Combine multiple data sources with an offset.

    Improvements:
    - Correct layer offset handling
    - Simplified normalization of positions
    - Support for animations
    - Delegation for tile image lookups
    - Dynamic map removal with re-normalization
    """

    def __init__(self, tile_size: Vector2DInt, normalize: bool = True) -> None:
        super().__init__()
        self.tile_size = tile_size
        self._normalize = normalize
        self.map_size: tuple[int, int] = (0, 0)
        self.maps: list[tuple[PyscrollDataAdapter, pygame.Rect, int]] = []
        self._min_x: int = 0
        self._min_y: int = 0
        self._animation_map: dict[int, AnimationToken] = {}
        self._tracked_gids: set[int] = set()

    def add_map(
        self, data: PyscrollDataAdapter, offset: Vector2DInt, layer: int = 0
    ) -> None:
        if data.tile_size != self.tile_size:
            raise ValueError("Tile sizes must be the same for all maps.")

        rect = pygame.Rect(offset, data.map_size)
        self.maps.append((data, rect, layer))

        # Only normalize if flag is set
        if self._normalize:
            self._min_x = min(self._min_x, rect.left)
            self._min_y = min(self._min_y, rect.top)
            self._normalize_positions()

        self._update_map_size()

    def remove_map(self, data: PyscrollDataAdapter) -> None:
        initial_len = len(self.maps)
        self.maps = [m for m in self.maps if m[0] != data]
        if len(self.maps) == initial_len:
            raise ValueError("Map is not in the aggregator")

        if self._normalize:
            self._re_normalize_positions()
        else:
            self._update_map_size()

    def reload_animations(self) -> None:
        self._update_time()
        self._tracked_gids = set()
        self._animation_map = {}
        self._animation_queue = []

        for data, rect, z in self.maps:
            for gid, frame_data in data.get_animations():
                self._tracked_gids.add(gid)
                frames = []
                for frame_gid, frame_duration in frame_data:
                    image = data._get_tile_image_by_id(frame_gid)
                    frames.append(AnimationFrame(image, frame_duration / 1000.0))
                ani = AnimationToken(set(), frames, self._last_time)
                self._animation_map[gid] = ani
                heappush(self._animation_queue, ani)

    def _normalize_positions(self) -> None:
        """Shift maps so that top-left is always (0,0)."""
        if self._min_x < 0 or self._min_y < 0:
            shift_x = -self._min_x
            shift_y = -self._min_y
            for _, rect, _ in self.maps:
                rect.move_ip(shift_x, shift_y)
            self._min_x, self._min_y = 0, 0

    def _re_normalize_positions(self) -> None:
        """Recalculate normalization after removal."""
        if not self.maps:
            self._min_x, self._min_y = 0, 0
            self.map_size = (0, 0)
            return

        self._min_x = min(rect.left for _, rect, _ in self.maps)
        self._min_y = min(rect.top for _, rect, _ in self.maps)
        self._normalize_positions()
        self._update_map_size()

    def _update_map_size(self) -> None:
        mx = 0
        my = 0
        for _, rect, _ in self.maps:
            mx = max(mx, rect.right)
            my = max(my, rect.bottom)
        self.map_size = (mx, my)

    @property
    def visible_tile_layers(self) -> list[int]:
        """Return all visible layers adjusted by aggregator offsets."""
        layers = set()
        for data, _, z in self.maps:
            layers.update([l + z for l in data.visible_tile_layers])
        return sorted(layers)

    def get_tile_images_by_rect(
        self, view: pygame.Rect
    ) -> Iterable[tuple[int, int, int, Surface]]:
        """Yield tile images within the view, with adjusted coords and layers."""
        view = pygame.Rect(view)
        sorted_maps = sorted(self.maps, key=lambda m: m[2])  # sort by z offset

        for data, rect, z in sorted_maps:
            ox, oy = rect.topleft
            clipped = rect.clip(view).move(-ox, -oy)
            if clipped.width > 0 and clipped.height > 0:
                for x, y, l, image in data.get_tile_images_by_rect(clipped):
                    yield x + ox, y + oy, l + z, image

    def _get_tile_image(self, x: int, y: int, l: int) -> Optional[Surface]:
        """Delegate tile image lookup to the correct sub-map."""
        for data, rect, z in self.maps:
            if rect.collidepoint(x, y) and (l - z) in data.visible_tile_layers:
                local_x = x - rect.left
                local_y = y - rect.top
                local_l = l - z
                return data._get_tile_image(local_x, local_y, local_l)
        return None

    def _get_tile_image_by_id(self, id: int) -> Optional[Surface]:
        """Delegate image lookup by ID to child maps (first match)."""
        for data, _, _ in self.maps:
            try:
                return data._get_tile_image_by_id(id)
            except Exception:
                continue
        return None

    def get_animations(self) -> Iterable[tuple[int, list[tuple[int, int]]]]:
        """Aggregate animations from all child maps."""
        for data, _, _ in self.maps:
            if hasattr(data, "get_animations"):
                yield from data.get_animations()

    def reload_data(self) -> None:
        """Reload all child maps."""
        for data, _, _ in self.maps:
            if hasattr(data, "reload_data"):
                data.reload_data()

    def __repr__(self) -> str:
        return f"MapAggregator(tile_size={self.tile_size}, maps={self.maps})"

    def __len__(self) -> int:
        return len(self.maps)
