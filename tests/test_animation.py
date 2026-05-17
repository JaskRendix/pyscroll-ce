import random
from unittest.mock import MagicMock

import pytest

from pyscroll.animation import AnimationFrame, AnimationToken


@pytest.fixture
def surf():
    return MagicMock()


@pytest.fixture
def frames(surf):
    return [
        AnimationFrame(image=surf, duration=0.5),
        AnimationFrame(image=surf, duration=1.0),
    ]


@pytest.fixture
def positions():
    return {(1, 2, 0), (3, 4, 1)}


def test_initial_state(frames, positions):
    token = AnimationToken(positions, frames)
    assert token.index == 0
    assert token.next == frames[0].duration


def test_empty_frames_raises(positions):
    with pytest.raises(ValueError):
        AnimationToken(positions, [])


def test_negative_speed_multiplier_raises(frames, positions):
    with pytest.raises(ValueError):
        AnimationToken(positions, frames, speed_multiplier=-1)


def test_zero_speed_multiplier_raises(frames, positions):
    with pytest.raises(ValueError):
        AnimationToken(positions, frames, speed_multiplier=0)


def test_random_start_frame(frames, positions):
    token = AnimationToken(positions, frames, random_start_frame=True)
    assert token.index in (0, 1)


def test_random_jitter(frames, positions):
    token = AnimationToken(positions, frames, random_jitter=0.5)
    assert frames[0].duration <= token.next <= frames[0].duration + 0.5


@pytest.mark.parametrize(
    "loop,expected_index",
    [
        (True, 0),
        (False, 1),
    ],
)
def test_advance(frames, positions, loop, expected_index):
    token = AnimationToken(positions, frames, loop=loop)
    token.advance(0.5)
    token.advance(1.0)
    assert token.index == expected_index
    if not loop:
        assert token.done


def test_advance_non_looping_stays_on_last(frames, positions):
    token = AnimationToken(positions, frames, loop=False)
    token.advance(0.5)
    token.advance(1.0)
    assert token.done
    assert token.advance(99.0) == frames[-1]


def test_single_frame_looping(positions, surf):
    frames = [AnimationFrame(image=surf, duration=0.5)]
    token = AnimationToken(positions, frames, loop=True)
    token.advance(0.5)
    assert token.index == 0
    assert not token.done


def test_single_frame_non_looping(positions, surf):
    frames = [AnimationFrame(image=surf, duration=0.5)]
    token = AnimationToken(positions, frames, loop=False)
    token.advance(0.5)
    assert token.done
    assert token.index == 0


def test_update_advances(frames, positions):
    token = AnimationToken(positions, frames)
    frame = token.update(current_time=0.6, elapsed_time=0.1)
    assert frame == frames[1]
    assert token.index == 1


def test_update_non_looping_stop(frames, positions):
    token = AnimationToken(positions, frames, loop=False)
    token.update(current_time=0.6, elapsed_time=0.1)
    token.update(current_time=1.6, elapsed_time=0.5)
    assert token.done
    assert token.update(current_time=2.0, elapsed_time=0.5) == frames[-1]


def test_update_no_infinite_loop(positions):
    tiny = AnimationFrame(image=MagicMock(), duration=0.000001)
    token = AnimationToken(positions, [tiny], speed_multiplier=1000.0)
    token.update(current_time=1.0, elapsed_time=0.1)
    assert token.index == 0


@pytest.mark.parametrize(
    "loop,expect_reverse",
    [
        (True, True),
        (False, False),
    ],
)
def test_ping_pong(frames, positions, loop, expect_reverse):
    token = AnimationToken(positions, frames, ping_pong=True, loop=loop)
    token.advance(0.5)
    assert token.index == 1

    token.advance(1.5)
    if loop:
        assert token.index == 0
        assert token.direction == -1
    else:
        assert token.done


def test_on_complete_called_once(frames, positions):
    cb = MagicMock()
    token = AnimationToken(positions, frames, loop=False, on_complete=cb)
    token.advance(0.5)
    token.advance(1.0)
    token.advance(99.0)
    cb.assert_called_once_with(token)


def test_on_complete_not_called_for_looping(frames, positions):
    cb = MagicMock()
    token = AnimationToken(positions, frames, loop=True, on_complete=cb)
    for _ in range(10):
        token.advance(0.5)
    cb.assert_not_called()


def test_on_complete_ping_pong(frames, positions):
    cb = MagicMock()
    token = AnimationToken(
        positions, frames, loop=False, ping_pong=True, on_complete=cb
    )
    token.advance(0.5)
    token.advance(1.0)
    token.advance(1.5)
    cb.assert_called_once_with(token)


def test_reset_clears_done(frames, positions):
    token = AnimationToken(positions, frames, loop=False)
    token.advance(0.5)
    token.advance(1.0)
    assert token.done

    token.reset(current_time=2.0)
    assert not token.done
    assert token.index == 0
    assert token.next == frames[0].duration + 2.0


def test_reset_allows_callback_again(frames, positions):
    cb = MagicMock()
    token = AnimationToken(positions, frames, loop=False, on_complete=cb)
    token.advance(0.5)
    token.advance(1.0)
    token.reset()
    token.advance(0.5)
    token.advance(1.0)
    assert cb.call_count == 2


def test_reset_preserves_positions(frames, positions):
    token = AnimationToken(positions, frames)
    token.advance(0.5)
    token.reset()
    assert token.positions == positions


def test_lt_number(frames, positions):
    token = AnimationToken(positions, frames)
    assert (token < 10.0) is True
    assert (token < 0.1) is False


def test_lt_token(frames, positions):
    t1 = AnimationToken(positions, frames)
    t2 = AnimationToken(positions, frames, initial_time=1.0)
    assert t1 < t2


def test_repr(frames, positions):
    token = AnimationToken(positions, frames)
    r = repr(token)
    assert "AnimationToken" in r
    assert "loop=" in r
    assert "ping_pong=" in r


def test_animation_stress_many_tokens():
    positions = {(0, 0, 0)}
    surf = MagicMock()

    # Create a large batch of randomized animations
    tokens = []
    for _ in range(5000):
        frames = [
            AnimationFrame(
                image=surf,
                duration=random.uniform(0.0001, 1.0),
                frame_speed_multiplier=random.uniform(0.5, 2.0),
            )
            for _ in range(random.randint(1, 5))
        ]

        token = AnimationToken(
            positions=positions,
            frames=frames,
            initial_time=random.uniform(0, 5),
            loop=random.choice([True, False]),
            speed_multiplier=random.uniform(0.1, 5.0),
            ping_pong=random.choice([True, False]),
            random_jitter=random.uniform(0.0, 0.2),
            random_start_frame=random.choice([True, False]),
        )
        tokens.append(token)

    # Randomized update cycles
    for _ in range(200):
        current_time = random.uniform(0, 10)
        for token in tokens:
            frame = token.update(current_time=current_time, elapsed_time=None)

            assert token.index >= 0
            assert token.index < len(token.frames)
            assert frame is token.current_frame

            # Only enforce next >= current_time if animation is still active
            if not token.done:
                assert token.next >= 0
                assert token.next >= token._durations[token.index]

    # If we reach this point, the stress test passed
    assert True
