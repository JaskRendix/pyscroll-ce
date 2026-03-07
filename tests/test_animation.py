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


@pytest.mark.parametrize(
    "loop,expected_index",
    [
        pytest.param(True, 0, id="loop_true"),
        pytest.param(False, 1, id="loop_false"),
    ],
)
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


@pytest.mark.parametrize(
    "number,expected",
    [
        pytest.param(10.0, True, id="number_large"),
        pytest.param(0.1, False, id="number_small"),
    ],
)
def test_lt_comparison_with_number(frames, positions, number, expected):
    token = AnimationToken(positions, frames)
    assert (token < number) is expected


def test_lt_comparison_with_other_token(frames, positions):
    token1 = AnimationToken(positions, frames)
    token2 = AnimationToken(positions, frames, initial_time=1.0)
    assert token1 < token2


@pytest.mark.parametrize(
    "token_speed,frame_speed,expected",
    [
        pytest.param(2.0, None, 0.25, id="token_speed_only"),
        pytest.param(2.0, 2.0, 0.125, id="token_and_frame_speed"),
        pytest.param(1.0, 2.0, 0.25, id="frame_speed_only"),
    ],
)
def test_speed_multiplier_combinations(positions, token_speed, frame_speed, expected):
    surf = MagicMock()
    frame_kwargs = {"image": surf, "duration": 0.5}
    if frame_speed:
        frame_kwargs["frame_speed_multiplier"] = frame_speed
    frames = [AnimationFrame(**frame_kwargs)]

    token = AnimationToken(positions, frames, speed_multiplier=token_speed)
    assert pytest.approx(token.next, 0.01) == expected


@pytest.mark.parametrize(
    "loop,check_direction",
    [
        pytest.param(True, True, id="ping_pong_looping"),
        pytest.param(False, False, id="ping_pong_non_looping"),
    ],
)
def test_ping_pong_behavior(frames, positions, loop, check_direction):
    token = AnimationToken(positions, frames, ping_pong=True, loop=loop)
    token.advance(0.5)
    if check_direction:
        assert token.index == 1
        assert token.direction == 1
    token.advance(1.5)
    if loop:
        assert token.index == 0
        assert token.direction == -1
        assert not token.done
    else:
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
