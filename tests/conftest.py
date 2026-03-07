import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def init_pygame():
    """Initialize pygame and display for all tests."""
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()
