import unittest
from unittest.mock import MagicMock

from pygame.surface import Surface

from pyscroll.data import TiledMapData


class TestTiledMapData(unittest.TestCase):

    def setUp(self):
        self.mock_tmx = MagicMock()
        self.mock_tmx.tilewidth = 16
        self.mock_tmx.tileheight = 16
        self.mock_tmx.width = 10
        self.mock_tmx.height = 10
        self.mock_tmx.visible_tile_layers = [0]
        self.mock_tmx.images = [Surface((16, 16))]
        self.mock_tmx.layers = [MagicMock()]
        self.mock_tmx.layers[0].data = [[1 for _ in range(10)] for _ in range(10)]
        self.mock_tmx.tile_properties = {1: {"frames": [(0, 100)]}}
        self.mock_tmx.get_tile_image.return_value = Surface((16, 16))
        self.mock_tmx.filename = "test.tmx"

        self.tiled_map_data = TiledMapData(self.mock_tmx)
        self.tiled_map_data.at = {(x, y, 0): 1 for x in range(10) for y in range(10)}
        self.tiled_map_data.images = [Surface((16, 16))]

    def test_tile_size(self):
        self.assertEqual(self.tiled_map_data.tile_size, (16, 16))

    def test_map_size(self):
        self.assertEqual(self.tiled_map_data.map_size, (10, 10))

    def test_visible_tile_layers(self):
        self.assertEqual(self.tiled_map_data.visible_tile_layers, [0])

    def test_get_tile_image(self):
        image = self.tiled_map_data.get_tile_image(0, 0, 0)
        self.assertIsInstance(image, Surface)

    def test_get_tile_image_by_id(self):
        image = self.tiled_map_data._get_tile_image_by_id(0)
        self.assertIsInstance(image, Surface)

    def test_get_animations(self):
        animations = list(self.tiled_map_data.get_animations())
        self.assertEqual(len(animations), 1)
