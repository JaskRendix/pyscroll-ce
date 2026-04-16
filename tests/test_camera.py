import random
from unittest.mock import MagicMock

import pytest
from pygame.rect import Rect

from pyscroll.camera import (
    BasicCamera,
    BoundsCamera,
    CutsceneCamera,
    DebugFlyCamera,
    FollowCamera,
    PlatformerCamera,
    RailCamera,
    SplitFollowCamera,
    ZoomCamera,
)


@pytest.mark.parametrize(
    "camera_class",
    [
        pytest.param(FollowCamera, id="follow"),
        pytest.param(BasicCamera, id="basic"),
        pytest.param(PlatformerCamera, id="platformer"),
        pytest.param(DebugFlyCamera, id="debug_fly"),
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

    if world.width < view_rect.width:
        assert x == float(world.centerx)
    else:
        assert world.left + half_w <= x <= world.right - half_w

    if world.height < view_rect.height:
        assert y == float(world.centery)
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
        assert x == float(world.centerx)
    else:
        assert x == world.left + half_w

    if world.height < view_rect.height:
        assert y == float(world.centery)
    else:
        assert y == world.top + half_h


def test_bounds_camera_shake_clamped_by_default(view_rect, target_rect):
    world = Rect(0, 0, 2000, 2000)
    base = FollowCamera(lerp_factor=1.0)
    cam = BoundsCamera(base, world)

    target_rect.center = world.center
    cam.shake(100)

    half_w = view_rect.width // 2
    half_h = view_rect.height // 2

    for _ in range(20):
        x, y = cam.update(view_rect, target_rect, dt=1.0)
        assert world.left + half_w <= x <= world.right - half_w
        assert world.top + half_h <= y <= world.bottom - half_h


def test_bounds_camera_shake_unclamped(view_rect, target_rect):
    world = Rect(0, 0, 2000, 2000)
    base = FollowCamera(lerp_factor=1.0)
    cam = BoundsCamera(base, world, clamp_shake=False)

    half_w = view_rect.width // 2
    half_h = view_rect.height // 2

    # Place target exactly at the minimum clamped position
    # so any shake pushes it outside bounds
    target_rect.center = (world.left + half_w, world.top + half_h)
    cam.shake(50)

    random.seed(42)

    escaped = False
    for _ in range(20):
        x, y = cam.update(view_rect, target_rect, dt=1.0)
        if (
            x < world.left + half_w
            or x > world.right - half_w
            or y < world.top + half_h
            or y > world.bottom - half_h
        ):
            escaped = True
            break

    assert escaped, "shake with clamp_shake=False should be able to escape bounds"


@pytest.mark.parametrize(
    "camera_class",
    [
        pytest.param(FollowCamera, id="follow"),
        pytest.param(BasicCamera, id="basic"),
        pytest.param(PlatformerCamera, id="platformer"),
        pytest.param(DebugFlyCamera, id="debug_fly"),
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


def test_cutscene_on_complete_called_once(view_rect, target_rect):
    callback = MagicMock()
    cam = CutsceneCamera(
        waypoints=[(0, 0), (100, 100)],
        duration=1.0,
        loop=False,
        on_complete=callback,
    )
    # run past completion
    for _ in range(100):
        cam.update(view_rect, target_rect, 0.1)
    callback.assert_called_once()


def test_cutscene_on_complete_not_called_for_looping(view_rect, target_rect):
    callback = MagicMock()
    cam = CutsceneCamera(
        waypoints=[(0, 0), (100, 100)],
        duration=1.0,
        loop=True,
        on_complete=callback,
    )
    for _ in range(100):
        cam.update(view_rect, target_rect, 0.1)
    callback.assert_not_called()


def test_cutscene_reset_allows_callback_again(view_rect, target_rect):
    callback = MagicMock()
    cam = CutsceneCamera(
        waypoints=[(0, 0), (100, 100)],
        duration=1.0,
        loop=False,
        on_complete=callback,
    )
    for _ in range(20):
        cam.update(view_rect, target_rect, 0.1)
    assert callback.call_count == 1

    cam.reset()
    for _ in range(20):
        cam.update(view_rect, target_rect, 0.1)
    assert callback.call_count == 2


def test_cutscene_reset_restarts_movement(view_rect, target_rect):
    cam = CutsceneCamera(
        waypoints=[(0, 0), (100, 100)],
        duration=1.0,
        loop=False,
    )
    # run to completion
    for _ in range(20):
        cam.update(view_rect, target_rect, 0.1)
    end_pos = cam.update(view_rect, target_rect, 0.1)

    cam.reset()
    start_pos = cam.update(view_rect, target_rect, 0.001)

    assert start_pos[0] < end_pos[0]
    assert start_pos[1] < end_pos[1]


def test_cutscene_single_waypoint(view_rect, target_rect):
    cam = CutsceneCamera(waypoints=[(50, 75)], duration=1.0)
    pos = cam.update(view_rect, target_rect, 0.1)
    assert pos == (50.0, 75.0)


def test_cutscene_loop_resets_time(view_rect, target_rect):
    cam = CutsceneCamera(
        waypoints=[(0, 0), (100, 100)],
        duration=1.0,
        loop=True,
    )
    for _ in range(11):
        cam.update(view_rect, target_rect, 0.1)
    # after looping, time should be reset and position near start
    assert cam.time < 1.0


def test_shake_is_additive(view_rect, target_rect):
    cam = FollowCamera()
    cam.shake(10)
    cam.shake(20)
    assert cam._shake_amount == 30


def test_shake_capped_at_100(view_rect, target_rect):
    cam = FollowCamera()
    cam.shake(80)
    cam.shake(80)
    assert cam._shake_amount == 100


def test_shake_decays_each_frame(view_rect, target_rect):
    cam = FollowCamera(lerp_factor=1.0)
    cam.shake(5)
    for _ in range(5):
        cam.update(view_rect, target_rect, 1.0)
    assert cam._shake_amount == 0


def test_platformer_camera_follows_up_immediately(view_rect, target_rect):
    cam = PlatformerCamera(lerp_factor=1.0, vertical_deadzone=200)
    # target is above the view center by less than deadzone
    target_rect.center = (view_rect.centerx, view_rect.centery - 50)
    x, y = cam.update(view_rect, target_rect, 1.0)
    # should follow upward even within deadzone distance
    assert y < view_rect.centery


def test_platformer_camera_deadzone_only_applies_downward(view_rect, target_rect):
    cam = PlatformerCamera(lerp_factor=1.0, vertical_deadzone=200)
    # target is below the view center by less than deadzone
    target_rect.center = (view_rect.centerx, view_rect.centery + 50)
    x, y = cam.update(view_rect, target_rect, 1.0)
    # should NOT follow downward within deadzone
    assert y == view_rect.centery


def test_bounds_camera_shake_forwarded_to_base(view_rect, target_rect):
    world = Rect(0, 0, 2000, 2000)
    base = FollowCamera(lerp_factor=1.0)
    cam = BoundsCamera(base, world)
    cam.shake(10)
    assert base._shake_amount == 10
    assert cam._shake_amount == 0


def test_bounds_camera_own_shake_amount_always_zero(view_rect, target_rect):
    world = Rect(0, 0, 2000, 2000)
    base = FollowCamera(lerp_factor=1.0)
    cam = BoundsCamera(base, world)
    cam.shake(50)
    target_rect.center = world.center
    cam.update(view_rect, target_rect, 1.0)
    assert cam._shake_amount == 0


def test_zoom_camera_shake_forwarded_to_base(view_rect, target_rect):
    base = FollowCamera(lerp_factor=1.0)
    cam = ZoomCamera(base, zoom=1.0)
    cam.shake(10)
    assert base._shake_amount == 10
    assert cam._shake_amount == 0


def test_zoom_camera_own_shake_amount_always_zero(view_rect, target_rect):
    base = FollowCamera(lerp_factor=1.0)
    cam = ZoomCamera(base, zoom=1.0)
    cam.shake(50)
    cam.update(view_rect, target_rect, 1.0)
    assert cam._shake_amount == 0


def test_zoom_camera_shake_visible_in_output(view_rect, target_rect):
    base = FollowCamera(lerp_factor=1.0)
    cam = ZoomCamera(base, zoom=1.0)
    cam.shake(20)
    random.seed(42)
    x, y = cam.update(view_rect, target_rect, 1.0)
    assert (x, y) != target_rect.center


def test_debug_camera_set_position(view_rect, target_rect):
    cam = DebugFlyCamera()
    cam.set_position(200.0, 300.0)
    x, y = cam.update(view_rect, target_rect, 0.0)
    assert x == 200.0
    assert y == 300.0


def test_debug_camera_set_position_overrides_lazy_init(view_rect, target_rect):
    cam = DebugFlyCamera()
    cam.set_position(999.0, 888.0)
    # should use set position, not current_view.center
    x, y = cam.update(view_rect, target_rect, 0.0)
    assert x == 999.0
    assert y == 888.0


def test_debug_camera_set_position_mid_flight(view_rect, target_rect):
    cam = DebugFlyCamera(speed=100)
    cam.set_input(1, 0)
    cam.update(view_rect, target_rect, 1.0)  # move to ~(500, 400)
    cam.set_position(0.0, 0.0)
    x, y = cam.update(view_rect, target_rect, 0.0)
    assert x == 0.0
    assert y == 0.0


def test_catmull_rom_passes_through_waypoints(view_rect, target_rect):
    waypoints = [(0.0, 0.0), (100.0, 50.0), (200.0, 0.0), (300.0, 50.0)]
    cam = CutsceneCamera(waypoints, duration=3.0, interpolation="catmull_rom")

    # at time=0, should be at first waypoint
    pos = cam.update(view_rect, target_rect, 0.0)
    assert pos == pytest.approx((0.0, 0.0), abs=1.0)


def test_catmull_rom_smoother_than_linear(view_rect, target_rect):
    waypoints = [(0.0, 0.0), (100.0, 100.0), (200.0, 0.0)]

    cam_linear = CutsceneCamera(waypoints, duration=2.0, interpolation="linear")
    cam_spline = CutsceneCamera(waypoints, duration=2.0, interpolation="catmull_rom")

    # advance both to just before the midpoint
    dt = 0.99
    pos_linear = cam_linear.update(view_rect, target_rect, dt)
    pos_spline = cam_spline.update(view_rect, target_rect, dt)

    # both should be near (100, 100) but spline approaches more smoothly
    assert abs(pos_spline[0] - 100.0) <= abs(pos_linear[0] - 100.0) + 1.0


def test_catmull_rom_invalid_interpolation():
    with pytest.raises(ValueError):
        CutsceneCamera([(0, 0), (100, 100)], duration=1.0, interpolation="bezier")


def test_catmull_rom_static_method():
    p0 = (0.0, 0.0)
    p1 = (0.0, 0.0)
    p2 = (1.0, 1.0)
    p3 = (1.0, 1.0)

    # at t=0 should be at p1
    result = CutsceneCamera._catmull_rom(p0, p1, p2, p3, 0.0)
    assert result == pytest.approx((0.0, 0.0), abs=1e-6)

    # at t=1 should be at p2
    result = CutsceneCamera._catmull_rom(p0, p1, p2, p3, 1.0)
    assert result == pytest.approx((1.0, 1.0), abs=1e-6)


def test_catmull_rom_loop_wraps_control_points(view_rect, target_rect):
    waypoints = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
    cam = CutsceneCamera(
        waypoints, duration=4.0, loop=True, interpolation="catmull_rom"
    )
    # just run through two full loops without error
    for _ in range(80):
        cam.update(view_rect, target_rect, 0.1)
    assert cam.time < 4.0


def test_linear_interpolation_unchanged(view_rect, target_rect):
    waypoints = [(0.0, 0.0), (100.0, 100.0)]
    cam = CutsceneCamera(waypoints, duration=1.0, interpolation="linear")
    pos = cam.update(view_rect, target_rect, 0.5)
    assert pos == pytest.approx((50.0, 50.0), abs=1.0)


def test_split_follow_fallback_to_target_rect(view_rect, target_rect):
    cam = SplitFollowCamera(lerp_factor=1.0)
    pos = cam.update(view_rect, target_rect, 1.0)
    assert pos == pytest.approx(target_rect.center, abs=1.0)


def test_split_follow_single_target(view_rect, target_rect):
    cam = SplitFollowCamera(lerp_factor=1.0)
    t1 = Rect(200, 200, 32, 32)
    cam.targets = [t1]
    pos = cam.update(view_rect, target_rect, 1.0)
    assert pos == pytest.approx(t1.center, abs=1.0)


def test_split_follow_midpoint(view_rect, target_rect):
    cam = SplitFollowCamera(lerp_factor=1.0)
    t1 = Rect(0, 0, 32, 32)
    t2 = Rect(200, 200, 32, 32)
    cam.targets = [t1, t2]
    pos = cam.update(view_rect, target_rect, 1.0)
    mid_x = (t1.centerx + t2.centerx) / 2
    mid_y = (t1.centery + t2.centery) / 2
    assert pos == pytest.approx((mid_x, mid_y), abs=1.0)


def test_split_follow_zoom_decreases_with_separation(view_rect, target_rect):
    cam = SplitFollowCamera(
        lerp_factor=1.0,
        zoom_speed=100.0,
        min_zoom=0.5,
        max_zoom=2.0,
        max_distance=400.0,
    )
    t1 = Rect(0, 0, 32, 32)
    t2 = Rect(400, 0, 32, 32)  # max separation
    cam.targets = [t1, t2]

    for _ in range(30):
        cam.update(view_rect, target_rect, 0.1)

    assert cam.zoom == pytest.approx(0.5, abs=0.05)


def test_split_follow_zoom_increases_when_close(view_rect, target_rect):
    cam = SplitFollowCamera(
        lerp_factor=1.0,
        zoom_speed=100.0,
        min_zoom=0.5,
        max_zoom=2.0,
        max_distance=400.0,
    )
    t1 = Rect(100, 100, 32, 32)
    t2 = Rect(100, 100, 32, 32)  # same position
    cam.targets = [t1, t2]

    cam.zoom = 0.5  # start zoomed out
    for _ in range(30):
        cam.update(view_rect, target_rect, 0.1)

    assert cam.zoom == pytest.approx(2.0, abs=0.05)


def test_split_follow_zoom_clamped(view_rect, target_rect):
    cam = SplitFollowCamera(min_zoom=0.5, max_zoom=2.0)
    t1 = Rect(0, 0, 32, 32)
    t2 = Rect(10000, 0, 32, 32)  # extreme separation
    cam.targets = [t1, t2]

    for _ in range(100):
        cam.update(view_rect, target_rect, 0.1)

    assert cam.zoom >= 0.5
    assert cam.zoom <= 2.0


def test_split_follow_three_targets_midpoint(view_rect, target_rect):
    cam = SplitFollowCamera(lerp_factor=1.0)
    t1 = Rect(0, 0, 32, 32)
    t2 = Rect(300, 0, 32, 32)
    t3 = Rect(150, 300, 32, 32)
    cam.targets = [t1, t2, t3]
    pos = cam.update(view_rect, target_rect, 1.0)
    mid_x = (t1.centerx + t2.centerx + t3.centerx) / 3
    mid_y = (t1.centery + t2.centery + t3.centery) / 3
    assert pos == pytest.approx((mid_x, mid_y), abs=1.0)


def test_rail_camera_requires_at_least_two_points():
    with pytest.raises(ValueError):
        RailCamera(rail=[(0, 0)])


def test_rail_camera_stays_on_rail(view_rect, target_rect):
    rail = [(0.0, 0.0), (500.0, 0.0)]
    cam = RailCamera(rail=rail, lerp_factor=1.0)

    # target is off the rail vertically
    target_rect.center = (250, 300)
    x, y = cam.update(view_rect, target_rect, 1.0)

    # y should be clamped to rail (y=0), x should be on segment
    assert y == pytest.approx(0.0, abs=1.0)
    assert 0.0 <= x <= 500.0


def test_rail_camera_follows_along_rail(view_rect, target_rect):
    rail = [(0.0, 0.0), (500.0, 0.0)]
    cam = RailCamera(rail=rail, lerp_factor=1.0)

    target_rect.center = (100, 0)
    x1, _ = cam.update(view_rect, target_rect, 1.0)

    target_rect.center = (400, 0)
    x2, _ = cam.update(view_rect, target_rect, 1.0)

    assert x2 > x1


def test_rail_camera_clamps_to_endpoints(view_rect, target_rect):
    rail = [(0.0, 0.0), (100.0, 0.0)]
    cam = RailCamera(rail=rail, lerp_factor=1.0)

    target_rect.center = (9999, 0)
    x, y = cam.update(view_rect, target_rect, 1.0)

    assert x == pytest.approx(100.0, abs=1.0)
    assert y == pytest.approx(0.0, abs=1.0)


def test_rail_camera_multi_segment(view_rect, target_rect):
    rail = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)]
    cam = RailCamera(rail=rail, lerp_factor=1.0)

    # target is closest to second segment
    target_rect.center = (150, 50)
    x, y = cam.update(view_rect, target_rect, 1.0)

    assert x == pytest.approx(100.0, abs=1.0)
    assert 0.0 <= y <= 100.0


def test_rail_camera_loop_connects_last_to_first(view_rect, target_rect):
    rail = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
    cam = RailCamera(rail=rail, lerp_factor=1.0, loop=True)

    # target is closest to the closing segment (last -> first)
    target_rect.center = (-50, 50)
    x, y = cam.update(view_rect, target_rect, 1.0)

    assert x == pytest.approx(0.0, abs=1.0)
    assert 0.0 <= y <= 100.0


def test_rail_camera_degenerate_segment(view_rect, target_rect):
    rail = [(50.0, 50.0), (50.0, 50.0), (200.0, 200.0)]
    cam = RailCamera(rail=rail, lerp_factor=1.0)
    target_rect.center = (100, 100)
    pos = cam.update(view_rect, target_rect, 1.0)
    assert pos is not None


def test_rail_camera_static_closest_point_midpoint():
    a = (0.0, 0.0)
    b = (100.0, 0.0)
    p = (50.0, 50.0)
    result = RailCamera._closest_point_on_segment(a, b, p)
    assert result == pytest.approx((50.0, 0.0), abs=1e-6)


def test_rail_camera_static_closest_point_clamped_start():
    a = (0.0, 0.0)
    b = (100.0, 0.0)
    p = (-50.0, 0.0)
    result = RailCamera._closest_point_on_segment(a, b, p)
    assert result == pytest.approx((0.0, 0.0), abs=1e-6)


def test_rail_camera_static_closest_point_clamped_end():
    a = (0.0, 0.0)
    b = (100.0, 0.0)
    p = (150.0, 0.0)
    result = RailCamera._closest_point_on_segment(a, b, p)
    assert result == pytest.approx((100.0, 0.0), abs=1e-6)
