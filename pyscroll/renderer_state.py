from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pygame.rect import Rect
    from pygame.surface import Surface


@dataclass
class RendererState:
    """
    Explicit contract describing the lifecycle and invariants of a BufferedRenderer.

    This state object is mutated only by the renderer and its pipelines.
    It ensures that all required fields exist and that transitions are explicit.
    """

    # Core buffers
    buffer: Surface | None
    zoom_buffer: Surface | None

    # Viewport-derived state
    tile_view: Rect
    last_tile_view_size: tuple[int, int]

    # Previous blit region on the target surface
    previous_blit: Rect

    # Redraw cutoff threshold
    redraw_cutoff: int

    # Whether anchored view logic is active
    anchored_view: bool

    # Whether pipelines have been initialized
    pipelines_ready: bool = False

    def update_tile_view(self, new_tile_view: Rect) -> bool:
        """
        Update tile_view and return True if dimensions changed.
        """
        changed = new_tile_view.size != self.last_tile_view_size
        self.tile_view = new_tile_view
        if changed:
            self.last_tile_view_size = new_tile_view.size
        return changed

    def set_buffers(self, buffer: Surface, zoom_buffer: Surface | None) -> None:
        self.buffer = buffer
        self.zoom_buffer = zoom_buffer

    def set_previous_blit(self, rect: Rect) -> None:
        self.previous_blit = rect

    def mark_pipelines_ready(self) -> None:
        self.pipelines_ready = True
