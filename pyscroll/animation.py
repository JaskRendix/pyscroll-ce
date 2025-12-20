from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from pygame.surface import Surface

TimeLike = float | int

__all__ = ("AnimationFrame", "AnimationToken")


@dataclass(frozen=True)
class AnimationFrame:
    """
    Represents a single frame in an animation.

    Attributes:
        image: The image surface to display.
        duration: Base duration this frame should be shown, in seconds.
        frame_speed_multiplier: A multiplier specific to this frame.
            Allows for complex, non-uniform pacing.
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
        next: Time value when the next frame should appear.
        loop: If True, animation loops; if False, plays once.
        ping_pong: If True, animation reverses direction when reaching an end.
        direction: 1 for forward, -1 for backward.
        done: Indicates whether a non-looping animation has completed.
        speed_multiplier: Global factor applied to all frame durations.
    """

    __slots__ = (
        "positions",
        "frames",
        "next",
        "index",
        "loop",
        "done",
        "speed_multiplier",
        "ping_pong",
        "direction",
    )

    def __init__(
        self,
        positions: set[tuple[int, int, int]],
        frames: Sequence[AnimationFrame],
        initial_time: float = 0.0,
        loop: bool = True,
        speed_multiplier: float = 1.0,
        ping_pong: bool = False,
        random_jitter: float = 0.0,
    ) -> None:
        """
        Initializes an AnimationToken instance with full feature set.
        """
        if not frames:
            raise ValueError("Frames sequence cannot be empty.")
        if speed_multiplier <= 0:
            raise ValueError("Speed multiplier must be greater than zero.")

        self.positions = positions
        self.frames = tuple(frames)
        self.index = 0

        self.speed_multiplier = speed_multiplier
        self.loop = loop
        self.ping_pong = ping_pong
        self.done = False
        self.direction = 1

        initial_frame = self.frames[0]
        combined_multiplier = (
            self.speed_multiplier * initial_frame.frame_speed_multiplier
        )

        if combined_multiplier <= 0:
            initial_duration = initial_frame.duration
        else:
            initial_duration = initial_frame.duration / combined_multiplier

        jitter_offset = random.uniform(0.0, random_jitter) if random_jitter > 0 else 0.0

        self.next = initial_duration + initial_time + jitter_offset

    def advance(self, current_time: TimeLike) -> AnimationFrame:
        """
        Advances to the next frame in the animation sequence, handling loop/ping-pong.
        """
        if self.done:
            return self.frames[self.index]

        if self.ping_pong:
            is_at_end = self.index == len(self.frames) - 1 and self.direction == 1
            is_at_start = self.index == 0 and self.direction == -1

            if is_at_end:
                self.direction = -1
            elif is_at_start:
                if not self.loop:
                    self.done = True
                    return self.frames[self.index]
                self.direction = 1

            self.index += self.direction

            if not self.loop and self.index == 0 and self.direction == -1:
                self.done = True
                return self.frames[self.index]

        else:
            if self.index == len(self.frames) - 1:
                if self.loop:
                    self.index = 0
                else:
                    self.done = True
                    return self.frames[self.index]
            else:
                self.index += 1

        next_frame = self.frames[self.index]

        combined_multiplier = self.speed_multiplier * next_frame.frame_speed_multiplier

        if combined_multiplier <= 0:
            effective_duration = next_frame.duration
        else:
            effective_duration = next_frame.duration / combined_multiplier

        self.next = effective_duration + current_time

        return next_frame

    def update(self, current_time: TimeLike, elapsed_time: TimeLike) -> AnimationFrame:
        if self.done:
            return self.frames[self.index]

        safety_counter = 0
        max_steps = len(self.frames) * 4

        while current_time >= self.next:
            self.advance(self.next)

            safety_counter += 1
            if safety_counter > max_steps:
                break

        return self.frames[self.index]

    def __lt__(self, other: AnimationToken | float | int) -> bool:
        """
        Compares this token's next frame time with another, essential for min-heap.
        """
        if isinstance(other, AnimationToken):
            return self.next < other.next
        else:
            return self.next < float(other)

    def __repr__(self) -> str:
        return f"AnimationToken(index={self.index}, next={self.next:.3f}, loop={self.loop}, ping_pong={self.ping_pong})"
