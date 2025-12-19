# pyscroll‑ce

For Python 3.10+ and pygame‑ce 2.5.6+

__pygame‑ce is supported__

A simple and fast module for animated scrolling maps for your new or existing game.

If you find this useful, please consider making a donation to help support development:  

![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)

---

## Introduction

**pyscroll‑ce** is a maintained fork of the original `pyscroll` project.  
The old repository has been inactive, with pull requests left unmerged for over a year, so this new repo was created to keep the project alive and compatible with modern Python and pygame‑ce.

pyscroll‑ce is a generic module for fast scrolling images with pygame. It uses clever optimizations to achieve high frame rates. Its sole purpose is to draw maps — it does not load images or data, so you can integrate it with your own data structures, tile storage, and rendering logic.

It is fully compatible with [pytmx](https://github.com/bitcraft/pytmx), allowing you to use maps created with the Tiled Map Editor. It also has out‑of‑the‑box support for pygame sprites.

---

## Features

- Reload map tiles and data without restarting the game  
- Draw sprites or plain surfaces in layers  
- Support for animated tiles  
- Zoom in and out  
- Optional drop‑in replacement for `pygame.LayeredGroup`  
- Pixel alpha and colorkey tilesets supported  
- Draw and scroll shapes  
- Fast and lightweight footprint  
- Performance is independent of map size  
- Direct support for pytmx‑loaded maps from Tiled  

---

## Use It Like a Camera

pyscroll‑ce includes a pygame sprite group that renders all sprites on the map and correctly draws them above or below tiles. Sprites can use their rect in world coordinates, and the group acts like a camera, translating world coordinates to screen coordinates while rendering sprites and map layers.

This makes it easy to implement minimaps or chunky retro‑style graphics.

---

## Installation

Install from pip:

```bash
pip install pyscroll-ce
```

Or install from source (inside the project folder):

```bash
pip install .
```

For development (editable install):

```bash
pip install -e .
```

---

## New Game Tutorial

For a gentle introduction, open `apps/tutorial/quest.py`. It demonstrates how to use `PyscrollGroup` for efficient rendering.  
The Quest demo shows how to draw maps with pytmx, render layers quickly, and handle sprite layering (e.g., the Hero being covered when moving under certain tiles).

---

## Example Use with pytmx

```bash
import pygame
from pytmx.util_pygame import load_pygame
import pyscroll

class Sprite(pygame.sprite.Sprite):
    def __init__(self, surface) -> None:
        super().__init__()
        self.image = surface
        self.rect = surface.get_rect()

class Game:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen

        # Load TMX
        tmx_data = load_pygame("desert.tmx")

        # Create map renderer
        map_data = pyscroll.TiledMapData(tmx_data)
        map_layer = pyscroll.BufferedRenderer(map_data, screen.get_size())

        # Create group with map
        self.group = pyscroll.PyscrollGroup(map_layer=map_layer)

        # Camera is now external
        self.camera = Camera()

        # Add a sprite
        surface = pygame.image.load("my_surface.png").convert_alpha()
        self.hero = Sprite(surface)
        self.group.add(self.hero)

    def update(self, dt: float) -> None:
        # Update all sprites
        self.group.update(dt)

        # Update camera and center the map on the hero
        new_center = self.camera.update(self.group.view, self.hero.rect, dt)
        self.group.center(new_center)

    def draw(self) -> None:
        self.group.draw(self.screen)
```

---

## Adapting Existing Games / Map Data

pyscroll‑ce can be integrated with existing map data. You may need to create an adapter class or adjust your data handler to match the `TiledMapData` API.

Example: rendering custom surfaces with layer positions.

```bash
map_layer = pyscroll.BufferedRenderer(map_data, map_size)

def game_engine_draw():
    surfaces: list[Renderable] = []

    for game_object in my_game_engine:
        surfaces.append(
            Renderable(
                layer=game_object.layer,
                rect=game_object.get_screen_rect(),
                surface=game_object.get_surface(),
                blendmode=None,
            )
        )

    map_layer.draw(screen, screen.get_rect(), surfaces)
```

---

## FAQ

### Why are tiles repeating while scrolling?
By default, pyscroll‑ce does not handle maps with completely empty areas (no tiles in any layer).  
Solutions:
1. Fill empty areas with a background tile in Tiled or your data.  
2. Pass `alpha=True` to `BufferedRenderer` to enable per‑pixel alpha buffers (slower, ~33% performance reduction).

### Why are there streaks when scrolling?
Streaks are caused by missing tiles. See above for solutions.

### Can I blit graphics under the scrolling map layer?
Yes, but performance will be reduced. Options:
1. Pass `alpha=True` to the constructor.  
2. Use a colorkey (`colorkey=yourColor`).  

### Does the map layer support transparency?
Yes, for tiles. For transparency under the map, use `alpha` or `colorkey` as described above.

### Does pyscroll‑ce support parallax layers?
Not directly. You can build parallax effects by using multiple renderers with `alpha=True` and scrolling them at different speeds.
