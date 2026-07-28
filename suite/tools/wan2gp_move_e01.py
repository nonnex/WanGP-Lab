#!/usr/bin/env python3
"""Headless Wan2GP Wan-Move e01 smoke (no Gradio UI).

Uses Wan2GP Python API with sparse logging (no tqdm/[stdout] spam).

  bash suite/scripts/start_wangp.sh   # UI
  bash suite/tools/run_move_e01.sh    # headless

Requires ckpts under wangp/ckpts/:
  - wan2.1_wanmove_14B_quanto_mbf16_int8.safetensors
  - umt5-xxl/models_t5_umt5-xxl-enc-quanto_int8.safetensors
  - Wan2.1_VAE.safetensors
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

# suite/tools/this.py → parents[2] = WanGP-Lab root
SUITE = Path(os.environ.get("WANGP_LAB_ROOT", Path(__file__).resolve().parents[2]))
WGP = Path(os.environ.get("WANGP_ROOT", os.environ.get("AIIMGSEQ_WANGP_ROOT", SUITE / "wangp")))
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


def _check_ckpts() -> list[str]:
    missing = []
    need = [
        WGP / "ckpts/wan2.1_wanmove_14B_quanto_mbf16_int8.safetensors",
        WGP / "ckpts/umt5-xxl/models_t5_umt5-xxl-enc-quanto_int8.safetensors",
        WGP / "ckpts/Wan2.1_VAE.safetensors",
    ]
    for p in need:
        if not p.is_file() or p.stat().st_size < 1_000_000:
            missing.append(str(p))
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--still", type=Path, default=DEFAULT_STILL)
    ap.add_argument("--tracks", type=Path, default=DEFAULT_TRACKS)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--negative", default=DEFAULT_NEG)
    ap.add_argument("--frames", type=int, default=49, help="default 49 (faster); 81 full")
    ap.add_argument("--steps", type=int, default=16, help="default 16 (faster); 30 quality")
    ap.add_argument("--seed", type=int, default=33)
    ap.add_argument(
        "--profile",
        type=float,
        default=4,
        help="4=default on 24GB RAM host; 2=faster if RAM free; 5=fail-safe",
    )
    ap.add_argument("--attention", default="sage", help="sage (installed)|auto|sdpa|sage2")
    ap.add_argument("--tea-cache", type=float, default=0.0, help="0=off; try 1.5-2.0 if supported")
    ap.add_argument("--resolution", default="832x480")
    ap.add_argument("--model-type", default="wanmove")
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--skip-gate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    # auto-pick hands tracks matching frame count
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
        print("MISSING ckpts (download first):", file=sys.stderr)
        for m in missing:
            print(" ", m, file=sys.stderr)
        return 2

    still = args.still if Path(args.still).is_absolute() else SUITE / args.still
    tracks = args.tracks if Path(args.tracks).is_absolute() else SUITE / args.tracks
    still, tracks = Path(still), Path(tracks)
    if not still.is_file() or not tracks.is_file():
        print(f"missing still or tracks:\n  {still}\n  {tracks}", file=sys.stderr)
        return 2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_root = Path(
        os.environ.get("WANGP_LAB_EXPERIMENTS", SUITE / "data" / "experiments")
    )
    out = args.out_dir or (exp_root / f"{ts}_wan2gp_move_e01")
    out = out if Path(out).is_absolute() else SUITE / out
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "inputs").mkdir(exist_ok=True)
    (out / "outputs").mkdir(exist_ok=True)
    shutil.copy2(still, out / "inputs" / "still.jpg")
    shutil.copy2(tracks, out / "inputs" / "tracks.npy")

    # Merge defaults from API would be ideal; minimal required keys:
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
        # trajectory file via custom_guide; keep video_prompt_type empty (forced "")
        "video_prompt_type": "",
        "prompt_enhancer": "",
        "flow_shift": 7.0,
        "sample_solver": "unipc",
        "settings_version": 2.66,
    }
    if args.tea_cache and args.tea_cache > 0:
        settings["skip_steps_cache_type"] = "tea"
        settings["teacache_multiplier"] = float(args.tea_cache)
        # alternate key names used in some WanGP versions
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
        f"""#!/usr/bin/env python3
import json, sys, time, traceback
from pathlib import Path

WGP = Path({str(WGP)!r})
sys.path.insert(0, str(WGP))
from shared.api import init

settings = json.loads(Path({str(settings_path)!r}).read_text())
out_dir = Path({str(out)!r})
log_path = out_dir / "wan2gp_api.log"
log_path.write_text("", encoding="utf-8")

