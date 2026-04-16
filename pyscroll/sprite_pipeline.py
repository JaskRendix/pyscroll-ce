from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pygame.rect import Rect
    from pygame.surface import Surface

    from pyscroll.group import Renderable
    from pyscroll.sprite_manager import SpriteRendererProtocol


class SpritePipeline:
    """
    Handles sprite rendering for the buffered renderer.
    This isolates sprite ordering, offset math, and quadtree usage.
    """

    def apply(
        self,
        sprite_renderer: SpriteRendererProtocol,
        surface: Surface,
        offset: tuple[int, int],
        tile_view: Rect,
        sprites: list[Renderable],
    ) -> None:
        sprite_renderer.render_sprites(
            surface,
            offset,
            tile_view,
            sprites,
        )
