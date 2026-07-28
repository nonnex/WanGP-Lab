# MHR70 index cheat-sheet (lab)

From `sam_3d_body/metadata/mhr70.py` — first 70 of 308 MHR keypoints.

## Body (0–20)

| i | name |
|---|------|
| 0 | nose |
| 1 | left-eye |
| 2 | right-eye |
| 3 | left-ear |
| 4 | right-ear |
| 5 | left-shoulder |
| 6 | right-shoulder |
| 7 | left-elbow |
| 8 | right-elbow |
| 9 | left-hip |
| 10 | right-hip |
| **11** | **left-knee** |
| **12** | **right-knee** |
| 13 | left-ankle |
| 14 | right-ankle |
| 15 | left-big-toe-tip |
| 16 | left-small-toe-tip |
| 17 | left-heel |
| 18 | right-big-toe-tip |
| 19 | right-small-toe-tip |
| 20 | right-heel |

## Hands / extras (21–69)

21–41 right hand (+ right-wrist 41)  
42–62 left hand (+ left-wrist 62)  
63–68 olecranon / cubital / acromion  
69 neck  

## Lab formulas

```text
on_top = "left"  if knee_y[11] < knee_y[12] else "right"   # smaller y = higher on screen
open   = abs(y12-y11) < 45  AND  abs(x12-x11) > 55         # seated 480–1080p heuristic
```

Image coords: origin top-left, +y down (OpenCV/PIL convention after projection).
