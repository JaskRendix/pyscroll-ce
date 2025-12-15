import unittest

from pygame.rect import Rect

from pyscroll.data import PyscrollDataAdapter


class TestPyscrollDataAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = PyscrollDataAdapter()

    def test_process_animation_queue_empty(self):
        tile_view = Rect(0, 0, 10, 10)
        self.assertEqual(self.adapter.process_animation_queue(tile_view), [])

    def test_prepare_tiles(self):
        tiles = Rect(0, 0, 10, 10)
        self.adapter.prepare_tiles(tiles)

    def test_reload_animations_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.adapter.reload_animations()

    def test_get_tile_image_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.adapter.get_tile_image(0, 0, 0)

    def test_get_tile_image_by_id_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.adapter._get_tile_image_by_id(0)

    def test_get_animations_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            next(self.adapter.get_animations())

    def test_get_tile_images_by_rect_not_implemented(self):
        rect = Rect(0, 0, 10, 10)
        with self.assertRaises(StopIteration):
            next(self.adapter.get_tile_images_by_rect(rect))
