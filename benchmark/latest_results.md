# Benchmark Results

## Environment

- Python: 3.12.3  
- pygame‑ce: 2.5.6  
- SDL: 2.32.10  

---

## PyscrollGroup Benchmark

```
Sprites: 5000
Iterations: 200
Total time: 1.9906s
Avg per frame: 9.953 ms
FPS equivalent: 100.5 FPS
Culling benchmark: 0.6670580879999761
Renderable creation: 0.1174s for 200000 instances
spritedict update: 0.0022s for 5000 updates
```

---

## FastQuadTree Benchmark

```
query_count=1000, depth=4

1000 rects:
  Build:       0.004811s
  Quadtree:    0.032924s
  Brute-force: 0.047972s

5000 rects:
  Build:       0.022712s
  Quadtree:    0.105227s
  Brute-force: 0.244694s

10000 rects:
  Build:       0.038267s
  Quadtree:    0.185984s
  Brute-force: 0.497932s

20000 rects:
  Build:       0.075629s
  Quadtree:    0.358072s
  Brute-force: 0.978913s
```

---

## FastQuadTree Depth Benchmark

```
Items:   5000
Queries: 1000
Depths:  2–6

Depth |  Build (s) |  Query (s)
--------------------------------
    2 | 0.007437 | 0.052560
    3 | 0.012848 | 0.047044
    4 | 0.018877 | 0.070450
    5 | 0.030667 | 0.108517
    6 | 0.048340 | 0.192085
```

---

## ViewPort Benchmark

```
center()                          2.184 µs per call
translate_point()                 0.579 µs per call
translate_rect()                  0.489 µs per call
translate_points(32)             10.308 µs per call
translate_rects(32)              14.039 µs per call
```

---
