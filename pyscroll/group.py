from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pygame.sprite import LayeredUpdates, Sprite

if TYPE_CHECKING:
    from pygame.rect import FRect, Rect
    from pygame.surface import Surface

    from pyscroll.common import Vector2D
    from pyscroll.orthographic import BufferedRenderer


@dataclass(slots=True)
class Renderable:
    """
    Lightweight container for a sprite’s render information.
    Using slots=True eliminates per-instance __dict__ overhead,
    which is significant when creating many Renderables per frame.
    """

    layer: int
    rect: Rect | FRect
    surface: Surface | None = None
    blendmode: Any = None


class PyscrollGroup(LayeredUpdates[Sprite]):
    """
    Optimized sprite group that integrates with a Pyscroll renderer.

    Improvements:
    - Faster attribute access via local bindings
    - Frustum culling
    - Accurate spritedict updates even for off-screen sprites
    - Zero overhead Renderable objects (slots=True)
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
        self,
        surface: Surface,
        bgd: Surface | None = None,
        special_flags: int = 0,
    ) -> list[Rect | FRect]:
        """
        Draw map and all visible sprites onto the surface.

        This method is hot-path optimized:
        - Local variable binding for speed
        - Frustum culling
        - Minimal attribute lookups
        - Zero-dict Renderable objects
        """
        map_layer = self._map_layer
        ox, oy = map_layer.get_center_offset()
        view_rect = map_layer.view_rect

        spritedict = self.spritedict
        get_layer = self.get_layer_of_sprite
        sprites = self.sprites  # local binding for speed

        renderables: list[Renderable] = []

        for spr in sprites():
            rect = spr.rect
            if rect is None:
                continue

            # Frustum culling
            if rect.colliderect(view_rect):
                new_rect = rect.move(ox, oy)
                spritedict[spr] = new_rect

                renderables.append(
                    Renderable(
                        layer=get_layer(spr),
                        rect=new_rect,
                        surface=spr.image,
                        blendmode=getattr(spr, "blendmode", None),
                    )
                )
            else:
                # Keep spritedict consistent for pygame's internal clear logic
                # Move the rect anyway so pygame knows where the sprite "was"
                spritedict[spr] = rect.move(ox, oy)

        # Required by pygame.sprite.LayeredUpdates
        self.lostsprites = []

        # Delegate final drawing to the map renderer
        return map_layer.draw(surface, surface.get_rect(), renderables)
