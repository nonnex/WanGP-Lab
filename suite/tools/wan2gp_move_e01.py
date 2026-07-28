#!/usr/bin/env python3
"""Headless Wan2GP Wan-Move e01 (no Gradio UI).

  bash suite/tools/run_move_e01.sh --frames 49 --steps 16 --profile 4 --seed 7

Requires wangp/ckpts/:
  wan2.1_wanmove_14B_quanto_mbf16_int8.safetensors
  umt5-xxl/models_t5_umt5-xxl-enc-quanto_int8.safetensors
  Wan2.1_VAE.safetensors
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SUITE = Path(os.environ.get("WANGP_LAB_ROOT", Path(__file__).resolve().parents[2]))
WGP = Path(os.environ.get("WANGP_ROOT", SUITE / "wangp"))
MOTOR = Path(
    os.environ.get(
        "LAB_MOTOR_ROOT",
        os.environ.get("AIIMGSEQ_LAB_ROOT", "/home/nick/AI/Projects/ai-img-seq-kimi"),
    )
)
WGP_PY = WGP / ".venv" / "bin" / "python"
LAB_PY = MOTOR / "pipeline" / ".venv" / "bin" / "python"
CACHE = Path(os.environ.get("WANGP_LAB_CACHE", SUITE / "data" / "cache" / "wanmove"))

DEFAULT_STILL = CACHE / "still_675_832x480.jpg"
DEFAULT_TRACKS = CACHE / "tracks_e01_open_hands_t49.npy"
DEFAULT_PROMPT = (
    "Same woman as the start image, seated upright, locked face. "
    "Slowly uncross legs: lower the top knee until both knees are level, "
    "then slide knees apart left-right until thighs sit side by side with a clear gap. "
    "Hands leave the knee and rest on the thigh or mattress beside the hip. "
    "Feet stay down. No kick, no lying flat. Static camera."
)
DEFAULT_NEG = (
    "hand stuck on knee, hand glued to knee, frozen hand on leg, kick, raised leg, "
    "lying down, reclining flat, frozen cross, thighs stacked, legs stay crossed, "
    "morphing face, identity drift, camera move, zoom, pan"
)

RUNNER_SRC = r'''#!/usr/bin/env python3
import json, sys, time, traceback
from pathlib import Path

WGP = Path({wgp!r})
sys.path.insert(0, str(WGP))
from shared.api import init

settings_path = Path({settings_path!r})
out_dir = Path({out!r})
log_path = out_dir / "wan2gp_api.log"
log_path.write_text("", encoding="utf-8")

def log(msg):
    line = f"{{time.strftime('%H:%M:%S')}} {{msg}}"
    print(line, flush=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

try:
    user = json.loads(settings_path.read_text())
    log("init profile={profile}")
    session = init(
        root=WGP,
        output_dir=out_dir / "outputs",
        cli_args=["--attention", "{attention}", "--profile", "{profile}"],
        console_output=False,
    )
    settings = session.get_default_settings(user["model_type"])
    settings.update(user)
    settings["image_start"] = str(Path(settings["image_start"]).resolve())
    settings["custom_guide"] = str(Path(settings["custom_guide"]).resolve())
    settings_path.write_text(json.dumps(settings, indent=2, default=str))
    log(f"availability {{session.get_model_availability(user['model_type'])}}")
    log("submit")
    job = session.submit_task(settings)
    t0 = time.time()
    last = None
    for event in job.events.iter(timeout=1.0):
        if event.kind == "progress":
            p = event.data
            key = (
                getattr(p, "phase", None),
                getattr(p, "current_step", None),
                getattr(p, "total_steps", None),
            )
            if key != last:
                last = key
                log(f"progress {{key[0]}} {{key[1]}}/{{key[2]}} t={{time.time()-t0:.0f}}s")
        elif event.kind == "error":
            log(f"ERROR {{event.data!r}}")
    log("result()")
    result = job.result()
    meta = {{
        "success": bool(result.success),
        "generated_files": [str(x) for x in (getattr(result, "generated_files", None) or [])],
        "errors": [getattr(e, "message", str(e)) for e in (getattr(result, "errors", None) or [])],
        "elapsed_s": round(time.time() - t0, 1),
    }}
    (out_dir / "result.json").write_text(json.dumps(meta, indent=2))
    log("RESULT " + json.dumps(meta))
    sys.exit(0 if result.success else 3)
except Exception:
    log("EXCEPTION\n" + traceback.format_exc())
    sys.exit(1)
'''


def _check_ckpts() -> list[str]:
    need = [
        WGP / "ckpts/wan2.1_wanmove_14B_quanto_mbf16_int8.safetensors",
        WGP / "ckpts/umt5-xxl/models_t5_umt5-xxl-enc-quanto_int8.safetensors",
        WGP / "ckpts/Wan2.1_VAE.safetensors",
    ]
    return [str(p) for p in need if not p.is_file() or p.stat().st_size < 1_000_000]


def _extract_frames(video: Path, frames_dir: Path) -> int:
    """Extract jpg frames. Prefer ffmpeg; fallback Lab imageio (no system ffmpeg on bare WSL)."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    for pat in list(frames_dir.glob("*.jpg")):
        pat.unlink(missing_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        subprocess.run(
            [ffmpeg, "-y", "-i", str(video), str(frames_dir / "%04d.jpg")],
            check=False,
            capture_output=True,
        )
        n = len(list(frames_dir.glob("*.jpg")))
        if n >= 2:
            return n
    if LAB_PY.is_file():
        code = subprocess.run(
            [
                str(LAB_PY),
                "-c",
                f"""
from pathlib import Path
import imageio.v3 as iio
from PIL import Image
vid=Path({str(video)!r}); out=Path({str(frames_dir)!r})
out.mkdir(parents=True, exist_ok=True)
frames=iio.imread(vid)
for i,f in enumerate(frames):
    Image.fromarray(f).save(out/f'{{i:04d}}.jpg', quality=92)
print(len(list(out.glob('*.jpg'))))
""",
            ],
            cwd=str(MOTOR),
            capture_output=True,
            text=True,
        )
        if code.returncode == 0:
            return len(list(frames_dir.glob("*.jpg")))
        print(code.stderr or code.stdout, file=sys.stderr)
    return len(list(frames_dir.glob("*.jpg")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--still", type=Path, default=DEFAULT_STILL)
    ap.add_argument("--tracks", type=Path, default=DEFAULT_TRACKS)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--negative", default=DEFAULT_NEG)
    ap.add_argument("--frames", type=int, default=49)
    ap.add_argument("--steps", type=int, default=16)
    ap.add_argument("--seed", type=int, default=33)
    ap.add_argument("--profile", type=float, default=4)
    ap.add_argument("--attention", default="sage")
    ap.add_argument("--tea-cache", type=float, default=0.0)
    ap.add_argument("--resolution", default="832x480")
    ap.add_argument("--model-type", default="wanmove")
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--skip-gate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.frames != 49:
        alt = CACHE / f"tracks_e01_open_hands_t{args.frames}.npy"
        if alt.is_file() and (
            args.tracks == DEFAULT_TRACKS or not Path(args.tracks).is_file()
        ):
            args.tracks = alt

    if not WGP.is_dir() or not WGP_PY.is_file():
        print(f"Wan2GP or venv missing: {WGP}", file=sys.stderr)
        return 2

    missing = _check_ckpts()
    if missing and not args.dry_run:
        print("MISSING ckpts:", file=sys.stderr)
        for m in missing:
            print(" ", m, file=sys.stderr)
        return 2

    still = Path(args.still)
    tracks = Path(args.tracks)
    if not still.is_absolute():
        still = SUITE / still
    if not tracks.is_absolute():
        tracks = SUITE / tracks
    if not still.is_file() or not tracks.is_file():
        print(f"missing still or tracks:\n  {still}\n  {tracks}", file=sys.stderr)
        return 2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_root = Path(os.environ.get("WANGP_LAB_EXPERIMENTS", SUITE / "data" / "experiments"))
    out = Path(args.out_dir) if args.out_dir else exp_root / f"{ts}_wan2gp_move_e01"
    if not out.is_absolute():
        out = SUITE / out
    out.mkdir(parents=True, exist_ok=True)
    (out / "inputs").mkdir(exist_ok=True)
    (out / "outputs").mkdir(exist_ok=True)
    shutil.copy2(still, out / "inputs" / "still.jpg")
    shutil.copy2(tracks, out / "inputs" / "tracks.npy")

    settings = {
        "model_type": args.model_type,
        "prompt": args.prompt,
        "negative_prompt": args.negative,
        "resolution": args.resolution,
        "video_length": args.frames,
        "num_inference_steps": args.steps,
        "seed": args.seed,
        "force_fps": 24,
        "image_prompt_type": "S",
        "image_start": str(still.resolve()),
        "custom_guide": str(tracks.resolve()),
        "video_prompt_type": "",
        "prompt_enhancer": "",
        "flow_shift": 7.0,
        "sample_solver": "unipc",
        "settings_version": 2.66,
    }
    if args.tea_cache and args.tea_cache > 0:
        settings["skip_steps_cache_type"] = "tea"
        settings["teacache_multiplier"] = float(args.tea_cache)
        settings["tea_cache"] = float(args.tea_cache)

    settings_path = out / "wan2gp_settings.json"
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print("settings", settings_path)
    print(json.dumps(settings, indent=2))
    if args.dry_run:
        print("dry-run only")
        return 0

    runner = out / "_run_api.py"
    runner.write_text(
        RUNNER_SRC.format(
            wgp=str(WGP),
            settings_path=str(settings_path),
            out=str(out),
            profile=int(args.profile),
            attention=args.attention,
        ),
        encoding="utf-8",
    )

    print("running", WGP_PY, runner)
    print("log", out / "wan2gp_api.log")
    proc = subprocess.run([str(WGP_PY), str(runner)], cwd=str(WGP))
    print("exit", proc.returncode)
    log_path = out / "wan2gp_api.log"
    if log_path.is_file():
        print("--- log ---")
        print("\n".join(log_path.read_text(errors="replace").splitlines()[-40:]))
    if proc.returncode != 0:
        return proc.returncode

    outs = sorted(
        (out / "outputs").rglob("*.mp4") if (out / "outputs").is_dir() else [],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not outs:
        print("no mp4", file=sys.stderr)
        return 4
    video = outs[0]
    print("video", video)
    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)
    n_frames = _extract_frames(video, frames_dir)
    print("frames", n_frames, frames_dir)
    if n_frames < 2:
        print("frame extract failed", file=sys.stderr)
        return 5

    gate_rc = 0
    if not args.skip_gate and LAB_PY.is_file():
        gate_json = out / "pose_gate_open_end.json"
        g = subprocess.run(
            [
                str(LAB_PY),
                str(MOTOR / "pipeline" / "pose_gate.py"),
                "hop",
                "--frames",
                str(frames_dir),
                "--mode",
                "open_end",
                "--json-out",
                str(gate_json),
            ],
            cwd=str(MOTOR),
        )
        gate_rc = 0 if g.returncode in (0, 3) else g.returncode
        if gate_json.is_file():
            print(gate_json.read_text()[:1200])
            _append_leaderboard(out, gate_json, args.seed, args.frames, args.steps)
        rolling = exp_root / "last_pose_gate_open_end.json"
        if gate_json.is_file():
            shutil.copy2(gate_json, rolling)

    if os.environ.get("WANGP_LAB_NO_PRUNE", "") not in ("1", "true", "yes"):
        _prune_old_runs(exp_root)

    return gate_rc


def _append_leaderboard(
    run_dir: Path, gate_json: Path, seed: int, frames: int, steps: int
) -> None:
    try:
        d = json.loads(gate_json.read_text())
    except Exception:
        return
    board = run_dir.parent / "LEADERBOARD.tsv"
    if not board.is_file():
        board.write_text(
            "ts\tseed\tframes\tsteps\tok\tprogress\tphase\tnote\tpath\n",
            encoding="utf-8",
        )
    line = "\t".join(
        [
            datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            str(seed),
            str(frames),
            str(steps),
            str(bool(d.get("ok"))),
            f"{float(d.get('progress') or 0):.4f}",
            str(d.get("phase") or ""),
            str(d.get("note") or "").replace("\t", " "),
            str(run_dir.name),
        ]
    )
    with board.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("leaderboard", board)


def _prune_old_runs(exp_root: Path) -> None:
    """Full lab hygiene (prune + symlink + spam)."""
    script = SUITE / "suite" / "scripts" / "lab_hygiene.sh"
    if script.is_file():
        subprocess.run(["bash", str(script), "--quiet"], check=False)
        return
    legacy = SUITE / "suite" / "scripts" / "prune_experiments.sh"
    if legacy.is_file():
        keep = os.environ.get("WANGP_LAB_KEEP_RUNS", "2")
        subprocess.run(["bash", str(legacy), str(keep)], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
