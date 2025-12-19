from unittest.mock import MagicMock

import pytest
from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.data import MapAggregator, PyscrollDataAdapter


@pytest.fixture
def aggregator():
    return MapAggregator((16, 16))


@pytest.fixture
def mock_data1():
    mock = MagicMock(spec=PyscrollDataAdapter)
    mock.tile_size = (16, 16)
    mock.map_size = (5, 5)
    mock.visible_tile_layers = [0]
    mock.get_tile_images_by_rect.return_value = [
        (x, y, 0, Surface((16, 16))) for y in range(5) for x in range(5)
    ]
    return mock


@pytest.fixture
def mock_data2():
    mock = MagicMock(spec=PyscrollDataAdapter)
    mock.tile_size = (16, 16)
    mock.map_size = (5, 5)
    mock.visible_tile_layers = [1]
    mock.get_tile_images_by_rect.return_value = [
        (x, y, 1, Surface((16, 16))) for y in range(5) for x in range(5)
    ]
    return mock


def test_add_and_remove_map(aggregator, mock_data1, mock_data2):
    aggregator.add_map(mock_data1, (0, 0))
    assert aggregator.map_size == (5, 5)

    aggregator.add_map(mock_data2, (5, 0))
    assert aggregator.map_size == (10, 5)

    aggregator.remove_map(mock_data1)
    assert aggregator.map_size == (10, 5)

    aggregator.remove_map(mock_data2)
    assert aggregator.map_size == (0, 0)


def test_visible_tile_layers_with_offsets(aggregator, mock_data1, mock_data2):
    aggregator.add_map(mock_data1, (0, 0), layer=0)
    aggregator.add_map(mock_data2, (0, 0), layer=10)
    # Layers should be offset correctly: mock_data1 layer 0 → 0, mock_data2 layer 1 → 11
    assert aggregator.visible_tile_layers == [0, 11]


def test_get_tile_images_by_rect_layer_adjustment(aggregator, mock_data1, mock_data2):
    aggregator.add_map(mock_data1, (0, 0), layer=0)
    aggregator.add_map(mock_data2, (5, 0), layer=10)
    rect = Rect(0, 0, 10, 5)
    tiles = list(aggregator.get_tile_images_by_rect(rect))
    # Ensure layers are adjusted by z offset
    assert any(l == 0 for _, _, l, _ in tiles)
    assert any(l == 11 for _, _, l, _ in tiles)


def test_add_map_negative_coordinates_normalization(aggregator, mock_data1):
    aggregator.add_map(mock_data1, (-2, -2))
    # Normalization should shift map so top-left is (0,0)
    assert aggregator._min_x == 0
    assert aggregator._min_y == 0
    assert aggregator.map_size == (5, 5)


def test_remove_nonexistent_map_raises(aggregator, mock_data1):
    with pytest.raises(ValueError):
        aggregator.remove_map(mock_data1)


def test_add_map_different_tile_size_raises(aggregator, mock_data1):
    mock_data_wrong = MagicMock(spec=PyscrollDataAdapter)
    mock_data_wrong.tile_size = (32, 32)
    mock_data_wrong.map_size = (3, 3)
    mock_data_wrong.visible_tile_layers = [0]
    with pytest.raises(ValueError):
        aggregator.add_map(mock_data_wrong, (0, 0))


def test_get_tile_images_empty_aggregator(aggregator):
    rect = Rect(0, 0, 5, 5)
    tiles = list(aggregator.get_tile_images_by_rect(rect))
    assert tiles == []


def test_get_animations_delegation(aggregator, mock_data1):
    mock_data1.get_animations.return_value = [(1, [(0, 100)])]
    aggregator.add_map(mock_data1, (0, 0))
    animations = list(aggregator.get_animations())
    assert animations == [(1, [(0, 100)])]


def test__get_tile_image_delegation(aggregator, mock_data1):
    mock_data1._get_tile_image.return_value = Surface((16, 16))
    aggregator.add_map(mock_data1, (0, 0))
    img = aggregator._get_tile_image(1, 1, 0)
    assert isinstance(img, Surface)


def test_world_to_local_basic(aggregator, mock_data1):
    aggregator.add_map(mock_data1, (10, 20), layer=5)

    result = aggregator.world_to_local(12, 23, 5)

    assert result is not None
    data, lx, ly, ll = result

    assert data is mock_data1
    assert lx == 2
    assert ly == 3
    assert ll == 0


def test_world_to_local_outside_map(aggregator, mock_data1):
    aggregator.add_map(mock_data1, (0, 0))
    result = aggregator.world_to_local(100, 100, 0)

    assert result is None


def test_world_to_local_wrong_layer(aggregator, mock_data1):
    aggregator.add_map(mock_data1, (0, 0), layer=0)
    result = aggregator.world_to_local(1, 1, 5)
    assert result is None
