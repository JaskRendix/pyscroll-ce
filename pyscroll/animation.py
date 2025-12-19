from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Union

from pygame.surface import Surface

from pyscroll.common import Vector3DInt

TimeLike = Union[float, int]

__all__ = ("AnimationFrame", "AnimationToken")


@dataclass(frozen=True)
class AnimationFrame:
    """
    Represents a single frame in an animation.

    Attributes:
        image: The image surface to display.
        duration: Duration this frame should be shown, in seconds.
    """

    image: Surface
    duration: float


class AnimationToken:
    """
    Manages tile-based animation logic including frame timing, looping, and updates.

    Attributes:
        positions: Set of (x, y, layer) map coordinates where this animation is active.
        frames: Tuple of AnimationFrame instances.
        index: Current frame index.
        next: Time value when the next frame should appear.
        loop: If True, animation loops; if False, plays once.
        done: Indicates whether a non-looping animation has completed.
    """

    __slots__ = (
        "positions",
        "frames",
        "next",
        "index",
        "loop",
        "done",
        "speed_multiplier",
    )

    def __init__(
        self,
        positions: set[Vector3DInt],
        frames: Sequence[AnimationFrame],
        initial_time: float = 0.0,
        loop: bool = True,
        speed_multiplier: float = 1.0,
    ) -> None:
        """
        Initializes an AnimationToken instance.

        Args:
            positions: Set of map positions for the animation tile.
            frames: Sequence of AnimationFrame instances.
            initial_time: Optional time offset for smoother transitions.
            loop: If False, the animation stops at the last frame.

        Raises:
            ValueError: If the frames sequence is empty.
        """
        if not frames:
            raise ValueError("Frames sequence cannot be empty.")

        self.positions = positions
        self.frames = tuple(frames)
        self.index = 0

        self.speed_multiplier = speed_multiplier

        initial_duration = self.frames[0].duration / self.speed_multiplier
        self.next = initial_duration + initial_time

        self.loop = loop
        self.done = False

        if self.speed_multiplier <= 0:
            raise ValueError("Speed multiplier must be greater than zero.")

    def advance(self, current_time: TimeLike) -> AnimationFrame:
        """
        Advances to the next frame in the animation sequence.

        The 'current_time' passed in should be the time when the last frame
        expired (i.e., the value of self.next before advancing).

        Args:
            current_time: The time value used as the starting point for the
                next frame's duration.

        Returns:
            The next AnimationFrame in the sequence.
        """
        if self.done:
            return self.frames[self.index]

        if self.index == len(self.frames) - 1:
            if self.loop:
                self.index = 0
            else:
                self.done = True
                return self.frames[self.index]
        else:
            self.index += 1

        next_frame = self.frames[self.index]

        effective_duration = next_frame.duration / self.speed_multiplier

        self.next = effective_duration + current_time

        return next_frame

    def update(self, current_time: TimeLike, elapsed_time: TimeLike) -> AnimationFrame:
        """
        Updates the animation frame based on simulated elapsed time.

        Args:
            current_time: The current time used to evaluate frame progression.
            elapsed_time: Simulated time passed since last update.

        Returns:
            The active AnimationFrame.
        """
        if self.done:
            return self.frames[self.index]

        while current_time >= self.next:
            self.advance(self.next)
            current_time -= elapsed_time
        return self.frames[self.index]

    def __lt__(self, other: Union[AnimationToken, float, int]) -> bool:
        """
        Compares this token's next frame time with another.

        Args:
            other: Another AnimationToken or time value.

        Returns:
            True if this token's next frame time is earlier.
        """
        if isinstance(other, AnimationToken):
            return self.next < other.next
        else:
            return self.next < float(other)

    def __repr__(self) -> str:
        return f"AnimationToken(positions={self.positions}, frames={self.frames})"
