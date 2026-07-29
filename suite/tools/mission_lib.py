#!/usr/bin/env python3
"""Generic mission load / stage / run-card / gate-hint helpers (suite SoT)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

SUITE = Path(os.environ.get("WANGP_LAB_ROOT", Path(__file__).resolve().parents[2]))
MISSIONS_DIR = SUITE / "suite" / "missions"
DEFAULT_WGP = Path(os.environ.get("WANGP_ROOT", SUITE / "wangp"))
DEFAULT_EXP = Path(os.environ.get("WANGP_LAB_EXPERIMENTS", SUITE / "data" / "experiments"))


def _resolve(p: str | Path, root: Path = SUITE) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def list_missions() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not MISSIONS_DIR.is_dir():
        return out
    for d in sorted(MISSIONS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        mf = d / "mission.json"
        if not mf.is_file():
            continue
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
            m["_path"] = str(mf)
            out.append(m)
        except Exception:
            continue
    return out


def load_mission(mission_id: str) -> dict[str, Any]:
    # exact folder or id field
    for m in list_missions():
        if m.get("id") == mission_id or Path(m.get("_path", "")).parent.name == mission_id:
            return m
    # legacy alias
    if mission_id in ("e01", "default", ""):
        return load_mission("e01_uncross_open")
    raise FileNotFoundError(f"mission not found: {mission_id}")


def default_mission_id() -> str:
    env = os.environ.get("WANGP_LAB_MISSION", "").strip()
    if env:
        return env
    ids = [m.get("id") for m in list_missions() if m.get("id")]
    if "e01_uncross_open" in ids:
        return "e01_uncross_open"
    return ids[0] if ids else "e01_uncross_open"


def load_gate_hints() -> dict[str, Any]:
    p = MISSIONS_DIR / "gate_hints.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def gate_next_action(phase: str | None, note: str | None = None) -> dict[str, str]:
    hints = load_gate_hints()
    key = (phase or "unknown").strip() or "unknown"
    # strip prefixes like late_not_open:phase
    if ":" in key:
        key = key.split(":")[-1]
    h = hints.get(key) or hints.get("unknown") or {
        "summary": key,
        "next": "Inspect gate JSON and track END preview.",
    }
    return {
        "phase": key,
        "summary": str(h.get("summary", "")),
        "next": str(h.get("next", "")),
        "note": note or "",
    }


def file_sha8(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def stage_into_wangp(src: Path | None, wgp: Path | None = None) -> Path | None:
    """Copy file under wangp/mask_outputs for Gradio CWD safety."""
    if src is None:
        return None
    src = Path(src)
    if not src.is_file():
        return None
    wgp = Path(wgp or DEFAULT_WGP)
    try:
        if src.resolve().is_relative_to(wgp.resolve()):
            return src.resolve()
    except Exception:
        pass
    dst_dir = wgp / "mask_outputs"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if (
        not dst.is_file()
        or dst.stat().st_mtime < src.stat().st_mtime
        or dst.stat().st_size != src.stat().st_size
    ):
        shutil.copy2(src, dst)
    return dst.resolve()


def mission_still(m: dict[str, Any], *, smoke: bool = False) -> Path:
    assets = m.get("assets") or {}
    key = "still_smoke" if smoke and assets.get("still_smoke") else "still"
    return _resolve(assets.get(key) or assets.get("still") or "")


def mission_tracks(m: dict[str, Any], frames: int) -> Path:
    assets = m.get("assets") or {}
    tracks = assets.get("tracks") or {}
    # json keys may be str
    p = tracks.get(str(frames)) or tracks.get(frames) or tracks.get("49")
    if not p:
        # first available
        p = next(iter(tracks.values()), "")
    return _resolve(p)


def ladder_step(m: dict[str, Any], level: str) -> dict[str, Any]:
    ladder = m.get("ladder") or {}
    if level not in ladder:
        raise KeyError(f"mission {m.get('id')} has no ladder.{level}")
    return dict(ladder[level])


def apply_ladder_to_settings(
    settings: dict[str, Any],
    m: dict[str, Any],
    level: str,
    *,
    seed_override: int | None = None,
    steps_override: int | None = None,
    wgp: Path | None = None,
) -> dict[str, Any]:
    """Mutate WanGP settings dict from mission ladder level. Returns settings."""
    step = ladder_step(m, level)
    frames = int(step.get("frames", 49))
    steps = int(steps_override if steps_override is not None else step.get("steps", 16))
    seed = int(seed_override if seed_override is not None else step.get("seed", 33))
    use_tracks = bool(step.get("use_tracks", level != "L0"))

    settings["prompt"] = m.get("prompt") or settings.get("prompt") or ""
    settings["negative_prompt"] = m.get("negative_prompt") or settings.get("negative_prompt") or ""
    settings["resolution"] = step.get("resolution") or "832x480"
    settings["video_length"] = frames
    settings["num_inference_steps"] = steps
    settings["seed"] = seed
    settings["force_fps"] = str(step.get("force_fps", "24"))
    settings["flow_shift"] = step.get("flow_shift", 7.0)
    settings["sample_solver"] = step.get("sample_solver", "unipc")
    settings["guidance_scale"] = step.get("guidance_scale", 4.0)
    settings["image_prompt_type"] = "S"
    settings["prompt_enhancer"] = ""
    settings["output_filename"] = m.get("output_filename") or m.get("id") or "lab_mission"

    still = mission_still(m, smoke=(level == "L0"))
    still_s = stage_into_wangp(still, wgp)
    if still_s is not None:
        # Motion Designer uses list for image_start gallery
        settings["image_start"] = [str(still_s)]

    if use_tracks:
        tr = mission_tracks(m, frames)
        tr_s = stage_into_wangp(tr, wgp)
        if tr_s is not None:
            settings["custom_guide"] = str(tr_s)
    else:
        settings["custom_guide"] = None
        if level == "L0":
            settings["repeat_generation"] = int(step.get("repeat_generation", 3))

    settings["_lab_mission"] = m.get("id")
    settings["_lab_level"] = level
    return settings


def write_run_card(
    exp_dir: Path,
    *,
    mission_id: str,
    level: str,
    settings: dict[str, Any],
    gate: dict[str, Any] | None = None,
    video: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write run_card.json for research UX (generic)."""
    exp_dir = Path(exp_dir)
    exp_dir.mkdir(parents=True, exist_ok=True)
    still = settings.get("image_start")
    if isinstance(still, list) and still:
        still_p = Path(str(still[0]))
    elif still:
        still_p = Path(str(still))
    else:
        still_p = None
    tracks_p = Path(settings["custom_guide"]) if settings.get("custom_guide") else None

    phase = None
    if gate:
        phase = gate.get("phase") or (gate.get("note") or "").split(":")[-1]
    hint = gate_next_action(phase, gate.get("note") if gate else None)

    card = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "mission_id": mission_id,
        "level": level,
        "seed": settings.get("seed"),
        "frames": settings.get("video_length"),
        "steps": settings.get("num_inference_steps"),
        "resolution": settings.get("resolution"),
        "model_hint": settings.get("output_filename"),
        "still": str(still_p) if still_p else None,
        "still_sha8": file_sha8(still_p) if still_p else "",
        "tracks": str(tracks_p) if tracks_p else None,
        "tracks_sha8": file_sha8(tracks_p) if tracks_p else "",
        "video": str(video) if video else None,
        "gate": {
            "ok": gate.get("ok") if gate else None,
            "pose_pass": gate.get("pose_pass") if gate else None,
            "progress": gate.get("progress") if gate else None,
            "phase": phase,
            "note": gate.get("note") if gate else None,
            "late_open": gate.get("late_open") if gate else None,
        },
        "next_action": hint,
        "extra": extra or {},
    }
    out = exp_dir / "run_card.json"
    out.write_text(json.dumps(card, indent=2), encoding="utf-8")
    # also append slim leaderboard
    board = DEFAULT_EXP / "LEADERBOARD.tsv"
    if not board.is_file():
        board.write_text(
            "ts\tmission\tlevel\tseed\tframes\tsteps\tok\tprogress\tphase\tpath\n",
            encoding="utf-8",
        )
    with board.open("a", encoding="utf-8") as f:
        f.write(
            "\t".join(
                [
                    card["ts"],
                    mission_id,
                    level,
                    str(card["seed"]),
                    str(card["frames"]),
                    str(card["steps"]),
                    str(bool(card["gate"].get("ok"))),
                    f"{float(card['gate'].get('progress') or 0):.4f}",
                    str(phase or ""),
                    exp_dir.name,
                ]
            )
            + "\n"
        )
    return out


