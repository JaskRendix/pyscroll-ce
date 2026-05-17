# pyscroll‑ce

For Python 3.10–3.12 and pygame‑ce 2.5.6+

A module for fast scrolling maps in pygame‑ce.

`https://img.shields.io/badge/python-3.10%E2%80%933.12-blue.svg`
`https://img.shields.io/badge/license-GPL--3.0-green.svg`

---

## Introduction

pyscroll‑ce is a maintained fork of the original `pyscroll` project.  
The goal is compatibility with modern Python and pygame‑ce, plus continued development.

pyscroll‑ce draws scrolling maps with high performance.  
It does not load images or map data.  
It integrates with pytmx or custom data sources.

The module supports animated tiles, sprite layering, zoom, and multiple camera types.

---

## Features

- Reload map tiles and data without restarting  
- Draw sprites or surfaces in layers  
- Support for animated tiles  
- Zoom support  
- Optional drop‑in replacement for `pygame.LayeredGroup`  
- Pixel alpha and colorkey tilesets  
- Draw and scroll shapes  
- Performance independent of map size  
- pytmx integration  
- Camera subsystem with multiple camera types and transitions

---

## Camera System

Cameras live in the `pyscroll.cameras` package.  
The public API is re‑exported through `pyscroll.camera`.

### Available Cameras

| Class | Description |
|---|---|
| `BasicCamera` | Smooth follow |
| `FollowCamera` | Smooth follow with deadzone |
| `PlatformerCamera` | Vertical deadzone for platformers |
| `ZoomCamera` | Wraps a camera, adds zoom |
| `BoundsCamera` | Wraps a camera, clamps to world bounds |
| `CutsceneCamera` | Waypoints, linear or Catmull–Rom |
| `SplitFollowCamera` | Midpoint follow for multiple targets |
| `RailCamera` | Movement constrained to a polyline |
| `DebugFlyCamera` | Free movement for development |

### CameraManager

`CameraManager` transitions between cameras with a duration value.

```python
manager = CameraManager(FollowCamera())
manager.set_camera(ZoomCamera(FollowCamera()), duration=1.0)
pos = manager.update(view, target_rect, dt)
```

All camera classes are fully type‑annotated.

---

## Installation

Not yet published to PyPI.

Install from source:

```bash
pip install .
```

Editable install:

```bash
pip install -e .
```

---

## Example with pytmx

```python
import pygame
from pytmx.util_pygame import load_pygame
import pyscroll
from pyscroll.camera import FollowCamera, CameraManager

class Sprite(pygame.sprite.Sprite):
    def __init__(self, surface):
        super().__init__()
        self.image = surface
        self.rect = surface.get_rect()

class Game:
    def __init__(self, screen):
        self.screen = screen

        tmx = load_pygame("desert.tmx")
        map_data = pyscroll.TiledMapData(tmx)
        map_layer = pyscroll.BufferedRenderer(map_data, screen.get_size())

        self.group = pyscroll.PyscrollGroup(map_layer=map_layer)

        self.camera = CameraManager(FollowCamera())

        surface = pygame.image.load("my_surface.png").convert_alpha()
        self.hero = Sprite(surface)
        self.group.add(self.hero)

    def update(self, dt):
        self.group.update(dt)
        center = self.camera.update(self.group.view, self.hero.rect, dt)
        self.group.center(center)

    def draw(self):
        self.group.draw(self.screen)
```

---

## Integrating with Custom Map Data

pyscroll‑ce works with custom map structures.  
Provide a data source that matches the `TiledMapData` interface.

Example:

```python
map_layer = pyscroll.BufferedRenderer(map_data, map_size)

surfaces = []
for obj in engine_objects:
    surfaces.append(
        Renderable(
            layer=obj.layer,
            rect=obj.get_screen_rect(),
            surface=obj.get_surface(),
            blendmode=None,
        )
    )

map_layer.draw(screen, screen.get_rect(), surfaces)
```

---

## FAQ

### Tiles repeat while scrolling
Empty map areas cause repetition.  
Fill empty areas or enable per‑pixel alpha:

```python
BufferedRenderer(map_data, size, alpha=True)
```

### Streaks appear while scrolling
Caused by missing tiles.  
Fill empty areas or enable alpha.

### Drawing under the map layer
Possible but slower.  
Use `alpha=True` or a colorkey.

### Transparency support
Tiles support transparency.  
For transparency under the map, use alpha or colorkey.

### Parallax layers
Not built in.  
Use multiple renderers at different scroll speeds.
