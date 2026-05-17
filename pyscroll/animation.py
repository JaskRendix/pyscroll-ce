from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pygame.surface import Surface

TimeLike = float | int
Position: TypeAlias = tuple[int, int, int]

__all__ = ("AnimationFrame", "AnimationToken")


@dataclass(frozen=True)
class AnimationFrame:
    """
    Represents a single frame in an animation.

    Attributes:
        image: The image surface to display.
        duration: Base duration this frame should be shown, in seconds.
        frame_speed_multiplier: A multiplier specific to this frame.
    """

    image: Surface
    duration: float
    frame_speed_multiplier: float = 1.0


class AnimationToken:
    """
    Manages tile-based animation logic including frame timing, looping, and updates.

    Attributes:
        positions: Set of (x, y, layer) map coordinates where this animation is active.
        frames: Tuple of AnimationFrame instances.
        index: Current frame index.
        next: Time when the next frame should appear.
        loop: If True, animation loops; if False, plays once.
        ping_pong: If True, animation reverses direction at ends.
        direction: 1 for forward, -1 for backward.
        done: Indicates whether a non-looping animation has completed.
        speed_multiplier: Global factor applied to all frame durations.
    """

    __slots__ = (
        "positions",
        "frames",
        "_durations",
        "next",
        "index",
        "loop",
        "done",
        "speed_multiplier",
        "ping_pong",
        "direction",
        "on_complete",
        "_completed",
    )

    def __init__(
        self,
        positions: set[Position],
        frames: Sequence[AnimationFrame],
        initial_time: float = 0.0,
        loop: bool = True,
        speed_multiplier: float = 1.0,
        ping_pong: bool = False,
        random_jitter: float = 0.0,
        random_start_frame: bool = False,
        on_complete: Callable[[AnimationToken], None] | None = None,
    ) -> None:

        if not frames:
            raise ValueError("Frames sequence cannot be empty.")
        if speed_multiplier <= 0:
            raise ValueError("Speed multiplier must be greater than zero.")

        self.positions = positions
        self.frames = tuple(frames)
        self.loop = loop
        self.ping_pong = ping_pong
        self.speed_multiplier = speed_multiplier
        self.done = False
        self.direction = 1
        self.on_complete = on_complete
        self._completed = False

        # Precompute effective durations for all frames
        self._durations = tuple(
            (
                f.duration
                if (speed_multiplier * f.frame_speed_multiplier) <= 0
                else f.duration / (speed_multiplier * f.frame_speed_multiplier)
            )
            for f in self.frames
        )

        # Optional random starting frame
        self.index = random.randrange(len(self.frames)) if random_start_frame else 0

        jitter_offset = random.uniform(0.0, random_jitter) if random_jitter > 0 else 0.0

        self.next = initial_time + self._durations[self.index] + jitter_offset

    @property
    def current_frame(self) -> AnimationFrame:
        return self.frames[self.index]

    @property
    def is_finished(self) -> bool:
        return self.done

    def __len__(self) -> int:
        return len(self.frames)

    def __bool__(self) -> bool:
        return not self.done

    def advance(self, current_time: TimeLike) -> AnimationFrame:
        """
        Advances to the next frame, handling looping and ping-pong behavior.
        """
        if self.done:
            return self.current_frame

        if self.ping_pong:
            at_end = self.index == len(self.frames) - 1 and self.direction == 1
            at_start = self.index == 0 and self.direction == -1

            if at_end:
                self.direction = -1
            elif at_start:
                if not self.loop:
                    self._finish()
                    return self.current_frame
                self.direction = 1

            self.index += self.direction
            self._clamp_index()

            if not self.loop and self.index == 0 and self.direction == -1:
                self._finish()
                return self.current_frame

        else:
            if self.index == len(self.frames) - 1:
                if self.loop:
                    self.index = 0
                else:
                    self._finish()
                    return self.current_frame
            else:
                self.index += 1
                self._clamp_index()

        self.next = current_time + self._durations[self.index]
        return self.current_frame

    def update(
        self, current_time: TimeLike, elapsed_time: TimeLike | None = None
    ) -> AnimationFrame:
        """
        Advances through as many frames as needed to catch up to current_time.
        `elapsed_time` is accepted for backward compatibility but unused.
        """
        if self.done:
            return self.current_frame

        # Safety limit: max 4 full cycles
        max_steps = len(self.frames) * 4
        steps = 0

        while current_time >= self.next:
            self.advance(self.next)
            steps += 1
            if steps > max_steps:
                break

        return self.current_frame

    def reset(self, current_time: float = 0.0) -> None:
        """
        Reset the animation to its initial state.
        """
        self.index = 0
        self.direction = 1
        self.done = False
        self._completed = False
        self.next = current_time + self._durations[0]

    def _finish(self) -> None:
        self.done = True
        if not self._completed and self.on_complete is not None:
            self._completed = True
            self.on_complete(self)

    def _clamp_index(self) -> None:
        if self.index < 0:
            self.index = 0
        elif self.index >= len(self.frames):
            self.index = len(self.frames) - 1

    def __lt__(self, other: AnimationToken | float | int) -> bool:
        """
        Required for heap ordering.
        """
        if isinstance(other, AnimationToken):
            return self.next < other.next
        return self.next < float(other)

    def __repr__(self) -> str:
        return (
            f"AnimationToken(index={self.index}, next={self.next:.3f}, "
            f"loop={self.loop}, ping_pong={self.ping_pong})"
        )
