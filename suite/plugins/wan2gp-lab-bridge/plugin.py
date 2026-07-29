"""Lab Bridge — WanGP plugin (Cockpit ↔ Motor).

Mission ops: tracks → preview → ladder presets → generate → gate last output.
Lab tools run in pipeline/.venv only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import gradio as gr

from shared.utils.plugins import WAN2GPPlugin

PLUGIN_ID = "wan2gp-lab-bridge"
PLUGIN_NAME = "Lab Bridge"

DEFAULT_SUITE_ROOT = Path(
    os.environ.get("WANGP_LAB_ROOT", "/home/nick/AI/Projects/WanGP-Lab")
)
DEFAULT_LAB_ROOT = Path(
    os.environ.get(
        "LAB_MOTOR_ROOT",
        os.environ.get("AIIMGSEQ_LAB_ROOT", "/home/nick/AI/Projects/ai-img-seq-kimi"),
    )
)
DEFAULT_WGP_ROOT = Path(
    os.environ.get(
        "WANGP_ROOT",
        os.environ.get("AIIMGSEQ_WANGP_ROOT", str(DEFAULT_SUITE_ROOT / "wangp")),
    )
)
DEFAULT_SUITE_CACHE = Path(
    os.environ.get(
        "WANGP_LAB_CACHE",
        str(DEFAULT_SUITE_ROOT / "data" / "cache" / "wanmove"),
    )
)
DEFAULT_OUTPUTS = Path(
    os.environ.get(
        "WANGP_LAB_OUTPUTS",
        str(DEFAULT_SUITE_ROOT / "_outputs"),
    )
)
DEFAULT_EXPERIMENTS = Path(
    os.environ.get(
        "WANGP_LAB_EXPERIMENTS",
        str(DEFAULT_SUITE_ROOT / "data" / "experiments"),
    )
)


def _tracks_script(suite: Path, lab: Path) -> Path:
    for p in (
        suite / "suite" / "tools" / "mhr70_to_wanmove_tracks.py",
        lab / "lab" / "tools" / "mhr70_to_wanmove_tracks.py",
    ):
        if p.is_file():
            return p
    return suite / "suite" / "tools" / "mhr70_to_wanmove_tracks.py"


PROMPT_E01 = (
    "Same woman as the start image, seated upright, locked face. "
    "Slowly uncross legs: lower the top knee until both knees are level, "
    "then slide knees apart left-right until thighs sit side by side with a clear gap. "
    "Hands leave the knee and rest on the thigh or mattress beside the hip. "
    "Feet stay down. No kick, no lying flat. Static camera."
)
NEG_E01 = (
    "hand stuck on knee, hand glued to knee, frozen hand on leg, kick, raised leg, "
    "lying down, reclining flat, frozen cross, thighs stacked, legs stay crossed, "
    "morphing face, camera move, zoom, pan"
)


def _lab_py(lab: Path) -> Path:
    return lab / "pipeline" / ".venv" / "bin" / "python"


def _run_lab(lab: Path, args: list[str], timeout: int = 600) -> tuple[int, str]:
    py = _lab_py(lab)
    if not py.is_file():
        return 2, f"Lab venv missing: {py}"
    try:
        p = subprocess.run(
            [str(py), *args],
            cwd=str(lab),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
        return p.returncode, out[-8000:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 1, f"{type(e).__name__}: {e}"


def _newest_video(roots: list[Path]) -> Path | None:
    cands: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for pat in ("*.mp4", "*.webm", "*.mov"):
            cands.extend(root.glob(pat))
            cands.extend(root.rglob(pat))
    cands = [p for p in cands if p.is_file()]
    if not cands:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def _leaderboard_md(exp: Path, n: int = 8) -> str:
    board = exp / "LEADERBOARD.tsv"
    if not board.is_file():
        return "_No leaderboard yet. Gate a run to populate._"
    lines = board.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) < 2:
        return "_Leaderboard empty._"
    hdr = lines[0].split("\t")
    rows = [ln.split("\t") for ln in lines[1:] if ln.strip()]
    rows = rows[-n:]
    # ts seed frames steps ok progress phase note path
    out = ["| seed | progress | phase | ok | path |", "|------|----------|-------|----|------|"]
    for r in reversed(rows):
        def col(name, default=""):
            try:
                return r[hdr.index(name)]
            except Exception:
                return default
        out.append(
            f"| {col('seed')} | **{col('progress')}** | `{col('phase')}` | {col('ok')} | `{col('path')}` |"
        )
    return "\n".join(out)


def _vis_for_tracks(tracks: Path) -> Path | None:
    for cand in (
        tracks.with_suffix(".vis.jpg"),
        tracks.parent / f"{tracks.stem}.vis.jpg",
    ):
        if cand.is_file():
            return _gradio_safe_image(cand)
    return None


def _gradio_safe_path(src: Path | str | None) -> Path | None:
    """Copy any suite file into wangp/ so Gradio + form fields accept it.

    wgp.py launch() hardcodes allowed_paths (CWD=wangp, outputs, …).
    Suite cache under data/cache is rejected → always stage under mask_outputs/.
    """
    if src is None:
        return None
    src = Path(src)
    if not src.is_file():
        return None
    try:
        src_res = src.resolve()
        wgp_res = DEFAULT_WGP_ROOT.resolve()
        if src_res == wgp_res or wgp_res in src_res.parents:
            return src_res
    except Exception:
        pass
    try:
        dst_dir = DEFAULT_WGP_ROOT / "mask_outputs"
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name
        if (
            not dst.is_file()
            or dst.stat().st_mtime < src.stat().st_mtime
            or dst.stat().st_size != src.stat().st_size
        ):
            shutil.copy2(src, dst)
        return dst.resolve()
    except Exception:
        try:
            tmp = Path("/tmp") / f"wangp_lab_{src.name}"
            shutil.copy2(src, tmp)
            return tmp
        except Exception:
            return src


def _gradio_safe_image(src: Path | None) -> Path | None:
    return _gradio_safe_path(src)


class LabBridgePlugin(WAN2GPPlugin):
    def __init__(self):
        super().__init__()
        self.name = PLUGIN_NAME
        self.version = "0.4.0"
        self.description = (
            "Mission cockpit: tracks + preview, L0–L2 presets, gate last output, "
            "leaderboard. Cockpit=WanGP, Motor=Lab."
        )

    def setup_ui(self):
        self.request_global("get_current_model_settings")
        self.request_global("refresh_model_defs")
        self.request_global("switch_to_model")
        self.request_component("refresh_form_trigger")
        self.request_component("state")
        self.request_component("main_tabs")
        self.request_component("model_choice_target")
        self.add_tab(
            tab_id=PLUGIN_ID,
            label=PLUGIN_NAME,
            component_constructor=self.create_ui,
            position=1,
        )

    def create_ui(self, api_session=None):
        lab_default = str(DEFAULT_LAB_ROOT)
        wgp_default = str(DEFAULT_WGP_ROOT)
        suite_default = str(DEFAULT_SUITE_ROOT)
        cache = (
            DEFAULT_SUITE_CACHE
            if DEFAULT_SUITE_CACHE.is_dir()
            else (DEFAULT_SUITE_ROOT / "data" / "cache" / "wanmove")
        )
        still_default = str(cache / "still_675_832x480.jpg")
        tracks_default = str(cache / "tracks_e01_open_hands_t49.npy")
        analysis_default = str(DEFAULT_LAB_ROOT / "_data" / "analysis" / "0009")
        src_still_default = str(
            DEFAULT_LAB_ROOT
            / "_src"
            / "0009_still_day21_10_sophia_dylan_evening_675.jpeg"
        )
        vis0 = _vis_for_tracks(Path(tracks_default))

        with gr.Column() as root:
            gr.Markdown(
                "## Lab Bridge — mission cockpit\n"
                "**WanGP** = gen UI · **Lab** = SAM3D / tracks / pose_gate  \n"
                f"Cache `{cache}` · outputs `{DEFAULT_OUTPUTS}`"
            )

            with gr.Accordion("Mission status", open=True):
                status = gr.Markdown(
                    value=self._status_md(DEFAULT_LAB_ROOT, DEFAULT_WGP_ROOT)
                )
                leaderboard = gr.Markdown(
                    value=_leaderboard_md(DEFAULT_EXPERIMENTS),
                    label="Leaderboard",
                )
                btn_refresh_lb = gr.Button("Refresh leaderboard / status", size="sm")

            with gr.Accordion("Paths", open=False):
                suite_root = gr.Textbox(label="Suite root", value=suite_default)
                lab_root = gr.Textbox(label="Lab motor root", value=lab_default)
                wgp_root = gr.Textbox(label="WanGP root", value=wgp_default)
                analysis_dir = gr.Textbox(label="SAM3D analysis dir", value=analysis_default)
                src_still = gr.Textbox(label="Full-res source still", value=src_still_default)
                out_still = gr.Textbox(label="Target still 832×480", value=still_default)
                out_tracks = gr.Textbox(label="Tracks .npy", value=tracks_default)

            gr.Markdown("### 1 · Tracks")
            with gr.Row():
                frames = gr.Dropdown(choices=[33, 49, 81], value=49, label="Frames")
                apart_dx = gr.Dropdown(
                    choices=[80, 100, 120, 140],
                    value=100,
                    label="apart-dx (px)",
                    info="100=best so far; 140 overshot dy",
                )
                btn_tracks = gr.Button("Build tracks (Lab)", variant="primary")
                btn_paths = gr.Button("Check paths")
            gr.Markdown(
                "Preview = **6 control points** (knees / ankles / wrists), not a full skeleton.  \n"
                "**Cyan = START** (crossed) · **Lime = END** (open target) · grey = path.  \n"
                "Rebuild tracks to refresh the image."
            )
            track_preview = gr.Image(
                label="Track preview (START | END + trails)",
                value=str(vis0) if vis0 else None,
                type="filepath",
                height=360,
            )

            gr.Markdown(
                "### 2 · Ladder presets → main form\n"
                "L0 smoke only · L1 Move 33×8 · L2 Move 49×16 (mission). "
                "Also sets `image_start` + `custom_guide` when files exist."
            )
            with gr.Row():
                steps = gr.Dropdown(
                    choices=[8, 12, 16, 24, 30], value=16, label="Steps (L2 override)"
                )
                seed = gr.Number(value=7, label="Seed", precision=0, info="7 best progress")
            with gr.Row():
                btn_l0 = gr.Button("L0 FastWan smoke")
                btn_l1 = gr.Button("L1 Move smoke 33×8")
                btn_l2 = gr.Button("L2 Move e01 49×16", variant="primary")
            with gr.Row():
                btn_switch_move = gr.Button("Model → lab_wanmove_e01")
                btn_switch_smoke = gr.Button("Model → lab_wanmove_e01_smoke")
                btn_switch_fast = gr.Button("Model → lab_ti2v5b_fast_e01")
                btn_goto = gr.Button("Open Media tab")

            gr.Markdown("### 3 · After Generate — gate")
            video_or_frames = gr.Textbox(
                label="mp4 / frames dir (optional if using Gate last)",
                placeholder="auto: newest under _outputs/ or leave empty",
            )
            with gr.Row():
                btn_gate_last = gr.Button("Gate last UI output", variant="primary")
                btn_gate = gr.Button("Gate path above")
            gate_json_out = gr.Textbox(label="Gate summary", lines=10)
            log = gr.Textbox(label="Log", lines=12, max_lines=28)

        # ----- handlers -----
        def refresh_status(lab_s, wgp_s):
            lab, wgp = Path(lab_s), Path(wgp_s)
            return (
                self._status_md(lab, wgp),
                _leaderboard_md(DEFAULT_EXPERIMENTS),
            )

        def check_paths(suite_s, lab_s, wgp_s):
            suite, lab, wgp = Path(suite_s), Path(lab_s), Path(wgp_s)
            lines = [
                f"Suite: {suite.is_dir()} — {suite}",
                f"Lab py: {_lab_py(lab).is_file()} — {_lab_py(lab)}",
                f"WanGP py: {(wgp / '.venv/bin/python').is_file()}",
                f"tracks script: {_tracks_script(suite, lab)}",
                f"pose_gate: {(lab / 'pipeline/pose_gate.py').is_file()}",
                f"finetune e01: {(wgp / 'finetunes/lab_wanmove_e01.json').is_file()}",
                f"plugin: {(wgp / 'plugins/wan2gp-lab-bridge').is_dir()}",
                f"still: {(DEFAULT_SUITE_CACHE / 'still_675_832x480.jpg').is_file()}",
                f"tracks49: {(DEFAULT_SUITE_CACHE / 'tracks_e01_open_hands_t49.npy').is_file()}",
                f"_outputs: {DEFAULT_OUTPUTS.is_dir()} link={os.path.islink(wgp / 'outputs')}",
            ]
            newest = _newest_video([DEFAULT_OUTPUTS, wgp / "outputs"])
            lines.append(f"newest video: {newest}")
            return "\n".join(lines), *refresh_status(lab_s, wgp_s)

        def build_tracks(
            suite_s, lab_s, analysis_s, src_s, out_still_s, out_tracks_s, nframes, apart
        ):
            suite, lab = Path(suite_s), Path(lab_s)
            nframes = int(nframes)
            apart = float(apart)
            still_p = Path(out_still_s)
            src_p = Path(src_s)
            if not still_p.is_file() and src_p.is_file():
                code, out = _run_lab(
                    lab,
                    [
                        "-c",
                        f"""
