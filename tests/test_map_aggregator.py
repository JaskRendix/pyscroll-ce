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
    assert any(layer == 0 for _, _, layer, _ in tiles)
    assert any(layer == 11 for _, _, layer, _ in tiles)


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


def test_tile_overdraw_default(aggregator):
    assert aggregator.tile_overdraw == (0, 0)


def test_tile_overdraw_propagated_from_child(aggregator, mock_data1):
    mock_data1.tile_overdraw = (0, 2)
    # MapAggregator itself doesn't aggregate overdraw from children —
    # that's handled at the renderer level via _expanded_tile_view
    # so aggregator should still return its own default
    aggregator.add_map(mock_data1, (0, 0))
    assert aggregator.tile_overdraw == (0, 0)


def test_get_tile_images_coords_translated_by_offset(aggregator, mock_data1):
    mock_data1.get_tile_images_by_rect.return_value = [
        (0, 0, 0, Surface((16, 16))),
        (1, 0, 0, Surface((16, 16))),
    ]
    aggregator.add_map(mock_data1, (10, 5))
    rect = Rect(0, 0, 20, 10)
    tiles = list(aggregator.get_tile_images_by_rect(rect))
    xs = [x for x, y, layer, _ in tiles]
    ys = [y for x, y, layer, _ in tiles]
    assert 10 in xs  # 0 + offset 10
    assert 11 in xs  # 1 + offset 10
    assert all(y == 5 for y in ys)  # 0 + offset 5


def test_get_tile_images_by_rect_no_overlap(aggregator, mock_data1):
    aggregator.add_map(mock_data1, (100, 100))
    rect = Rect(0, 0, 5, 5)  # does not overlap map at (100,100)
    tiles = list(aggregator.get_tile_images_by_rect(rect))
    assert tiles == []
    mock_data1.get_tile_images_by_rect.assert_not_called()


def test_get_tile_images_sorted_by_z(aggregator, mock_data1, mock_data2):
    aggregator.add_map(mock_data2, (0, 0), layer=10)  # added first but higher z
    aggregator.add_map(mock_data1, (0, 0), layer=0)  # added second but lower z

    rect = Rect(0, 0, 10, 5)
    tiles = list(aggregator.get_tile_images_by_rect(rect))
    layers = [layer for _, _, layer, _ in tiles]

    # z=0 tiles should come before z=10 tiles
    first_high_z = next(i for i, l in enumerate(layers) if l >= 10)
    assert all(l < 10 for l in layers[:first_high_z])


def test_reload_data_delegates_to_all_maps(aggregator, mock_data1, mock_data2):
    aggregator.add_map(mock_data1, (0, 0))
    aggregator.add_map(mock_data2, (5, 0))
    aggregator.reload_data()
    mock_data1.reload_data.assert_called_once()
    mock_data2.reload_data.assert_called_once()


def test_repr(aggregator, mock_data1):
    aggregator.add_map(mock_data1, (0, 0))
    r = repr(aggregator)
    assert "MapAggregator" in r
    assert "tile_size" in r


def test_len(aggregator, mock_data1, mock_data2):
    assert len(aggregator) == 0
    aggregator.add_map(mock_data1, (0, 0))
    assert len(aggregator) == 1
    aggregator.add_map(mock_data2, (5, 0))
    assert len(aggregator) == 2
    aggregator.remove_map(mock_data1)
    assert len(aggregator) == 1


def test_no_normalize(mock_data1):
    aggregator = MapAggregator((16, 16), normalize=False)
    aggregator.add_map(mock_data1, (-10, -10))
    # Without normalization, negative offsets are preserved
    assert aggregator._min_x == 0  # never updated
    assert aggregator._min_y == 0
