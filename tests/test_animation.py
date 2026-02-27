from unittest.mock import MagicMock

import pytest
from pyscroll.animation import AnimationFrame, AnimationToken


@pytest.fixture
def frames():
    surf1 = MagicMock()
    surf2 = MagicMock()
    return [
        AnimationFrame(image=surf1, duration=0.5),
        AnimationFrame(image=surf2, duration=1.0),
    ]


@pytest.fixture
def positions():
    return {(1, 2, 0), (3, 4, 1)}


def test_initial_state(frames, positions):
    token = AnimationToken(positions, frames)
    assert token.index == 0
    assert token.next == frames[0].duration


@pytest.mark.parametrize("loop,expected_index", [(True, 0), (False, 1)])
def test_advance(frames, positions, loop, expected_index):
    token = AnimationToken(positions, frames, loop=loop)
    token.advance(0.5)
    token.advance(1.0)
    assert token.index == expected_index
    if not loop:
        assert token.done


def test_non_looping_stays_on_last_frame(frames, positions):
    token = AnimationToken(positions, frames, loop=False)
    token.advance(0.5)
    token.advance(1.0)
    repeat_frame = token.advance(1.0)
    assert repeat_frame == frames[1]
    assert token.done


def test_update_advances(frames, positions):
    token = AnimationToken(positions, frames, loop=True)
    frame = token.update(current_time=0.6, elapsed_time=0.1)
    assert frame == frames[1]
    assert token.index == 1


def test_update_non_looping_stop(frames, positions):
    token = AnimationToken(positions, frames, loop=False)
    token.update(current_time=0.6, elapsed_time=0.1)
    token.update(current_time=1.6, elapsed_time=0.5)
    frame = token.update(current_time=2.1, elapsed_time=0.5)
    assert frame == frames[1]
    assert token.done


def test_empty_frame_list_raises(positions):
    with pytest.raises(ValueError):
        AnimationToken(positions, [], loop=True)


@pytest.mark.parametrize("number,expected", [(10.0, True), (0.1, False)])
def test_lt_comparison_with_number(frames, positions, number, expected):
    token = AnimationToken(positions, frames)
    assert (token < number) is expected


def test_lt_comparison_with_other_token(frames, positions):
    token1 = AnimationToken(positions, frames)
    token2 = AnimationToken(positions, frames, initial_time=1.0)
    assert token1 < token2


def test_speed_multiplier_affects_duration(frames, positions):
    token = AnimationToken(positions, frames, speed_multiplier=2.0)
    assert pytest.approx(token.next, 0.01) == frames[0].duration / 2.0


def test_frame_specific_speed_multiplier(positions):
    surf = MagicMock()
    frames = [
        AnimationFrame(image=surf, duration=1.0, frame_speed_multiplier=2.0),
    ]
    token = AnimationToken(positions, frames, speed_multiplier=2.0)
    assert pytest.approx(token.next, 0.001) == 0.25


def test_ping_pong_reverses(frames, positions):
    token = AnimationToken(positions, frames, ping_pong=True, loop=True)
    token.advance(0.5)
    assert token.index == 1
    assert token.direction == 1
    token.advance(1.5)
    assert token.index == 0
    assert token.direction == -1


def test_ping_pong_non_looping_stops(frames, positions):
    token = AnimationToken(positions, frames, ping_pong=True, loop=False)
    token.advance(0.5)
    token.advance(1.5)
    assert token.done
    assert token.index == 0


def test_random_jitter(frames, positions):
    token = AnimationToken(positions, frames, random_jitter=0.5)
    assert frames[0].duration <= token.next <= frames[0].duration + 0.5


def test_update_no_infinite_loop(frames, positions):
    tiny_frame = AnimationFrame(image=MagicMock(), duration=0.000001)
    token = AnimationToken(positions, [tiny_frame], speed_multiplier=1000.0)
    token.update(current_time=1.0, elapsed_time=0.1)
    assert token.index == 0
