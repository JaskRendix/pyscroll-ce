import pygame
import pytest
from pygame.rect import Rect
from pygame.surface import Surface


@pytest.fixture(scope="session", autouse=True)
def init_pygame():
    """Initialize pygame and display for all tests."""
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture
def view_rect():
    """Standard view rectangle for camera tests."""
    return Rect(0, 0, 640, 480)


@pytest.fixture
def target_rect():
    """Standard target rectangle for camera tests."""
    return Rect(100, 100, 32, 32)


@pytest.fixture
def surface():
    """Standard surface for rendering tests."""
    return Surface((640, 480))


@pytest.fixture
def tile_size():
    """Standard tile size used across tests."""
    return (32, 32)
