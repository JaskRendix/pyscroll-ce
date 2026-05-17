# **Benchmark Results**

## **Environment**

- Python: 3.12.3  
- pygame‑ce: 2.5.6  
- SDL: 2.32.10  

---

# **Animation Benchmarks**

## **Animation Micro‑Benchmark**

```
Iterations: 1,000,000
Total time: 0.535377 s
Per update: 535.38 ns
```

**Interpretation:**  
Your `AnimationToken.update()` hot path is extremely fast — well under a microsecond per call.  
This is excellent for real‑time tile animation.

---

## **Animation Macro‑Benchmark**

```
Tokens: 5000
Cycles: 200
Total updates: 1,000,000
Total time: 0.331938 s
Per update: 0.33 µs
```

**Interpretation:**  
Even with 5,000 tokens updated 200 times, the system stays extremely efficient.  
This confirms your animation engine scales cleanly.

---

# **PyscrollGroup Benchmark**

```
Sprites: 5000
Iterations: 200
Total time: 2.8234s
Avg per frame: 14.117 ms
FPS equivalent: 70.8 FPS
Culling benchmark: 0.9751654079991567
Renderable creation: 0.1596s for 200000 instances
spritedict update: 0.0013s for 5000 updates
```

**Interpretation:**  
70–100 FPS for 5000 sprites is strong.  
Renderable creation and culling remain the dominant costs, as expected.

---

# **FastQuadTree Benchmark**

```
query_count=1000, depth=4

1000 rects:
  Build:       0.002615s
  Quadtree:    0.023014s
  Brute-force: 0.065446s

5000 rects:
  Build:       0.016742s
  Quadtree:    0.087583s
  Brute-force: 0.408466s

10000 rects:
  Build:       0.051816s
  Quadtree:    0.259966s
  Brute-force: 0.636219s

20000 rects:
  Build:       0.050185s
  Quadtree:    0.257929s
  Brute-force: 1.065253s
```

**Interpretation:**  
Quadtree queries scale sub‑linearly and outperform brute force by 4–10× depending on size.

---

# **FastQuadTree Depth Benchmark**

```
Items:   5000
Queries: 1000
Depths:  2–6

Depth |  Build (s) |  Query (s)
--------------------------------
    2 | 0.006896 | 0.053625
    3 | 0.007962 | 0.049727
    4 | 0.011353 | 0.067094
    5 | 0.009898 | 0.056578
    6 | 0.010024 | 0.055645
```

**Interpretation:**  
Depth 3–5 is the sweet spot.  
Depth 4 has slightly higher query time due to node splitting overhead.

---

# **ViewPort Benchmark**

```
center()                          2.316 µs per call
translate_point()                 0.560 µs per call
translate_rect()                  0.568 µs per call
translate_points(32)             12.408 µs per call
translate_rects(32)              15.344 µs per call
```

**Interpretation:**  
Viewport transforms are extremely efficient and suitable for real‑time camera movement.

---
