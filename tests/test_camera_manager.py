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
        assert manager.start_pos == (0, 0)
        assert manager.next_cam is not None
    elif expected_pos_check == "approx_50":
        assert pos[0] == pytest.approx(50)
        assert pos[1] == pytest.approx(50)
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
