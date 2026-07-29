#!/usr/bin/env python3
"""Build Wan2GP Wan-Move tracks [T,N,2] from SAM3D MHR70 analysis.

Wan2GP Motion Designer / wanmove expects:
  np.save(path, array) with shape (T, N, 2) pixel coords (x, y).
  If max<=1, coords are treated as normalized and scaled by width/height.

Default motion: e01 uncross→open from start still analysis
  - knees 11/12: lower top knee (dy→0), then increase |dx| (apart)
  - ankles 13/14 follow knees lightly
  - optional hip 9/10 stable

Usage:
  pipeline/.venv/bin/python lab/tools/mhr70_to_wanmove_tracks.py \\
    --analysis _data/analysis/0009 \\
    --out _data/cache/wanmove/tracks_e01_open_t81.npy \\
    --frames 81 --width 832 --height 480 --vis
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

LK, RK = 11, 12
LA, RA = 13, 14
LH, RH = 9, 10
RW, LW = 41, 62  # MHR70 wrists (right=41, left=62)


def _load_kp2(analysis: Path) -> tuple[np.ndarray, dict]:
    z = np.load(analysis / "sam3d_body.npz", allow_pickle=True)
    kp = np.asarray(z["pred_keypoints_2d"], dtype=np.float64)
    if kp.ndim == 3:
        kp = kp[0]
    meta = {
        "trust": bool(z["skeleton_trust"]) if "skeleton_trust" in z.files else None,
        "src_w": int(z["image_width"]) if "image_width" in z.files else None,
        "src_h": int(z["image_height"]) if "image_height" in z.files else None,
    }
    # try common keys
    for a, b in (("width", "src_w"), ("W", "src_w"), ("height", "src_h"), ("H", "src_h")):
        if a in z.files and meta[b] is None:
            meta[b] = int(np.asarray(z[a]).reshape(-1)[0])
    return kp, meta


def _ease(t: float) -> float:
    # smoothstep
    t = float(np.clip(t, 0.0, 1.0))
    return t * t * (3.0 - 2.0 * t)


def cover_crop_map(
    x: float,
    y: float,
    *,
    src_w: int,
    src_h: int,
    width: int,
    height: int,
) -> tuple[float, float]:
    """Map full-res pixel → target with same cover-center-crop as still resize."""
    scale = max(width / src_w, height / src_h)
    nw, nh = int(src_w * scale), int(src_h * scale)
    left = (nw - width) // 2
    top = (nh - height) // 2
    return x * scale - left, y * scale - top


def build_e01_open_tracks(
    kp: np.ndarray,
    *,
    T: int,
    width: int,
    height: int,
    src_w: int | None,
    src_h: int | None,
    apart_dx: float = 90.0,
    move_hands: bool = True,
) -> np.ndarray:
    """T frames, N=6: Lknee,Rknee,Lankle,Rankle,Rwrist,Lwrist (pixel coords)."""
    sw = int(src_w or width)
    sh = int(src_h or height)

    def pt(i: int) -> np.ndarray:
        x, y = cover_crop_map(float(kp[i, 0]), float(kp[i, 1]), src_w=sw, src_h=sh, width=width, height=height)
        return np.array([x, y], dtype=np.float64)

    lk0, rk0 = pt(LK), pt(RK)
    la0, ra0 = pt(LA), pt(RA)
    lh0, rh0 = pt(LH), pt(RH)
    rw0 = pt(RW) if len(kp) > RW else (lk0 + rk0) * 0.5
    lw0 = pt(LW) if len(kp) > LW else lh0.copy()

    # who is on top (smaller y)
    left_on_top = lk0[1] < rk0[1]
    # mid y for open
    y_open = 0.5 * (lk0[1] + rk0[1])
    # lateral targets: push knees apart from midpoint
    mid_x = 0.5 * (lk0[0] + rk0[0])
    # keep side order
    if lk0[0] <= rk0[0]:
        lx1, rx1 = mid_x - apart_dx * 0.5, mid_x + apart_dx * 0.5
    else:
        lx1, rx1 = mid_x + apart_dx * 0.5, mid_x - apart_dx * 0.5
    lk1 = np.array([lx1, y_open])
    rk1 = np.array([rx1, y_open])
    # ankles: drop slightly toward floor, follow x of knees
    la1 = np.array([lx1, min(height - 8, la0[1] + 15)])
    ra1 = np.array([rx1, min(height - 8, ra0[1] + 15)])

    # Hands: leave knee — rest on outer thigh / hip (not glued on knee).
    # Right wrist often starts on top knee in 675 still; move to right hip/thigh.
    # Left wrist often lower; settle on left thigh / mattress beside hip.
    rw1 = np.array(
        [
            float(np.clip(rh0[0] + 25.0, 0, width - 1)),
            float(np.clip(rh0[1] + 35.0, 0, height - 1)),
        ]
    )
    lw1 = np.array(
        [
            float(np.clip(lh0[0] - 20.0, 0, width - 1)),
            float(np.clip(lh0[1] + 40.0, 0, height - 1)),
        ]
    )

    n_pts = 6 if move_hands else 4
    tracks = np.zeros((T, n_pts, 2), dtype=np.float32)
    for ti in range(T):
        u = ti / max(T - 1, 1)
        if u <= 0.55:
            a = _ease(u / 0.55)
            lk = lk0.copy()
            rk = rk0.copy()
            if left_on_top:
                lk[1] = (1 - a) * lk0[1] + a * y_open
                rk[1] = (1 - 0.3 * a) * rk0[1] + 0.3 * a * y_open
            else:
                rk[1] = (1 - a) * rk0[1] + a * y_open
                lk[1] = (1 - 0.3 * a) * lk0[1] + 0.3 * a * y_open
            la = (1 - a) * la0 + a * np.array([lk[0], la0[1]])
            ra = (1 - a) * ra0 + a * np.array([rk[0], ra0[1]])
            # hands leave knee early (first half of motion)
            ah = _ease(min(1.0, u / 0.4))
            rw = (1 - ah) * rw0 + ah * rw1
            lw = (1 - ah) * lw0 + ah * lw1
        else:
            a = _ease((u - 0.55) / 0.45)
            lk_m = np.array([lk0[0], y_open])
            rk_m = np.array([rk0[0], y_open])
            lk = (1 - a) * lk_m + a * lk1
            rk = (1 - a) * rk_m + a * rk1
            la = (1 - a) * np.array([lk_m[0], la0[1]]) + a * la1
            ra = (1 - a) * np.array([rk_m[0], ra0[1]]) + a * ra1
            rw, lw = rw1.copy(), lw1.copy()
        tracks[ti, 0] = lk
        tracks[ti, 1] = rk
        tracks[ti, 2] = la
        tracks[ti, 3] = ra
        if move_hands:
            tracks[ti, 4] = rw
            tracks[ti, 5] = lw
    tracks[..., 0] = np.clip(tracks[..., 0], 0, width - 1)
    tracks[..., 1] = np.clip(tracks[..., 1], 0, height - 1)
    return tracks


def vis_overlay(still: Path, tracks: np.ndarray, out: Path, width: int, height: int) -> None:
    """Readable mission preview — NOT a full skeleton.

    Wan-Move guide has only 6 points:
      0 L_knee · 1 R_knee · 2 L_ankle · 3 R_ankle · 4 R_wrist · 5 L_wrist

    Layout (2×2 of still size):
      [ START cyan ] [ END lime ]
      [ full still + faint trails + both poses ]
    """
    from PIL import Image, ImageDraw

    labels = ["L_knee", "R_knee", "L_ankle", "R_ankle", "R_wrist", "L_wrist"]
    bones = [(0, 2), (1, 3), (0, 1)]  # shin lines + knee bar
    COL_START = (80, 200, 255)
    COL_END = (80, 255, 120)
    COL_TRAIL = (100, 100, 120)

    base = Image.open(still).convert("RGB").resize((width, height), Image.BICUBIC)
    T = int(tracks.shape[0])
    N = int(tracks.shape[1])

    def xy(t: int, n: int) -> tuple[float, float]:
        return float(tracks[t, n, 0]), float(tracks[t, n, 1])

    def draw_pose(dr: ImageDraw.ImageDraw, t: int, color: tuple[int, int, int], tag: str) -> None:
        for a, b in bones:
            if a < N and b < N:
                dr.line([xy(t, a), xy(t, b)], fill=color, width=3)
        for n in range(min(N, len(labels))):
            x, y = xy(t, n)
            r = 6
            dr.ellipse((x - r, y - r, x + r, y + r), fill=color, outline=(0, 0, 0))
            dr.text((x + 8, y - 8), labels[n], fill=color)
        mx = 0.5 * (xy(t, 0)[0] + xy(t, 1)[0])
        my = min(xy(t, 0)[1], xy(t, 1)[1]) - 22
        dr.text((mx - 24, my), tag, fill=color)

    left = base.copy()
    right = base.copy()
    draw_pose(ImageDraw.Draw(left), 0, COL_START, "START")
    draw_pose(ImageDraw.Draw(right), T - 1, COL_END, "END open")
    ImageDraw.Draw(left).rectangle((0, 0, width, 28), fill=(0, 0, 0))
    ImageDraw.Draw(left).text((8, 6), "t=0  crossed (cyan)", fill=COL_START)
    ImageDraw.Draw(right).rectangle((0, 0, width, 28), fill=(0, 0, 0))
    ImageDraw.Draw(right).text((8, 6), f"t={T - 1}  open target (lime)", fill=COL_END)

    both = base.copy()
    drb = ImageDraw.Draw(both)
    for n in range(N):
        pts = [xy(t, n) for t in range(0, T, max(1, T // 24))]
        if len(pts) >= 2:
            drb.line(pts, fill=COL_TRAIL, width=2)
    draw_pose(drb, 0, COL_START, "S")
    draw_pose(drb, T - 1, COL_END, "E")
    drb.rectangle((0, 0, width, 28), fill=(0, 0, 0))
    drb.text(
        (8, 6),
        "6-pt guide only (knees/ankles/wrists) — not full skeleton",
        fill=(220, 220, 220),
    )

    canvas = Image.new("RGB", (width * 2, height * 2), (20, 20, 24))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (width, 0))
    canvas.paste(both.resize((width * 2, height), Image.BICUBIC), (0, height))

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=92)
    # compact single-panel for small UI thumbnails
    single = out.with_name(out.name.replace(".vis.jpg", ".vis_single.jpg"))
    if single == out:
        single = out.with_suffix(".vis_single.jpg")
    both.save(single, quality=90)
    print("vis", out)
    print("vis_single", single)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analysis", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--frames", type=int, default=81, help="T (Wan-Move often ~81 @24fps ~3.3s; 5s~121)")
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--apart-dx", type=float, default=100.0)
    ap.add_argument("--still", type=Path, default=None, help="for --vis overlay; also used as src size if --src-still set")
    ap.add_argument(
        "--src-still",
        type=Path,
        default=None,
        help="ORIGINAL full-res still used for analysis (e.g. 1920x1080). Required for correct coords.",
    )
    ap.add_argument("--src-w", type=int, default=None)
    ap.add_argument("--src-h", type=int, default=None)
    ap.add_argument("--vis", action="store_true")
    ap.add_argument("--json-meta", type=Path, default=None)
    args = ap.parse_args()

    kp, meta = _load_kp2(args.analysis)
    # Source resolution MUST match analysis image (usually 1920x1080 anchors).
    # Do NOT infer from max joint x (knees ~800px → wrongly became 1280x720).
    src_w = args.src_w or meta.get("src_w")
    src_h = args.src_h or meta.get("src_h")
    src_still = args.src_still
    if src_still is None:
        cand = Path("_src/0009_still_day21_10_sophia_dylan_evening_675.jpeg")
        if cand.is_file():
            src_still = cand
    if src_still is not None and Path(src_still).is_file():
        from PIL import Image as _Image

        sw0, sh0 = _Image.open(src_still).size
        src_w, src_h = sw0, sh0
        print(f"src_still {src_still} → {src_w}x{src_h}")
    if not src_w or not src_h:
        src_w, src_h = 1920, 1080
        print(f"WARN defaulting src to {src_w}x{src_h}")

    tracks = build_e01_open_tracks(
        kp,
        T=args.frames,
        width=args.width,
        height=args.height,
        src_w=src_w,
        src_h=src_h,
        apart_dx=args.apart_dx,
    )
    # sanity: start knees should land near body center of 832x480 still
    lx0, ly0 = float(tracks[0, 0, 0]), float(tracks[0, 0, 1])
    if not (200 < lx0 < 600 and 150 < ly0 < 450):
        print(f"WARN start Lknee ({lx0:.0f},{ly0:.0f}) looks off-body — check src size")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.out, tracks)
    print("wrote", args.out, "shape", tracks.shape, "dtype", tracks.dtype)
    print("start Lknee", tracks[0, 0], "Rknee", tracks[0, 1])
    print("end   Lknee", tracks[-1, 0], "Rknee", tracks[-1, 1])
    print("end dy", abs(tracks[-1, 0, 1] - tracks[-1, 1, 1]), "dx", abs(tracks[-1, 0, 0] - tracks[-1, 1, 0]))

    meta_out = {
        "out": str(args.out),
        "shape": list(tracks.shape),
        "width": args.width,
        "height": args.height,
        "frames": args.frames,
        "analysis": str(args.analysis),
        "src_wh": [src_w, src_h],
        "apart_dx": args.apart_dx,
        "points": ["L_knee", "R_knee", "L_ankle", "R_ankle", "R_wrist", "L_wrist"],
        "wan2gp": "custom_guide npy [T,N,2] pixel coords (hands leave knee)",
    }
    mp = args.json_meta or args.out.with_suffix(".json")
    mp.write_text(json.dumps(meta_out, indent=2), encoding="utf-8")
    print("meta", mp)

    if args.vis:
        still = args.still
        if still is None:
            # try fixture still
            cand = Path("_src/0009_still_day21_10_sophia_dylan_evening_675.jpeg")
            still = cand if cand.is_file() else None
        if still and still.is_file():
            vis_overlay(still, tracks, args.out.with_suffix(".vis.jpg"), args.width, args.height)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
