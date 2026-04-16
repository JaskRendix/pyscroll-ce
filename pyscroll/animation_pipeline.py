from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pygame.rect import Rect
    from pygame.surface import Surface

    from pyscroll.data import PyscrollDataAdapter
    from pyscroll.tile_renderer import TileRendererProtocol


class AnimationPipeline:
    """
    Handles tile animation updates by processing the animation queue
    and flushing updated tiles into the buffer.
    """

    def apply(
        self,
        data: PyscrollDataAdapter,
        tile_renderer: TileRendererProtocol,
        tile_view: Rect,
        expanded_tile_view: Rect,
        buffer: Surface,
    ) -> None:
        tile_queue = data.process_animation_queue(expanded_tile_view)
        tile_renderer.flush_tile_queue(tile_queue, tile_view, buffer)
