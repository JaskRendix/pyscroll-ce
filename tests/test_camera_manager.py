import pytest
from pygame.rect import Rect

from pyscroll.camera import BaseCamera
from pyscroll.camera_manager import CameraManager


class DummyCamera(BaseCamera):
    """Camera that always returns a fixed point."""

    def __init__(self, pos):
        super().__init__()
        self.pos = pos
        self.calls = 0

    def update(self, current_view, target_rect, dt):
        self.calls += 1
        return self.pos


class TargetCamera(BaseCamera):
    """Camera that always returns the target center."""

    def update(self, current_view, target_rect, dt):
        return target_rect.center


@pytest.fixture
def view():
    return Rect(0, 0, 800, 600)


def test_initial_camera_used(view, target_rect):
    cam = DummyCamera((0, 0))
    manager = CameraManager(cam)

    pos = manager.update(view, target_rect, 0.016)
    assert pos == (0, 0)
    assert cam.calls == 1


def test_instant_switch(view, target_rect):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))

    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=0)

    pos = manager.update(view, target_rect, 0.016)
    assert pos == (100, 100)
    assert cam_b.calls == 1
    assert manager.next_cam is None


@pytest.mark.parametrize(
    "num_updates,expected_pos_check",
    [
        pytest.param(1, "between_0_100", id="transition_starts"),
        pytest.param(30, "approx_50", id="transition_progress"),
        pytest.param(60, "exact_100_100", id="transition_completes"),
    ],
)
def test_transition_stages(view, target_rect, num_updates, expected_pos_check):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)

    for _ in range(num_updates):
        pos = manager.update(view, target_rect, 1 / 60)

    if expected_pos_check == "between_0_100":
        assert 0 < pos[0] < 100
        assert 0 < pos[1] < 100
        assert manager.next_cam is not None
    elif expected_pos_check == "approx_50":
        assert pos[0] == pytest.approx(50, abs=2)
        assert pos[1] == pytest.approx(50, abs=2)
        assert manager.next_cam is not None
    elif expected_pos_check == "exact_100_100":
        assert pos == (100, 100)
        assert manager.current is cam_b
        assert manager.next_cam is None


def test_target_camera(view, target_rect):
    cam = TargetCamera()
    manager = CameraManager(cam)

    pos = manager.update(view, target_rect, 0.016)
    assert pos == target_rect.center


def test_transition_interrupted_by_new_camera(view, target_rect):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))
    cam_c = DummyCamera((200, 200))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)
    manager.update(view, target_rect, 0.5)  # mid-transition
    manager.set_camera(cam_c, duration=0)  # instant switch
    pos = manager.update(view, target_rect, 0.016)
    assert pos == (200, 200)
    assert manager.next_cam is None


def test_transition_smoothstep_is_smooth(view, target_rect):
    """Verify smoothstep produces S-curve: slow start, fast middle, slow end."""
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 0))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)

    positions = []
    for _ in range(60):
        x, _ = manager.update(view, target_rect, 1 / 60)
        positions.append(x)

    # mid-section deltas should be larger than start/end deltas
    start_delta = positions[5] - positions[0]
    mid_delta = positions[32] - positions[27]
    end_delta = positions[59] - positions[54]

    assert mid_delta > start_delta
    assert mid_delta > end_delta


def test_no_transition_no_next_cam(view, target_rect):
    cam = DummyCamera((50, 50))
    manager = CameraManager(cam)
    assert manager.next_cam is None
    manager.update(view, target_rect, 0.016)
    assert manager.next_cam is None


def test_set_camera_resets_transition_state(view, target_rect):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)
    assert manager.transition_time == 0
    assert manager.transition_duration == 1.0
    assert manager.next_cam is cam_b


def test_current_position_none_before_update(view, target_rect):
    cam = DummyCamera((50, 50))
    manager = CameraManager(cam)
    assert manager.current_position is None


def test_current_position_updated_after_update(view, target_rect):
    cam = DummyCamera((50, 50))
    manager = CameraManager(cam)
    manager.update(view, target_rect, 0.016)
    assert manager.current_position == (50, 50)


def test_current_position_updated_during_transition(view, target_rect):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)
    manager.update(view, target_rect, 0.5)
    assert manager.current_position is not None
    assert 0 < manager.current_position[0] < 100


def test_both_cameras_update_during_transition(view, target_rect):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)

    for _ in range(10):
        manager.update(view, target_rect, 0.1)

    assert cam_a.calls == 10
    assert cam_b.calls == 10


def test_is_transitioning_false_initially(view_rect, target_rect):
    cam = DummyCamera((0, 0))
    manager = CameraManager(cam)
    assert not manager.is_transitioning


def test_is_transitioning_true_during_transition(view_rect, target_rect):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)
    assert manager.is_transitioning


def test_is_transitioning_false_after_completion(view_rect, target_rect):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)
    for _ in range(60):
        manager.update(view_rect, target_rect, 1 / 60)
    assert not manager.is_transitioning


def test_is_transitioning_false_after_instant_switch(view_rect, target_rect):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))
    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=0)
    assert not manager.is_transitioning