def log(msg):
    line = f"{{time.strftime('%H:%M:%S')}} {{msg}}"
    print(line, flush=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\\n")

try:
    log("init session profile={args.profile}")
    session = init(
        root=WGP,
        output_dir=out_dir / "outputs",
        cli_args=["--attention", "{args.attention}", "--profile", "{int(args.profile)}"],
        console_output=False,
    )
    # start from model defaults then override
    base = session.get_default_settings(settings["model_type"])
    base.update(settings)
    settings = base
    Path({str(settings_path)!r}).write_text(json.dumps(settings, indent=2, default=str))
    log(f"settings keys={{sorted(settings.keys())}}")
    av = session.get_model_availability(settings["model_type"])
    log(f"availability {{av}}")
    log("submit_task")
    job = session.submit_task(settings)
    log("job submitted")
    last = None
    t0 = time.time()
    while True:
        # poll events without printing empty streams
        got = False
        for event in job.events.iter(timeout=2.0):
            got = True
            if event.kind == "progress":
                p = event.data
                key = (getattr(p, "phase", None), getattr(p, "current_step", None), getattr(p, "total_steps", None))
                if key != last:
                    last = key
                    log(f"progress phase={{key[0]}} step={{key[1]}}/{{key[2]}} t={{time.time()-t0:.0f}}s")
            elif event.kind == "error":
                log(f"EVENT_ERROR {{event.data!r}}")
            elif event.kind == "preview":
                log("preview frame")
            # ignore stream entirely (causes [stdout] spam)
        if job.done() if hasattr(job, "done") else False:
            break
        # fallback: try result with short wait
        try:
            if hasattr(job, "events") and hasattr(job.events, "empty"):
                pass
        except Exception:
            pass
        # break when result ready - use non-blocking if available
        if hasattr(job, "_result") and getattr(job, "_result", None) is not None:
            break
        # if no events for a while, check result with timeout 0
        try:
            # SessionJob.result() blocks - only call once loop ends via events
            pass
        except Exception:
            pass
        # detect completion via internal flag
        if getattr(job, "finished", False) or getattr(job, "_finished", False):
            break
        # safety: if events iterator returned nothing, try wait result with 0.1s
        # Actually API: after events exhaust, call result()
        if not got:
            # brief sleep then try result without long block
            time.sleep(1)
            # if job has is_done
            if hasattr(job, "is_done") and job.is_done():
                break
            # after 5s idle with no events, still wait for result at end
            if time.time() - t0 > 5 and last is not None:
                # still generating - continue
                pass
            if time.time() - t0 > 7200:
                log("TIMEOUT 2h")
                sys.exit(4)
        # Prefer blocking result after first progress done? Use result() at end only.
        # Check if events channel closed
        if hasattr(job.events, "closed") and job.events.closed:
            break
        # API pattern from docs: for event in job.events.iter(); then result()
        # iter ends when job completes - so when loop exits naturally...
        # Our timeout-based iter never ends. Fix: call result in thread or use longer pattern.

    # Docs: exhaust events then result(). With timeout iter, call result() which waits.
    log("waiting result()")
    result = job.result()
    meta = {{
        "success": bool(result.success),
        "generated_files": [str(x) for x in (result.generated_files or [])],
        "errors": [getattr(e, "message", str(e)) for e in (result.errors or [])],
        "elapsed_s": round(time.time() - t0, 1),
    }}
    (out_dir / "result.json").write_text(json.dumps(meta, indent=2))
    log("RESULT " + json.dumps(meta))
    sys.exit(0 if result.success else 3)
except Exception:
    log("EXCEPTION\\n" + traceback.format_exc())
    sys.exit(1)
""",
        encoding="utf-8",
    )

    # Simpler runner: docs-faithful event loop without stream spam
    runner.write_text(
        f"""#!/usr/bin/env python3
import json, sys, time, traceback
from pathlib import Path

WGP = Path({str(WGP)!r})
sys.path.insert(0, str(WGP))
from shared.api import init

settings_path = Path({str(settings_path)!r})
out_dir = Path({str(out)!r})
log_path = out_dir / "wan2gp_api.log"
log_path.write_text("", encoding="utf-8")

def log(msg):
    line = f"{{time.strftime('%H:%M:%S')}} {{msg}}"
    print(line, flush=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\\n")

try:
    user = json.loads(settings_path.read_text())
    log("init profile={args.profile}")
    session = init(
        root=WGP,
        output_dir=out_dir / "outputs",
        cli_args=["--attention", "{args.attention}", "--profile", "{int(args.profile)}"],
        console_output=False,
    )
    settings = session.get_default_settings(user["model_type"])
    settings.update(user)
    # ensure required paths absolute
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
            key = (getattr(p, "phase", None), getattr(p, "current_step", None), getattr(p, "total_steps", None))
            if key != last:
                last = key
                log(f"progress {{key[0]}} {{key[1]}}/{{key[2]}} t={{time.time()-t0:.0f}}s")
        elif event.kind == "error":
            log(f"ERROR {{event.data!r}}")
        # skip stream/preview spam
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
    log("EXCEPTION\\n" + traceback.format_exc())
    sys.exit(1)
""",
        encoding="utf-8",
    )

    print("running", WGP_PY, runner)
    print("log will be", out / "wan2gp_api.log")
    proc = subprocess.run([str(WGP_PY), str(runner)], cwd=str(WGP))
    print("exit", proc.returncode)
    log_path = out / "wan2gp_api.log"
    if log_path.is_file():
        print("--- log ---")
        print("\n".join(log_path.read_text(errors="replace").splitlines()[-50:]))

    if proc.returncode != 0:
        return proc.returncode

    outs = []
    if (out / "outputs").is_dir():
        outs += list((out / "outputs").rglob("*.mp4"))
    if (WGP / "outputs").is_dir():
        outs += list((WGP / "outputs").rglob("*.mp4"))
    outs = sorted(set(outs), key=lambda p: p.stat().st_mtime, reverse=True)
    if not outs:
        print("no mp4", file=sys.stderr)
        return 4
    video = outs[0]
    print("video", video)
    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), str(frames_dir / "%04d.jpg")],
        check=False,
        capture_output=True,
    )
    print("frames", len(list(frames_dir.glob("*.jpg"))), frames_dir)

    if args.skip_gate or not LAB_PY.is_file():
        return 0
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
    if gate_json.is_file():
        print(gate_json.read_text()[:1000])
    return 0 if g.returncode in (0, 3) else g.returncode


if __name__ == "__main__":
    raise SystemExit(main())