from PIL import Image
from pathlib import Path
src=Path({str(src_p)!r}); dst=Path({str(still_p)!r})
dst.parent.mkdir(parents=True, exist_ok=True)
im=Image.open(src).convert('RGB')
tw,th=832,480
sw,sh=im.size
scale=max(tw/sw, th/sh)
nw,nh=int(sw*scale),int(sh*scale)
im2=im.resize((nw,nh), Image.BICUBIC)
left,top=(nw-tw)//2,(nh-th)//2
im2.crop((left,top,left+tw,top+th)).save(dst, quality=95)
print('wrote', dst)
""",
                    ],
                    timeout=120,
                )
                if code != 0:
                    return f"still resize failed:\n{out}", gr.update(), gr.update()

            tracks_script = _tracks_script(suite, lab)
            if not tracks_script.is_file():
                return f"tracks script missing: {tracks_script}", gr.update(), gr.update()

            out_t = Path(out_tracks_s)
            if f"t{nframes}" not in out_t.name:
                out_t = out_t.parent / f"tracks_e01_open_hands_t{nframes}.npy"
            out_t.parent.mkdir(parents=True, exist_ok=True)

            # keep variant copy when apart != 100
            code, out = _run_lab(
                lab,
                [
                    str(tracks_script),
                    "--analysis",
                    analysis_s,
                    "--src-still",
                    src_s,
                    "--still",
                    str(still_p),
                    "--out",
                    str(out_t),
                    "--frames",
                    str(nframes),
                    "--width",
                    "832",
                    "--height",
                    "480",
                    "--apart-dx",
                    str(apart),
                    "--vis",
                ],
                timeout=300,
            )
            if out_t.is_file() and apart != 100:
                variant = out_t.parent / f"{out_t.stem}_apart{int(apart)}.npy"
                shutil.copy2(out_t, variant)
                out += f"\nvariant {variant}"

            wgp_mask = DEFAULT_WGP_ROOT / "mask_outputs"
            try:
                wgp_mask.mkdir(parents=True, exist_ok=True)
                if out_t.is_file():
                    shutil.copy2(out_t, wgp_mask / out_t.name)
                if still_p.is_file():
                    shutil.copy2(still_p, wgp_mask / still_p.name)
            except Exception as e:
                out += f"\ncopy mask_outputs: {e}"

            vis = _vis_for_tracks(out_t)
            return (
                f"exit={code}\ntracks={out_t}\napart-dx={apart}\n{out}",
                str(out_t),
                str(vis) if vis else None,
            )

        def _apply_move(state, nframes, nsteps, seed_v, still_s, tracks_s, tag: str):
            settings = self.get_current_model_settings(state)
            settings["prompt"] = PROMPT_E01
            settings["negative_prompt"] = NEG_E01
            settings["resolution"] = "832x480"
            settings["video_length"] = int(nframes)
            settings["num_inference_steps"] = int(nsteps)
            settings["guidance_scale"] = 4.0
            settings["seed"] = int(seed_v)
            settings["force_fps"] = "24"
            settings["flow_shift"] = 7.0
            settings["sample_solver"] = "unipc"
            settings["image_prompt_type"] = "S"
            settings["prompt_enhancer"] = ""
            settings["output_filename"] = tag
            still_p = Path(still_s) if still_s else DEFAULT_SUITE_CACHE / "still_675_832x480.jpg"
            tracks_p = (
                Path(tracks_s)
                if tracks_s
                else DEFAULT_SUITE_CACHE / f"tracks_e01_open_hands_t{int(nframes)}.npy"
            )
            if not tracks_p.is_file():
                alt = DEFAULT_SUITE_CACHE / f"tracks_e01_open_hands_t{int(nframes)}.npy"
                if alt.is_file():
                    tracks_p = alt
            still_ok = _gradio_safe_path(still_p if still_p.is_file() else None)
            tracks_ok = _gradio_safe_path(tracks_p if tracks_p.is_file() else None)
            if still_ok is not None:
                settings["image_start"] = str(still_ok)
            if tracks_ok is not None:
                settings["custom_guide"] = str(tracks_ok)
            msg = (
                f"{tag} preset → form\n"
                f"frames={nframes} steps={nsteps} seed={seed_v}\n"
                f"image_start={settings.get('image_start')}\n"
                f"custom_guide={settings.get('custom_guide')}\n"
                "→ Media tab → Generate"
            )
            return time.time(), msg

        def apply_l2(state, nsteps, seed_v, still_s, tracks_s):
            return _apply_move(state, 49, int(nsteps), seed_v, still_s, tracks_s, "lab_wanmove_e01")

        def apply_l1(state, seed_v, still_s, tracks_s):
            t = DEFAULT_SUITE_CACHE / "tracks_e01_open_hands_t33.npy"
            return _apply_move(
                state, 33, 8, seed_v, still_s, str(t) if t.is_file() else tracks_s, "lab_wanmove_e01_smoke"
            )

        def apply_l0(state, seed_v, still_s):
            settings = self.get_current_model_settings(state)
            settings["prompt"] = PROMPT_E01
            settings["negative_prompt"] = NEG_E01
            settings["resolution"] = "640x352"
            settings["video_length"] = 33
            settings["num_inference_steps"] = 4
            settings["guidance_scale"] = 3.5
            settings["seed"] = int(seed_v)
            settings["force_fps"] = "24"
            settings["flow_shift"] = 3
            settings["sample_solver"] = "unipc"
            settings["image_prompt_type"] = "S"
            settings["prompt_enhancer"] = ""
            settings["repeat_generation"] = 3
            settings["custom_guide"] = None
            settings["output_filename"] = "lab_ti2v5b_fast_e01"
            still_p = Path(still_s) if still_s else DEFAULT_SUITE_CACHE / "still_675_640x352.jpg"
            if not still_p.is_file():
                still_p = DEFAULT_SUITE_CACHE / "still_675_640x352.jpg"
            still_ok = _gradio_safe_path(still_p if still_p.is_file() else None)
            if still_ok is not None:
                settings["image_start"] = str(still_ok)
            return (
                time.time(),
                "L0 FastWan smoke (no tracks). Not a pose pass.\n"
                f"image_start={settings.get('image_start')}",
            )

        def run_gate(lab_s, path_s):
            lab = Path(lab_s)
            path = Path(path_s.strip()) if path_s and path_s.strip() else None
            if path is None or not path.exists():
                return "Need existing mp4 or frames dir", ""
            return _gate_path(lab, path)

        def gate_last(lab_s, path_s):
            lab = Path(lab_s)
            path = Path(path_s.strip()) if path_s and path_s.strip() else None
            if path is None or not path.exists():
                path = _newest_video(
                    [
                        DEFAULT_OUTPUTS,
                        DEFAULT_WGP_ROOT / "outputs",
                        DEFAULT_EXPERIMENTS,
                    ]
                )
            if path is None:
                return "No video found under _outputs/ or experiments/", ""
            msg, summary = _gate_path(lab, path)
            return f"gated: {path}\n{msg}", summary

        def _gate_path(lab: Path, path: Path) -> tuple[str, str]:
            frames_dir = path
            gate_cache = DEFAULT_SUITE_CACHE
            gate_cache.mkdir(parents=True, exist_ok=True)
            tmp = None
            if path.is_file() and path.suffix.lower() in (".mp4", ".webm", ".mov"):
                tmp = DEFAULT_EXPERIMENTS / f"_gate_frames_{datetime.now().strftime('%H%M%S')}"
                tmp.mkdir(parents=True, exist_ok=True)
                code, out = _run_lab(
                    lab,
                    [
                        "-c",
                        f"""
