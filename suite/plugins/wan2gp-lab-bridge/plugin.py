"""Lab Bridge — generic mission cockpit (WanGP ↔ Lab motor).

Missions live in suite/missions/<id>/mission.json (e01 is one pack, not the only).
Lab tools run in pipeline/.venv only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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
DEFAULT_OUTPUTS = Path(
    os.environ.get("WANGP_LAB_OUTPUTS", str(DEFAULT_SUITE_ROOT / "_outputs"))
)
DEFAULT_EXPERIMENTS = Path(
    os.environ.get(
        "WANGP_LAB_EXPERIMENTS",
        str(DEFAULT_SUITE_ROOT / "data" / "experiments"),
    )
)

# suite tools on path for mission_lib
_TOOLS = DEFAULT_SUITE_ROOT / "suite" / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

try:
    import mission_lib as M
except Exception:  # pragma: no cover
    M = None  # type: ignore


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


def _stage(src: Path | None) -> Path | None:
    if M is not None:
        return M.stage_into_wangp(src, DEFAULT_WGP_ROOT)
    if src is None or not Path(src).is_file():
        return None
    dst = DEFAULT_WGP_ROOT / "mask_outputs" / Path(src).name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst.resolve()


def _vis_path(tracks: Path) -> Path | None:
    for cand in (tracks.with_suffix(".vis.jpg"), tracks.parent / f"{tracks.stem}.vis.jpg"):
        if cand.is_file():
            return _stage(cand)
    return None


def _mission_choices() -> list[str]:
    if M is None:
        return ["e01_uncross_open"]
    ids = [m.get("id") for m in M.list_missions() if m.get("id")]
    return ids or ["e01_uncross_open"]


def _load_m(mid: str) -> dict:
    if M is None:
        raise RuntimeError("mission_lib unavailable")
    return M.load_mission(mid)


class LabBridgePlugin(WAN2GPPlugin):
    def __init__(self):
        super().__init__()
        self.name = PLUGIN_NAME
        self.version = "0.5.0"
        self.description = (
            "Generic mission cockpit: pick hard-case recipe, build tracks, "
            "L0–L2 ladder, gate last output, run cards + next-action hints."
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
        choices = _mission_choices()
        default_id = (
            M.default_mission_id() if M is not None else choices[0]
        )
        if default_id not in choices:
            default_id = choices[0]

        try:
            m0 = _load_m(default_id)
        except Exception:
            m0 = {"id": default_id, "title": default_id, "assets": {}, "ladder": {}}

        still0 = M.mission_still(m0) if M else Path()
        tracks0 = M.mission_tracks(m0, 49) if M else Path()
        _stage(still0 if still0.is_file() else None)
        _stage(tracks0 if tracks0.is_file() else None)
        vis0 = _vis_path(tracks0) if tracks0.is_file() else None

        tb = m0.get("track_build") or {}
        analysis0 = str(tb.get("analysis") or "")
        src_still0 = str(tb.get("src_still") or "")
        apart0 = float(tb.get("apart_dx_default") or 100)

        with gr.Column() as root:
            gr.Markdown(
                "## Lab Bridge — mission cockpit\n"
                "Generic hard-case recipes (`suite/missions/`). "
                "e01 is one pack — add others without forking the plugin.\n\n"
                f"Outputs `{DEFAULT_OUTPUTS}` · experiments `{DEFAULT_EXPERIMENTS}`"
            )

            with gr.Accordion("Mission", open=True):
                mission_dd = gr.Dropdown(
                    choices=choices,
                    value=default_id,
                    label="Active mission",
                    info="Recipe JSON under suite/missions/<id>/",
                )
                mission_info = gr.Markdown(value=self._mission_md(m0))
                leaderboard = gr.Markdown(
                    value=M.leaderboard_md(DEFAULT_EXPERIMENTS) if M else "_no mission_lib_"
                )
                status = gr.Markdown(value=self._status_md(DEFAULT_LAB_ROOT, DEFAULT_WGP_ROOT, m0))
                btn_refresh = gr.Button("Refresh status / leaderboard", size="sm")

            with gr.Accordion("Paths (advanced)", open=False):
                suite_root = gr.Textbox(label="Suite root", value=str(DEFAULT_SUITE_ROOT))
                lab_root = gr.Textbox(label="Lab motor root", value=str(DEFAULT_LAB_ROOT))
                wgp_root = gr.Textbox(label="WanGP root", value=str(DEFAULT_WGP_ROOT))
                analysis_dir = gr.Textbox(label="SAM3D analysis dir", value=analysis0)
                src_still = gr.Textbox(label="Full-res source still", value=src_still0)
                out_still = gr.Textbox(
                    label="Still (staged path preferred)",
                    value=str(_stage(still0) or still0),
                )
                out_tracks = gr.Textbox(
                    label="Tracks .npy",
                    value=str(_stage(tracks0) or tracks0),
                )

            gr.Markdown("### 1 · Tracks (optional rebuild)")
            with gr.Row():
                frames = gr.Dropdown(choices=[33, 49, 81], value=49, label="Frames")
                apart_dx = gr.Dropdown(
                    choices=[80, 100, 120, 140],
                    value=int(apart0) if int(apart0) in (80, 100, 120, 140) else 100,
                    label="apart-dx (px)",
                )
                btn_tracks = gr.Button("Build tracks (Lab)", variant="primary")
                btn_paths = gr.Button("Check paths")
            gr.Markdown(
                "Preview = **control points** for the guide (not a full skeleton). "
                "**Cyan=START · Lime=END**."
            )
            track_preview = gr.Image(
                label="Track preview",
                value=str(vis0) if vis0 else None,
                type="filepath",
                height=360,
            )

            gr.Markdown(
                "### 2 · Ladder → Media Generator form\n"
                "Applies mission recipe (prompt, seed, still list, custom_guide). "
                "If gallery stays empty, drop staged files from `wangp/mask_outputs/`."
            )
            with gr.Row():
                steps = gr.Dropdown(
                    choices=[4, 8, 12, 16, 24, 30], value=16, label="Steps override (L2)"
                )
                seed = gr.Number(value=7, label="Seed override", precision=0)
            with gr.Row():
                btn_l0 = gr.Button("L0 smoke")
                btn_l1 = gr.Button("L1 Move smoke")
                btn_l2 = gr.Button("L2 mission", variant="primary")
            with gr.Row():
                btn_switch_model = gr.Button("Switch to ladder model")
                btn_goto = gr.Button("Open Media Generator")

            gr.Markdown("### 3 · Gate last generation")
            video_or_frames = gr.Textbox(
                label="mp4 / frames (optional)",
                placeholder="empty → newest under _outputs/",
            )
            with gr.Row():
                btn_gate_last = gr.Button("Gate last UI output", variant="primary")
                btn_gate = gr.Button("Gate path above")
            gate_json_out = gr.Textbox(label="Gate + next action", lines=12)
            log = gr.Textbox(label="Log", lines=10, max_lines=24)

        # ----- handlers -----
        def on_mission_change(mid: str):
            try:
                m = _load_m(mid)
            except Exception as e:
                return (
                    f"**Error loading mission:** {e}",
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    str(e),
                )
            still = M.mission_still(m)
            tr = M.mission_tracks(m, 49)
            s_st = _stage(still if still.is_file() else None)
            s_tr = _stage(tr if tr.is_file() else None)
            vis = _vis_path(Path(s_tr or tr)) if (s_tr or tr.is_file()) else None
            tb = m.get("track_build") or {}
            l2 = (m.get("ladder") or {}).get("L2") or {}
            return (
                self._mission_md(m),
                self._status_md(DEFAULT_LAB_ROOT, DEFAULT_WGP_ROOT, m),
                M.leaderboard_md(DEFAULT_EXPERIMENTS),
                str(tb.get("analysis") or ""),
                str(tb.get("src_still") or ""),
                str(s_st or still),
                str(s_tr or tr),
                str(vis) if vis else None,
                int(l2.get("seed", 33)),
                int(l2.get("steps", 16)),
            )

        def refresh(mid, lab_s, wgp_s):
            try:
                m = _load_m(mid)
            except Exception:
                m = {"id": mid}
            return (
                self._status_md(Path(lab_s), Path(wgp_s), m),
                M.leaderboard_md(DEFAULT_EXPERIMENTS) if M else "",
                self._mission_md(m),
            )

        def check_paths(mid, suite_s, lab_s, wgp_s):
            lab, wgp = Path(lab_s), Path(wgp_s)
            try:
                m = _load_m(mid)
            except Exception as e:
                return str(e), *refresh(mid, lab_s, wgp_s)
            still = M.mission_still(m)
            tr = M.mission_tracks(m, 49)
            lines = [
                f"mission: {m.get('id')} — {m.get('title')}",
                f"Lab py: {_lab_py(lab).is_file()}",
                f"WanGP py: {(wgp / '.venv/bin/python').is_file()}",
                f"still: {still.is_file()} — {still}",
                f"tracks49: {tr.is_file()} — {tr}",
                f"staged still: {_stage(still if still.is_file() else None)}",
                f"staged tracks: {_stage(tr if tr.is_file() else None)}",
                f"gate mode: {(m.get('gate') or {}).get('mode')}",
                f"newest video: {_newest_video([DEFAULT_OUTPUTS, wgp / 'outputs'])}",
            ]
            return "\n".join(lines), *refresh(mid, lab_s, wgp_s)

        def build_tracks(mid, suite_s, lab_s, analysis_s, src_s, out_still_s, nframes, apart):
            lab = Path(lab_s)
            suite = Path(suite_s)
            try:
                m = _load_m(mid)
            except Exception as e:
                return str(e), gr.update(), gr.update()
            nframes = int(nframes)
            apart = float(apart)
            tb = m.get("track_build") or {}
            if not tb.get("enabled", True):
                return "track_build disabled for this mission", gr.update(), gr.update()

            still_p = Path(out_still_s) if out_still_s else M.mission_still(m)
            # if staged path under mask_outputs, prefer mission still for rebuild source
            ms = M.mission_still(m)
            if ms.is_file():
                still_p = ms
            src_p = Path(src_s or tb.get("src_still") or "")
            analysis = analysis_s or tb.get("analysis") or ""
            if not still_p.is_file() and src_p.is_file():
                still_p.parent.mkdir(parents=True, exist_ok=True)
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
tw,th=int({int(tb.get('width') or 832)}),int({int(tb.get('height') or 480)})
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

            script = suite / (tb.get("script") or "suite/tools/mhr70_to_wanmove_tracks.py")
            if not script.is_file():
                script = suite / "suite/tools/mhr70_to_wanmove_tracks.py"
            if not script.is_file():
                return f"tracks script missing: {script}", gr.update(), gr.update()

            pat = tb.get("out_pattern") or "tracks_t{frames}.npy"
            out_name = pat.format(frames=nframes)
            cache_dir = Path(m.get("assets", {}).get("cache_dir") or still_p.parent)
            if not cache_dir.is_absolute():
                cache_dir = DEFAULT_SUITE_ROOT / cache_dir
            out_t = cache_dir / out_name
            out_t.parent.mkdir(parents=True, exist_ok=True)

            code, out = _run_lab(
                lab,
                [
                    str(script),
                    "--analysis",
                    str(analysis),
                    "--src-still",
                    str(src_p),
                    "--still",
                    str(still_p),
                    "--out",
                    str(out_t),
                    "--frames",
                    str(nframes),
                    "--width",
                    str(int(tb.get("width") or 832)),
                    "--height",
                    str(int(tb.get("height") or 480)),
                    "--apart-dx",
                    str(apart),
                    "--vis",
                ],
                timeout=300,
            )
            staged_t = _stage(out_t if out_t.is_file() else None)
            staged_s = _stage(still_p if still_p.is_file() else None)
            for extra in (
                out_t.with_suffix(".vis.jpg"),
                out_t.with_name(out_t.stem + ".vis.jpg"),
            ):
                if extra.is_file():
                    _stage(extra)
            vis = _vis_path(out_t)
            return (
                f"exit={code}\ntracks={out_t}\nstaged={staged_t}\napart={apart}\n{out}",
                str(staged_t or out_t),
                str(vis) if vis else None,
            )

        def apply_level(state, mid, level, seed_v, steps_v):
            try:
                m = _load_m(mid)
            except Exception as e:
                return time.time(), f"mission error: {e}"
            settings = self.get_current_model_settings(state)
            seed_o = int(seed_v) if seed_v is not None else None
            steps_o = int(steps_v) if (level == "L2" and steps_v is not None) else None
            M.apply_ladder_to_settings(
                settings,
                m,
                level,
                seed_override=seed_o,
                steps_override=steps_o,
                wgp=DEFAULT_WGP_ROOT,
            )
            # ensure list form for gallery (Motion Designer convention)
            is_ = settings.get("image_start")
            if isinstance(is_, str):
                settings["image_start"] = [is_]
            msg = (
                f"{m.get('id')} · {level} → form\n"
                f"model={(m.get('ladder') or {}).get(level, {}).get('model')}\n"
                f"frames={settings.get('video_length')} steps={settings.get('num_inference_steps')} "
                f"seed={settings.get('seed')}\n"
                f"image_start={settings.get('image_start')}\n"
                f"custom_guide={settings.get('custom_guide')}\n"
                "→ Media Generator · Generate\n"
                "(If Start image empty: drop file from wangp/mask_outputs/)"
            )
            return time.time(), msg

        def switch_model(mid, level):
            try:
                m = _load_m(mid)
                model = (m.get("ladder") or {}).get(level, {}).get("model") or "lab_wanmove_e01"
            except Exception:
                model = "lab_wanmove_e01"
            return self.switch_to_model(model, True)

        def run_gate(lab_s, mid, path_s, level_hint="L2"):
            lab = Path(lab_s)
            try:
                m = _load_m(mid)
            except Exception as e:
                return str(e), ""
            path = Path(path_s.strip()) if path_s and str(path_s).strip() else None
            if path is None or not path.exists():
                return "Need existing mp4 or frames dir", ""
            return _gate(lab, m, path, level_hint)

        def gate_last(lab_s, mid, path_s):
            lab = Path(lab_s)
            try:
                m = _load_m(mid)
            except Exception as e:
                return str(e), ""
            path = Path(path_s.strip()) if path_s and str(path_s).strip() else None
            if path is None or not path.exists():
                path = _newest_video(
                    [DEFAULT_OUTPUTS, DEFAULT_WGP_ROOT / "outputs", DEFAULT_EXPERIMENTS]
                )
            if path is None:
                return "No video under _outputs/ or experiments/", ""
            msg, summary = _gate(lab, m, path, "L2")
            return f"gated: {path}\n{msg}", summary

        def _gate(lab: Path, m: dict, path: Path, level: str) -> tuple[str, str]:
            gate_mode = (m.get("gate") or {}).get("mode") or "open_end"
            frames_dir = path
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

            gate_out = DEFAULT_EXPERIMENTS / "last_pose_gate.json"
            code, out = _run_lab(
                lab,
                [
                    str(lab / "pipeline" / "pose_gate.py"),
                    "hop",
                    "--frames",
                    str(frames_dir),
                    "--mode",
                    str(gate_mode),
                    "--json-out",
                    str(gate_out),
                ],
                timeout=600,
            )
            # back-compat name
            try:
                shutil.copy2(gate_out, DEFAULT_EXPERIMENTS / "last_pose_gate_open_end.json")
            except Exception:
                pass
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)

            summary = ""
            gate_d: dict = {}
            if gate_out.is_file():
                try:
                    gate_d = json.loads(gate_out.read_text())
                    summary = M.format_gate_summary(gate_d)
                except Exception as e:
                    summary = str(e)

            # run card next to video if under experiments, else rolling card dir
            card_dir = DEFAULT_EXPERIMENTS / f"ui_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            card_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(path, card_dir / path.name)
            except Exception:
                pass
            if gate_out.is_file():
                shutil.copy2(gate_out, card_dir / "pose_gate.json")
            settings_snap = {
                "seed": "ui",
                "video_length": "?",
                "num_inference_steps": "?",
                "image_start": None,
                "custom_guide": None,
                "output_filename": m.get("output_filename"),
            }
            M.write_run_card(
                card_dir,
                mission_id=str(m.get("id")),
                level=level,
                settings=settings_snap,
                gate=gate_d,
                video=path,
            )
            return f"exit={code} (0=pass, 3=fail typical)\n{out}", summary

        # wire
        mission_dd.change(
            fn=on_mission_change,
            inputs=[mission_dd],
            outputs=[
                mission_info,
                status,
                leaderboard,
                analysis_dir,
                src_still,
                out_still,
                out_tracks,
                track_preview,
                seed,
                steps,
            ],
        )
        btn_refresh.click(
            fn=refresh,
            inputs=[mission_dd, lab_root, wgp_root],
            outputs=[status, leaderboard, mission_info],
        )
        btn_paths.click(
            fn=check_paths,
            inputs=[mission_dd, suite_root, lab_root, wgp_root],
            outputs=[log, status, leaderboard, mission_info],
        )
        btn_tracks.click(
            fn=build_tracks,
            inputs=[
                mission_dd,
                suite_root,
                lab_root,
                analysis_dir,
                src_still,
                out_still,
                frames,
                apart_dx,
            ],
            outputs=[log, out_tracks, track_preview],
        )
        btn_l0.click(
            fn=lambda st, mid, sd, sp: apply_level(st, mid, "L0", sd, sp),
            inputs=[self.state, mission_dd, seed, steps],
            outputs=[self.refresh_form_trigger, log],
        )
        btn_l1.click(
            fn=lambda st, mid, sd, sp: apply_level(st, mid, "L1", sd, sp),
            inputs=[self.state, mission_dd, seed, steps],
            outputs=[self.refresh_form_trigger, log],
        )
        btn_l2.click(
            fn=lambda st, mid, sd, sp: apply_level(st, mid, "L2", sd, sp),
            inputs=[self.state, mission_dd, seed, steps],
            outputs=[self.refresh_form_trigger, log],
        )
        btn_switch_model.click(
            fn=lambda mid: switch_model(mid, "L2"),
            inputs=[mission_dd],
            outputs=[self.model_choice_target, self.main_tabs],
            show_progress="hidden",
        )
        btn_goto.click(
            fn=self.goto_media_tab,
            inputs=[self.state],
            outputs=[self.main_tabs],
        )
        btn_gate.click(
            fn=run_gate,
            inputs=[lab_root, mission_dd, video_or_frames],
            outputs=[log, gate_json_out],
        )
        btn_gate_last.click(
            fn=gate_last,
            inputs=[lab_root, mission_dd, video_or_frames],
            outputs=[log, gate_json_out],
        )
        return root

    @staticmethod
    def _mission_md(m: dict) -> str:
        notes = m.get("notes") or []
        note_s = " · ".join(str(n) for n in notes[:4]) if notes else "—"
        research = m.get("research") or {}
        best = ""
        if research:
            best = (
                f"  \nResearch so far: seed **{research.get('best_seed')}** · "
                f"progress **{research.get('best_progress')}** · "
                f"`{research.get('best_phase')}`"
            )
        return (
            f"### {m.get('title') or m.get('id')}\n"
            f"{m.get('description') or ''}{best}\n\n"
            f"Gate: `{(m.get('gate') or {}).get('mode')}` · notes: {note_s}"
        )

    @staticmethod
    def _status_md(lab: Path, wgp: Path, m: dict) -> str:
        ok_lab = _lab_py(lab).is_file()
        model = ((m.get("ladder") or {}).get("L2") or {}).get("model") or "lab_wanmove_e01"
        ok_ft = (wgp / "finetunes" / f"{model}.json").is_file() or (
            wgp / "finetunes" / "lab_wanmove_e01.json"
        ).is_file()
        still_ok = False
        tracks_ok = False
        if M is not None:
            try:
                still_ok = M.mission_still(m).is_file()
                tracks_ok = M.mission_tracks(m, 49).is_file()
            except Exception:
                pass
        newest = _newest_video([DEFAULT_OUTPUTS, wgp / "outputs"])
        n_missions = len(_mission_choices())
        return (
            f"**Status:** Lab `{'OK' if ok_lab else 'MISS'}` · "
            f"finetune `{'OK' if ok_ft else 'install_bridge'}` · "
            f"still `{'OK' if still_ok else 'MISS'}` · "
            f"tracks `{'OK' if tracks_ok else 'MISS'}` · "
            f"missions **{n_missions}** · profile **4** · sage  \n"
            f"newest out: `{newest.name if newest else '—'}`  \n"
            f"Ladder: **L0** smoke → **L1** Move smoke → **L2** mission + gate → "
            f"**L3** multi-seed → ship only if gate PASS"
        )
