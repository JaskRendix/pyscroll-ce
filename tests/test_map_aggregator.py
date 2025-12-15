import unittest
from unittest.mock import MagicMock

from pygame.rect import Rect
from pygame.surface import Surface

from pyscroll.data import MapAggregator, PyscrollDataAdapter


class TestMapAggregator(unittest.TestCase):

    def setUp(self):
        self.aggregator = MapAggregator((16, 16))
        self.mock_data1 = MagicMock(spec=PyscrollDataAdapter)
        self.mock_data2 = MagicMock(spec=PyscrollDataAdapter)
        self.mock_data3 = MagicMock(spec=PyscrollDataAdapter)
        self.mock_data1.tile_size = (16, 16)
        self.mock_data2.tile_size = (16, 16)
        self.mock_data3.tile_size = (32, 32)
        self.mock_data1.map_size = (5, 5)
        self.mock_data2.map_size = (5, 5)
        self.mock_data3.map_size = (3, 3)
        self.mock_data1.visible_tile_layers = [0]
        self.mock_data2.visible_tile_layers = [1]
        self.mock_data3.visible_tile_layers = [0]
        self.mock_data1.get_tile_images_by_rect.return_value = [
            (x, y, 0, Surface((16, 16))) for y in range(5) for x in range(5)
        ]
        self.mock_data2.get_tile_images_by_rect.return_value = [
            (x, y, 1, Surface((16, 16))) for y in range(5) for x in range(5)
        ]
        self.mock_data3.get_tile_images_by_rect.return_value = [
            (x, y, 0, Surface((32, 32))) for y in range(3) for x in range(3)
        ]

    def test_add_map(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.assertEqual(self.aggregator.map_size, (5, 5))
        self.aggregator.add_map(self.mock_data2, (5, 0))
        self.assertEqual(self.aggregator.map_size, (10, 5))

    def test_remove_map(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.assertEqual(self.aggregator.map_size, (5, 5))
        self.aggregator.remove_map(self.mock_data1)
        self.assertEqual(self.aggregator.map_size, (0, 0))

    def test_visible_tile_layers(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.aggregator.add_map(self.mock_data2, (5, 0))
        self.assertEqual(self.aggregator.visible_tile_layers, [0, 1])

    def test_get_tile_images_by_rect(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.aggregator.add_map(self.mock_data2, (5, 0))
        rect = Rect(0, 0, 10, 5)
        tiles = list(self.aggregator.get_tile_images_by_rect(rect))
        self.assertEqual(len(tiles), 50)

    def test_add_overlapping_maps(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.aggregator.add_map(self.mock_data2, (3, 0))
        rect = Rect(0, 0, 5, 5)
        tiles = list(self.aggregator.get_tile_images_by_rect(rect))
        self.assertEqual(len(tiles), 50)

    def test_remove_nonexistent_map(self):
        with self.assertRaises(ValueError):
            self.aggregator.remove_map(self.mock_data1)

    def test_add_map_different_tile_size(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        with self.assertRaises(ValueError):
            self.aggregator.add_map(self.mock_data3, (5, 0))

    def test_get_tile_images_empty_aggregator(self):
        rect = Rect(0, 0, 5, 5)
        tiles = list(self.aggregator.get_tile_images_by_rect(rect))
        self.assertEqual(len(tiles), 0)

    def test_visible_tile_layers_empty(self):
        self.assertEqual(self.aggregator.visible_tile_layers, [])

    def test_add_map_negative_coordinates(self):
        self.aggregator.add_map(self.mock_data1, (-2, -2))
        self.assertEqual(self.aggregator.map_size, (5, 5))
        rect = Rect(-2, -2, 5, 5)
        tiles = list(self.aggregator.get_tile_images_by_rect(rect))
        self.assertEqual(len(tiles), 25)

    def test_get_tile_images_partial_overlap(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        rect = Rect(2, 2, 5, 5)
        tiles = list(self.aggregator.get_tile_images_by_rect(rect))
        self.assertEqual(len(tiles), 25)

    def test_get_tile_images_no_overlap(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        rect = Rect(6, 6, 5, 5)
        tiles = list(self.aggregator.get_tile_images_by_rect(rect))
        self.assertEqual(len(tiles), 0)

    def test_add_multiple_maps_same_layer(self):
        self.mock_data2.visible_tile_layers = [0]
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.aggregator.add_map(self.mock_data2, (5, 0))
        self.assertEqual(self.aggregator.visible_tile_layers, [0])

    def test_add_map_zero_size(self):
        mock_data_zero_size = MagicMock(spec=PyscrollDataAdapter)
        mock_data_zero_size.tile_size = (16, 16)
        mock_data_zero_size.map_size = (0, 0)
        mock_data_zero_size.visible_tile_layers = [0]
        self.aggregator.add_map(mock_data_zero_size, (0, 0))
        self.assertEqual(self.aggregator.map_size, (0, 0))

    def test_remove_last_map(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.aggregator.remove_map(self.mock_data1)
        self.assertEqual(self.aggregator.map_size, (0, 0))

    def test_remove_first_map(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.aggregator.add_map(self.mock_data2, (5, 0))
        self.aggregator.remove_map(self.mock_data1)
        self.assertEqual(self.aggregator.map_size, (10, 5))

    def test_remove_middle_map(self):
        self.aggregator.add_map(self.mock_data1, (0, 0))
        self.aggregator.add_map(self.mock_data2, (5, 0))
        mock_data3 = MagicMock(spec=PyscrollDataAdapter)
        mock_data3.tile_size = (16, 16)
        mock_data3.map_size = (5, 5)
        mock_data3.visible_tile_layers = [2]
        self.aggregator.add_map(mock_data3, (2, 0))
        self.aggregator.remove_map(mock_data3)
        self.assertEqual(self.aggregator.map_size, (10, 5))