from pathlib import Path
import imageio.v3 as iio
from PIL import Image
vid=Path({str(path)!r}); out=Path({str(tmp)!r})
frames=iio.imread(vid)
for i,f in enumerate(frames):
    Image.fromarray(f).save(out/f'{{i:04d}}.jpg', quality=92)
print('frames', len(list(out.glob('*.jpg'))))
""",
                    ],
                    timeout=180,
                )
                if code != 0:
                    return f"frame extract failed:\n{out}", ""
                frames_dir = tmp
            elif not path.is_dir():
                return "path must be mp4 or directory", ""

            gate_out = DEFAULT_EXPERIMENTS / "last_pose_gate_open_end.json"
            # also suite cache rolling for back-compat
            gate_out_cache = gate_cache / "last_pose_gate_open_end.json"
            code, out = _run_lab(
                lab,
                [
                    str(lab / "pipeline" / "pose_gate.py"),
                    "hop",
                    "--frames",
                    str(frames_dir),
                    "--mode",
                    "open_end",
                    "--json-out",
                    str(gate_out),
                ],
                timeout=600,
            )
            if gate_out.is_file():
                try:
                    shutil.copy2(gate_out, gate_out_cache)
                except Exception:
                    pass
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)

            summary = ""
            if gate_out.is_file():
                try:
                    d = json.loads(gate_out.read_text())
                    summary = json.dumps(
                        {
                            "ok": d.get("ok"),
                            "pose_pass": d.get("pose_pass"),
                            "progress": d.get("progress"),
                            "phase": d.get("phase"),
                            "note": d.get("note"),
                            "late_open": d.get("late_open"),
                            "early_open": d.get("early_open"),
                        },
                        indent=2,
                    )
                    # append leaderboard if missing path context
                    board = DEFAULT_EXPERIMENTS / "LEADERBOARD.tsv"
                    if not board.is_file():
                        board.write_text(
                            "ts\tseed\tframes\tsteps\tok\tprogress\tphase\tnote\tpath\n",
                            encoding="utf-8",
                        )
                    with board.open("a", encoding="utf-8") as f:
                        f.write(
                            "\t".join(
                                [
                                    datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                                    "ui",
                                    "?",
                                    "?",
                                    str(bool(d.get("ok"))),
                                    f"{float(d.get('progress') or 0):.4f}",
                                    str(d.get("phase") or ""),
                                    str(d.get("note") or "").replace("\t", " "),
                                    path.name,
                                ]
                            )
                            + "\n"
                        )
                except Exception as e:
                    summary = str(e)
            return f"exit={code} (0=pass, 3=fail open)\n{out}", summary

        btn_refresh_lb.click(
            fn=refresh_status,
            inputs=[lab_root, wgp_root],
            outputs=[status, leaderboard],
        )
        btn_paths.click(
            fn=check_paths,
            inputs=[suite_root, lab_root, wgp_root],
            outputs=[log, status, leaderboard],
        )
        btn_tracks.click(
            fn=build_tracks,
            inputs=[
                suite_root,
                lab_root,
                analysis_dir,
                src_still,
                out_still,
                out_tracks,
                frames,
                apart_dx,
            ],
            outputs=[log, out_tracks, track_preview],
        )
        btn_l2.click(
            fn=apply_l2,
            inputs=[self.state, steps, seed, out_still, out_tracks],
            outputs=[self.refresh_form_trigger, log],
        )
        btn_l1.click(
            fn=apply_l1,
            inputs=[self.state, seed, out_still, out_tracks],
            outputs=[self.refresh_form_trigger, log],
        )
        btn_l0.click(
            fn=apply_l0,
            inputs=[self.state, seed, out_still],
            outputs=[self.refresh_form_trigger, log],
        )
        btn_goto.click(
            fn=self.goto_media_tab,
            inputs=[self.state],
            outputs=[self.main_tabs],
        )
        btn_switch_move.click(
            fn=lambda: self.switch_to_model("lab_wanmove_e01", True),
            outputs=[self.model_choice_target, self.main_tabs],
            show_progress="hidden",
        )
        btn_switch_smoke.click(
            fn=lambda: self.switch_to_model("lab_wanmove_e01_smoke", True),
            outputs=[self.model_choice_target, self.main_tabs],
            show_progress="hidden",
        )
        btn_switch_fast.click(
            fn=lambda: self.switch_to_model("lab_ti2v5b_fast_e01", True),
            outputs=[self.model_choice_target, self.main_tabs],
            show_progress="hidden",
        )
        btn_gate.click(
            fn=run_gate,
            inputs=[lab_root, video_or_frames],
            outputs=[log, gate_json_out],
        )
        btn_gate_last.click(
            fn=gate_last,
            inputs=[lab_root, video_or_frames],
            outputs=[log, gate_json_out],
        )
        return root

    @staticmethod
    def _status_md(lab: Path, wgp: Path) -> str:
        ok_lab = _lab_py(lab).is_file()
        ok_ft = (wgp / "finetunes" / "lab_wanmove_e01.json").is_file()
        still = DEFAULT_SUITE_CACHE / "still_675_832x480.jpg"
        tracks = DEFAULT_SUITE_CACHE / "tracks_e01_open_hands_t49.npy"
        newest = _newest_video([DEFAULT_OUTPUTS, wgp / "outputs"])
        return (
            f"**Status:** Lab venv `{'OK' if ok_lab else 'MISSING'}` · "
            f"finetune `{'OK' if ok_ft else 'install_bridge'}` · "
            f"still `{'OK' if still.is_file() else 'MISS'}` · "
            f"tracks49 `{'OK' if tracks.is_file() else 'MISS'}` · "
            f"profile **4** · sage · int8  \n"
            f"newest out: `{newest.name if newest else '—'}`  \n"
            f"ladder: **L0** FastWan → **L1** Move 33×8 → **L2** Move 49×16 + gate → "
            f"**L3** multi-seed → **L4** motor e12 only if open_end PASS"
        )
