from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pygame.rect import FRect, Rect
from pygame.sprite import LayeredUpdates, Sprite
from pygame.surface import Surface

from pyscroll.common import Vector2D

if TYPE_CHECKING:
    from pyscroll.orthographic import BufferedRenderer


class PyscrollGroup(LayeredUpdates[Sprite]):
    """
    Handles sprite management and rendering only.
    """

    def __init__(self, map_layer: BufferedRenderer, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._map_layer = map_layer

    def center(self, value: Vector2D) -> None:
        """Move the camera/renderer center."""
        self._map_layer.center(value)

    @property
    def view(self) -> Rect:
        """The visible area of the map."""
        return self._map_layer.view_rect

    def draw(
        self, surface: Surface, bgd: Surface | None = None, special_flags: int = 0
    ) -> list[Rect | FRect]:
        """Draw map and all visible sprites onto the surface."""
        map_layer = self._map_layer
        ox, oy = map_layer.get_center_offset()
        view_rect = map_layer.view_rect

        spritedict = self.spritedict
        renderables: list[tuple[Surface | None, FRect | Rect, int, Any]] = []

        for spr in self.sprites():
            rect = spr.rect
            if rect and rect.colliderect(view_rect):
                # Calculate drawing position (offset from map center)
                new_rect = rect.move(ox, oy)
                spritedict[spr] = new_rect

                # Direct tuple creation (faster than dataclasses in tight loops)
                renderables.append(
                    (
                        spr.image,
                        new_rect,
                        self.get_layer_of_sprite(spr),
                        getattr(spr, "blendmode", None),
                    )
                )

        self.lostsprites = []
        return map_layer.draw(surface, surface.get_rect(), cast(list[Any], renderables))
