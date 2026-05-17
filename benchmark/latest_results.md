# **Benchmark Results**

## **Environment**

- Python: 3.12.3  
- pygame‑ce: 2.5.6  
- SDL: 2.32.10  

---

## **PyscrollGroup Benchmark**

```
Sprites: 5000
Iterations: 200
Total time: 1.9141s
Avg per frame: 9.571 ms
FPS equivalent: 104.5 FPS
Culling benchmark: 0.7381282759999976
Renderable creation: 0.1129s for 200000 instances
spritedict update: 0.0010s for 5000 updates
```

---

## **FastQuadTree Benchmark**

```
query_count=1000, depth=4

1000 rects:
  Build:       0.002643s
  Quadtree:    0.021500s
  Brute-force: 0.048527s

5000 rects:
  Build:       0.011974s
  Quadtree:    0.065599s
  Brute-force: 0.237466s

10000 rects:
  Build:       0.019520s
  Quadtree:    0.116804s
  Brute-force: 0.468596s

20000 rects:
  Build:       0.036437s
  Quadtree:    0.228677s
  Brute-force: 0.972469s
```

---

## **FastQuadTree Depth Benchmark**

```
Items:   5000
Queries: 1000
Depths:  2–6

Depth |  Build (s) |  Query (s)
--------------------------------
    2 | 0.005775 | 0.050032
    3 | 0.008210 | 0.053479
    4 | 0.009274 | 0.055760
    5 | 0.009052 | 0.057233
    6 | 0.010362 | 0.050830
```

---

## **ViewPort Benchmark**

```
center()                          2.293 µs per call
translate_point()                 0.608 µs per call
translate_rect()                  0.534 µs per call
translate_points(32)             11.384 µs per call
translate_rects(32)              14.737 µs per call
```

---
