"""Lab Bridge — WanGP plugin (Cockpit ↔ Motor).

Lab tools run in pipeline/.venv only. Never import heavy Lab/torch into WanGP.
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

# Track builder: suite SoT, fallback motor lab/tools copy
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


class LabBridgePlugin(WAN2GPPlugin):
    def __init__(self):
        super().__init__()
        self.name = PLUGIN_NAME
        self.version = "0.3.0"
        self.description = (
            "Lab motor bridge: Move tracks (SAM3D/MHR70), mission presets, pose_gate. "
            "Cockpit=WanGP, Motor=Lab."
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

        with gr.Column() as root:
            gr.Markdown(
                "## Lab Bridge\n"
                "**WanGP** = Cockpit · **Lab** = Motor (SAM3D / tracks / pose_gate)\n\n"
                "Lab tools run in `pipeline/.venv` only. "
                f"Suite cache: `{cache}`"
            )
            with gr.Accordion("Paths", open=False):
                suite_root = gr.Textbox(label="Suite root (WanGP-Lab)", value=suite_default)
                lab_root = gr.Textbox(label="Lab motor root", value=lab_default)
                wgp_root = gr.Textbox(label="WanGP root", value=wgp_default)
                analysis_dir = gr.Textbox(
                    label="SAM3D analysis dir (sam3d_body.npz)",
                    value=analysis_default,
                )
                src_still = gr.Textbox(
                    label="Full-res source still (cover-crop coords)",
                    value=src_still_default,
                )
                out_still = gr.Textbox(label="Target still 832×480", value=still_default)
                out_tracks = gr.Textbox(label="Tracks .npy out", value=tracks_default)

            with gr.Row():
                frames = gr.Dropdown(choices=[33, 49, 81], value=49, label="Frames")
                steps = gr.Dropdown(
                    choices=[8, 12, 16, 24, 30], value=16, label="Steps (preset)"
                )
                seed = gr.Number(value=33, label="Seed", precision=0)

            with gr.Row():
                btn_paths = gr.Button("Check paths")
                btn_tracks = gr.Button("1 · Build tracks (Lab)", variant="primary")
                btn_preset_move = gr.Button("2 · Apply Move e01 preset")
                btn_preset_fast = gr.Button("2b · FastWan smoke preset")

            with gr.Row():
                btn_goto = gr.Button("3 · Open Media tab")
                btn_switch_move = gr.Button("Model → lab_wanmove_e01")
                btn_switch_fast = gr.Button("Model → lab_ti2v5b_fast_e01")

            gr.Markdown("### After Generate — paste mp4 or frames dir, then gate.")
            video_or_frames = gr.Textbox(
                label="Output mp4 or frames directory",
                placeholder="/path/to/out.mp4 or .../frames",
            )
            btn_gate = gr.Button("4 · pose_gate open_end (Lab)", variant="primary")
            log = gr.Textbox(label="Log", lines=16, max_lines=30)
            gate_json_out = gr.Textbox(label="Last gate JSON (summary)", lines=8)
            status = gr.Markdown(
                value=self._status_md(DEFAULT_LAB_ROOT, DEFAULT_WGP_ROOT)
            )

        def check_paths(suite_s, lab_s, wgp_s):
            suite = Path(suite_s)
            lab = Path(lab_s)
            wgp = Path(wgp_s)
            lines = [
                f"Suite root: {suite.is_dir()} — {suite}",
                f"Lab root: {lab.is_dir()} — {lab}",
                f"Lab python: {_lab_py(lab).is_file()} — {_lab_py(lab)}",
                f"WanGP root: {wgp.is_dir()} — {wgp}",
                f"WanGP python: {(wgp / '.venv/bin/python').is_file()}",
            ]
            ts = _tracks_script(suite, lab)
            lines.append(f"tracks script: {ts.is_file()} — {ts}")
            lines.append(
                f"pose_gate: {(lab / 'pipeline/pose_gate.py').is_file()}"
            )
            lines.append(
                f"finetune lab_wanmove_e01: {(wgp / 'finetunes/lab_wanmove_e01.json').is_file()}"
            )
            lines.append(
                f"plugin dir: {(wgp / 'plugins/wan2gp-lab-bridge').is_dir()}"
            )
            lines.append(f"suite cache: {DEFAULT_SUITE_CACHE.is_dir()} — {DEFAULT_SUITE_CACHE}")
            return "\n".join(lines), self._status_md(lab, wgp)

        def build_tracks(
            suite_s, lab_s, analysis_s, src_s, out_still_s, out_tracks_s, nframes
        ):
            suite = Path(suite_s)
            lab = Path(lab_s)
            nframes = int(nframes)
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
                    return f"still resize failed:\n{out}", gr.update()

            tracks_script = _tracks_script(suite, lab)
            if not tracks_script.is_file():
                return f"tracks script missing: {tracks_script}", gr.update()

            out_t = Path(out_tracks_s)
            if f"t{nframes}" not in out_t.name:
                out_t = out_t.parent / f"tracks_e01_open_hands_t{nframes}.npy"
            out_t.parent.mkdir(parents=True, exist_ok=True)

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
                    "100",
                    "--vis",
                ],
                timeout=300,
            )
            wgp_mask = DEFAULT_WGP_ROOT / "mask_outputs"
            try:
                wgp_mask.mkdir(parents=True, exist_ok=True)
                if out_t.is_file():
                    shutil.copy2(out_t, wgp_mask / out_t.name)
                if still_p.is_file():
                    shutil.copy2(still_p, wgp_mask / still_p.name)
            except Exception as e:
                out += f"\ncopy mask_outputs: {e}"
            return f"exit={code}\ntracks={out_t}\n{out}", str(out_t)

        def apply_move_preset(state, nframes, nsteps, seed_v):
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
            settings["output_filename"] = "lab_wanmove_e01"
            tpath = DEFAULT_SUITE_CACHE / f"tracks_e01_open_hands_t{int(nframes)}.npy"
            if tpath.is_file():
                settings["custom_guide"] = str(tpath)
            return (
                time.time(),
                f"Move preset applied.\ncustom_guide={settings.get('custom_guide')}\n"
                "→ set Start image + Generate on Media tab.",
            )

        def apply_fast_preset(state, seed_v):
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
            return (
                time.time(),
                "FastWan smoke preset (no tracks). Smoke only — not pose pass.",
            )

        def run_gate(lab_s, path_s):
            lab = Path(lab_s)
            path = Path(path_s.strip()) if path_s else None
            if not path or not path.exists():
                return "Need existing mp4 or frames dir", ""
            frames_dir = path
            gate_cache = DEFAULT_SUITE_CACHE
            gate_cache.mkdir(parents=True, exist_ok=True)
            if path.is_file() and path.suffix.lower() in (".mp4", ".webm", ".mov"):
                tmp = gate_cache / f"_gate_frames_{datetime.now().strftime('%H%M%S')}"
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

            gate_out = gate_cache / "last_pose_gate_open_end.json"
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
                except Exception as e:
                    summary = str(e)
            return f"exit={code} (0=pass, 3=fail open)\n{out}", summary

        btn_paths.click(
            fn=check_paths,
            inputs=[suite_root, lab_root, wgp_root],
            outputs=[log, status],
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
            ],
            outputs=[log, out_tracks],
        )
        btn_preset_move.click(
            fn=apply_move_preset,
            inputs=[self.state, frames, steps, seed],
            outputs=[self.refresh_form_trigger, log],
        )
        btn_preset_fast.click(
            fn=apply_fast_preset,
            inputs=[self.state, seed],
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
        return root

    @staticmethod
    def _status_md(lab: Path, wgp: Path) -> str:
        ok_lab = _lab_py(lab).is_file()
        ok_ft = (wgp / "finetunes" / "lab_wanmove_e01.json").is_file()
        return (
            f"**Status:** Lab venv `{'OK' if ok_lab else 'MISSING'}` · "
            f"finetune `{'OK' if ok_ft else 'run install_bridge.sh'}` · "
            f"profile **4** · sage · int8"
        )