def leaderboard_md(exp: Path | None = None, n: int = 10) -> str:
    exp = Path(exp or DEFAULT_EXP)
    board = exp / "LEADERBOARD.tsv"
    if not board.is_file():
        return "_No runs yet. Gate a generation to fill the leaderboard._"
    lines = board.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) < 2:
        return "_Leaderboard empty._"
    hdr = lines[0].split("\t")
    rows = [ln.split("\t") for ln in lines[1:] if ln.strip()][-n:]

    def col(r: list[str], name: str, default: str = "") -> str:
        try:
            return r[hdr.index(name)]
        except Exception:
            return default

    # support old and new headers
    out = [
        "| mission | lvl | seed | progress | phase | ok | path |",
        "|---------|-----|------|----------|-------|----|------|",
    ]
    for r in reversed(rows):
        out.append(
            "| {m} | {lv} | {s} | **{p}** | `{ph}` | {ok} | `{path}` |".format(
                m=col(r, "mission", col(r, "path", "")[:12]),
                lv=col(r, "level", "—"),
                s=col(r, "seed"),
                p=col(r, "progress"),
                ph=col(r, "phase"),
                ok=col(r, "ok"),
                path=col(r, "path"),
            )
        )
    return "\n".join(out)


def format_gate_summary(gate: dict[str, Any]) -> str:
    phase = gate.get("phase") or (str(gate.get("note") or "").split(":")[-1] or None)
    hint = gate_next_action(phase, gate.get("note"))
    block = {
        "ok": gate.get("ok"),
        "pose_pass": gate.get("pose_pass"),
        "progress": gate.get("progress"),
        "phase": phase,
        "note": gate.get("note"),
        "late_open": gate.get("late_open"),
        "next_action": hint,
    }
    return json.dumps(block, indent=2)


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for m in list_missions():
            print(f"{m.get('id')}\t{m.get('title')}")
    elif cmd == "show":
        print(json.dumps(load_mission(sys.argv[2]), indent=2))
    else:
        print("usage: mission_lib.py list|show <id>")
