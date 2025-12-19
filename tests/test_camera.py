import pygame
import pytest
from pygame.rect import Rect

from pyscroll.camera import (
    BasicCamera,
    BoundsCamera,
    CutsceneCamera,
    DebugFlyCamera,
    FollowCamera,
    PlatformerCamera,
    ZoomCamera,
)


@pytest.fixture(scope="module", autouse=True)
def pygame_init():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def view_rect():
    return Rect(0, 0, 640, 480)


@pytest.fixture
def target_rect():
    return Rect(100, 100, 32, 32)


@pytest.mark.parametrize(
    "camera_class",
    [
        FollowCamera,
        BasicCamera,
        PlatformerCamera,
    ],
)
def test_camera_returns_tuple(camera_class, view_rect, target_rect):
    cam = camera_class()
    result = cam.update(view_rect, target_rect, dt=0.1)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(v, float) for v in result)


def test_follow_camera_lerp(view_rect, target_rect):
    cam = FollowCamera(lerp_factor=1.0)
    assert cam.update(view_rect, target_rect, 1.0) == target_rect.center


def test_follow_camera_deadzone(view_rect, target_rect):
    dz = Rect(0, 0, 200, 200)
    cam = FollowCamera(lerp_factor=1.0, deadzone=dz)

    dz.center = view_rect.center
    target_rect.center = view_rect.center

    assert cam.update(view_rect, target_rect, 1.0) == view_rect.center


def test_follow_camera_shake(view_rect, target_rect):
    cam = FollowCamera(lerp_factor=1.0)
    cam.shake(10)

    import random

    random.seed(12345)

    x, y = cam.update(view_rect, target_rect, 1.0)
    assert (x, y) != target_rect.center
    assert cam._shake_amount == 9


def test_platformer_camera_vertical_deadzone(view_rect, target_rect):
    cam = PlatformerCamera(lerp_factor=1.0, vertical_deadzone=200)

    target_rect.center = (view_rect.centerx, view_rect.centery + 50)
    x, y = cam.update(view_rect, target_rect, 1.0)

    assert y == view_rect.centery


def test_zoom_camera_interpolation(view_rect, target_rect):
    base = FollowCamera(lerp_factor=1.0)
    cam = ZoomCamera(base, zoom=1.0, zoom_speed=5.0)

    cam.set_zoom(2.0)
    cam.update(view_rect, target_rect, dt=0.1)

    assert cam.zoom > 1.0
    assert cam.zoom < 2.0


def test_cutscene_camera_moves(view_rect, target_rect):
    cam = CutsceneCamera(
        waypoints=[(0, 0), (100, 100)],
        duration=2.0,
        loop=False,
    )

    p1 = cam.update(view_rect, target_rect, 0.5)
    p2 = cam.update(view_rect, target_rect, 0.5)

    assert p1 != p2
    assert p2[0] > p1[0]
    assert p2[1] > p1[1]


def test_debug_camera_moves(view_rect, target_rect):
    cam = DebugFlyCamera(speed=100)
    cam.set_input(1, 0)

    x1, y1 = cam.update(view_rect, target_rect, 1.0)
    x2, y2 = cam.update(view_rect, target_rect, 1.0)

    assert x2 > x1
    assert y2 == y1


def test_bounds_camera_clamps_inside_world(view_rect, target_rect):
    world = Rect(0, 0, 500, 500)
    base = FollowCamera(lerp_factor=1.0)
    cam = BoundsCamera(base, world)

    target_rect.center = (2000, 2000)

    x, y = cam.update(view_rect, target_rect, dt=1.0)

    half_w = view_rect.width // 2
    half_h = view_rect.height // 2

    # X axis
    if world.width < view_rect.width:
        assert x == half_w
    else:
        assert world.left + half_w <= x <= world.right - half_w

    # Y axis
    if world.height < view_rect.height:
        assert y == half_h
    else:
        assert world.top + half_h <= y <= world.bottom - half_h


def test_bounds_camera_clamps_left_top(view_rect, target_rect):
    world = Rect(0, 0, 500, 500)
    base = FollowCamera(lerp_factor=1.0)
    cam = BoundsCamera(base, world)

    target_rect.center = (-500, -500)

    x, y = cam.update(view_rect, target_rect, dt=1.0)

    half_w = view_rect.width // 2
    half_h = view_rect.height // 2

    if world.width < view_rect.width:
        assert x == half_w
    else:
        assert x == world.left + half_w

    if world.height < view_rect.height:
        assert y == half_h
    else:
        assert y == world.top + half_h


def test_bounds_camera_shake_never_escapes_bounds(view_rect, target_rect):
    world = Rect(0, 0, 500, 500)
    base = FollowCamera(lerp_factor=1.0)
    cam = BoundsCamera(base, world)

    target_rect.center = world.center
    cam.shake(20)

    import random

    random.seed(12345)

    x, y = cam.update(view_rect, target_rect, dt=1.0)

    half_w = view_rect.width // 2
    half_h = view_rect.height // 2

    # X axis
    if world.width < view_rect.width:
        # Camera must remain inside the only valid clamped region
        assert x <= half_w
        assert x >= half_w - 20  # shake cannot exceed intensity
    else:
        assert world.left + half_w <= x <= world.right - half_w

    # Y axis
    if world.height < view_rect.height:
        assert y <= half_h
        assert y >= half_h - 20
    else:
        assert y <= world.bottom - half_h
        assert y >= world.top + half_h - 20


@pytest.mark.parametrize(
    "camera_class",
    [
        FollowCamera,
        BasicCamera,
        PlatformerCamera,
        DebugFlyCamera,
    ],
)
def test_shake_is_deterministic(camera_class, view_rect, target_rect):
    cam = camera_class()
    cam.shake(10)

    import random

    random.seed(999)

    x1, y1 = cam.update(view_rect, target_rect, dt=1.0)

    # Reset and repeat
    cam2 = camera_class()
    cam2.shake(10)
    random.seed(999)

    x2, y2 = cam2.update(view_rect, target_rect, dt=1.0)

    assert (x1, y1) == (x2, y2)
    assert cam._shake_amount == 9
    assert cam2._shake_amount == 9
    assert (x1, y1) != target_rect.center
