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


@pytest.fixture
def target():
    return Rect(100, 100, 32, 32)


def test_initial_camera_used(view, target):
    cam = DummyCamera((0, 0))
    manager = CameraManager(cam)

    pos = manager.update(view, target, 0.016)
    assert pos == (0, 0)
    assert cam.calls == 1


def test_instant_switch(view, target):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))

    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=0)

    pos = manager.update(view, target, 0.016)
    assert pos == (100, 100)
    assert cam_b.calls == 1
    assert manager.next_cam is None


def test_transition_starts(view, target):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))

    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)

    pos = manager.update(view, target, 0.016)

    assert 0 < pos[0] < 100
    assert 0 < pos[1] < 100

    assert manager.start_pos == (0, 0)


def test_transition_progress(view, target):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))

    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)

    for _ in range(30):
        pos = manager.update(view, target, 1 / 60)

    assert pos[0] == pytest.approx(50)
    assert pos[1] == pytest.approx(50)


def test_transition_completes(view, target):
    cam_a = DummyCamera((0, 0))
    cam_b = DummyCamera((100, 100))

    manager = CameraManager(cam_a)
    manager.set_camera(cam_b, duration=1.0)

    for _ in range(60):
        pos = manager.update(view, target, 1 / 60)

    assert pos == (100, 100)
    assert manager.current is cam_b
    assert manager.next_cam is None


def test_target_camera(view, target):
    cam = TargetCamera()
    manager = CameraManager(cam)

    pos = manager.update(view, target, 0.016)
    assert pos == target.center
