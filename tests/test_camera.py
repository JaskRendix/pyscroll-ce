import pygame
import pytest
from pygame.rect import Rect

from pyscroll.camera import Camera


@pytest.fixture(scope="module", autouse=True)
def pygame_init():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def camera():
    return Camera(lerp_factor=0.5, deadzone=None)


@pytest.fixture
def view_rect():
    return Rect(0, 0, 640, 480)


@pytest.fixture
def target_rect():
    return Rect(100, 100, 32, 32)


def test_camera_init_defaults():
    cam = Camera()
    assert cam.lerp_factor == 1.0
    assert cam.deadzone is None
    assert cam._shake_amount == 0


def test_camera_init_with_deadzone():
    dz = Rect(0, 0, 200, 200)
    cam = Camera(lerp_factor=0.3, deadzone=dz)
    assert cam.deadzone == dz
    assert cam.lerp_factor == 0.3


@pytest.mark.parametrize(
    "lerp_factor, dt",
    [
        (0.0, 1.0),  # no movement
        (1.0, 1.0),  # instant snap
        (0.5, 0.016),  # typical frame
        (0.5, 0.5),  # half second
    ],
)
def test_camera_lerp_behavior(lerp_factor, dt, view_rect, target_rect):
    cam = Camera(lerp_factor=lerp_factor)
    current_center = view_rect.center
    target_center = target_rect.center

    new_x, new_y = cam.update(view_rect, target_rect, dt)

    if lerp_factor == 0.0:
        # No movement at all
        assert (new_x, new_y) == current_center

    elif lerp_factor == 1.0:
        # Instant snap to target
        assert (new_x, new_y) == target_center

    else:
        # Camera should move *toward* the target, regardless of direction
        if target_center[0] > current_center[0]:
            assert current_center[0] < new_x < target_center[0]
        else:
            assert target_center[0] < new_x < current_center[0]

        if target_center[1] > current_center[1]:
            assert current_center[1] < new_y < target_center[1]
        else:
            assert target_center[1] < new_y < current_center[1]


def test_camera_deadzone_no_movement(view_rect, target_rect):
    dz = Rect(0, 0, 200, 200)
    cam = Camera(lerp_factor=1.0, deadzone=dz)

    # Place deadzone centered on camera
    dz.center = view_rect.center

    # Target inside deadzone → no movement
    target_rect.center = view_rect.center
    new_center = cam.update(view_rect, target_rect, dt=1.0)

    assert new_center == view_rect.center


def test_camera_deadzone_movement(view_rect, target_rect):
    dz = Rect(0, 0, 50, 50)
    cam = Camera(lerp_factor=1.0, deadzone=dz)

    # Target outside deadzone → movement happens
    new_center = cam.update(view_rect, target_rect, dt=1.0)
    assert new_center != view_rect.center


def test_camera_shake_applies_random_offset(view_rect, target_rect):
    cam = Camera(lerp_factor=1.0)
    cam.shake(10)

    # Deterministic randomness
    import random

    random.seed(12345)

    new_x, new_y = cam.update(view_rect, target_rect, dt=1.0)

    # Should not equal exact target center
    assert (new_x, new_y) != target_rect.center

    # Shake should decay
    assert cam._shake_amount == 9


def test_camera_shake_stops_at_zero(view_rect, target_rect):
    cam = Camera(lerp_factor=1.0)
    cam.shake(1)

    # First update applies shake
    cam.update(view_rect, target_rect, dt=1.0)
    assert cam._shake_amount == 0

    # Second update should have no shake
    new_x, new_y = cam.update(view_rect, target_rect, dt=1.0)
    assert (new_x, new_y) == target_rect.center


def test_camera_update_returns_tuple(camera, view_rect, target_rect):
    result = camera.update(view_rect, target_rect, dt=0.1)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(v, float) for v in result)
