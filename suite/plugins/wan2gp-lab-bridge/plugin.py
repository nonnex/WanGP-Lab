"""Lab Bridge — researcher mission cockpit (WanGP ↔ Lab motor).

Missions live in suite/missions/<id>/mission.json (e01 is one pack, not the only).
Lab tools run in pipeline/.venv only.

Research loop (cheap-first):
  tracks → L1 iterate (33×8) → glance video → Gate → next-action
  L2 only for good candidates. L0 = UI smoke, never pose signal.
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
PLUGIN_VERSION = "0.6.1"

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
    """Run Lab motor python. Prefer with_ort_wsl_env when WSL vgem DRM is broken."""
    py = _lab_py(lab)
    if not py.is_file():
        return 2, f"Lab venv missing: {py}"
    wrap = DEFAULT_SUITE_ROOT / "suite" / "scripts" / "with_ort_wsl_env.sh"
    if wrap.is_file() and os.environ.get("WANGP_ORT_DRM_NS") != "1":
        cmd = ["bash", str(wrap), "--", str(py), *args]
    else:
        cmd = [str(py), *args]
    try:
        p = subprocess.run(
            cmd,
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


def _last_gate_path() -> Path:
    return DEFAULT_EXPERIMENTS / "last_pose_gate.json"


def _format_gate_hud(
    gate: dict | None,
    video: Path | None = None,
    *,
    level: str | None = None,
) -> str:
    """Compact researcher HUD — gate + KILL/HOLD/PROMOTE/PASS (no false reject)."""
    if not gate:
        return (
            "### Gate HUD\n"
            "_No gate yet. After Generate → **Gate last**._\n\n"
            "Iterate: **L1** = direction · **L2** = amplitude (Hold/Promote) · "
            "L1 FAIL ≠ drop track · L0 ≠ pose  \n"
            "`suite/docs/ITERATE_POLICY.md`"
        )
    ok = bool(gate.get("ok") or gate.get("pose_pass"))
    progress = gate.get("progress")
    try:
        prog_s = f"{float(progress):.2f}"
    except Exception:
        prog_s = str(progress or "—")
    phase = gate.get("phase") or (str(gate.get("note") or "").split(":")[-1] or "—")
    late = gate.get("late_open") or {}
    dy = late.get("max_dy")
    dx = late.get("min_dx")
    metrics = ""
    if dy is not None or dx is not None:
        metrics = f" · dy `{dy}` · dx `{dx}`"
    gate_badge = "**PASS**" if ok else "**FAIL**"
    verdict: dict = {}
    if M is not None:
        verdict = M.iterate_verdict(gate, level=level)
    v = str(verdict.get("verdict") or "HOLD")
    v_line = f"**{v}**"
    if verdict.get("reason"):
        v_line += f" — {verdict['reason']}"
    next_a = ""
    if verdict.get("next"):
        next_a = f"\n\n**Next:** {verdict['next']}"
    elif M is not None:
        hint = M.gate_next_action(str(phase), gate.get("note"))
        next_a = f"\n\n**Next:** {hint.get('next') or '—'}"
    vid = f"\n`{video.name}`" if video else ""
    return (
        f"### Gate HUD · {gate_badge} · iterate {v_line}\n"
        f"progress **{prog_s}** · `{phase}`{metrics}{vid}"
        f"{next_a}"
    )


def _load_last_gate_hud() -> str:
    p = _last_gate_path()
    if not p.is_file():
        return _format_gate_hud(None)
    try:
        gate = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _format_gate_hud(None)
    newest = _newest_video([DEFAULT_OUTPUTS, DEFAULT_WGP_ROOT / "outputs"])
    return _format_gate_hud(gate, newest)


class LabBridgePlugin(WAN2GPPlugin):
    def __init__(self):
        super().__init__()
        self.name = PLUGIN_NAME
        self.version = PLUGIN_VERSION
        self.description = (
            "Researcher cockpit: L1 direction + HOLD/PROMOTE→L2 (no false reject), "
            "tracks+uncross, gate HUD. Generic suite/missions."
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
        default_id = M.default_mission_id() if M is not None else choices[0]
        if default_id not in choices:
            default_id = choices[0]

        try:
            m0 = _load_m(default_id)
        except Exception:
            m0 = {"id": default_id, "title": default_id, "assets": {}, "ladder": {}}

        still0 = M.mission_still(m0) if M else Path()
        tracks0 = M.mission_tracks(m0, 33) if M else Path()
        if M and (not tracks0.is_file()):
            tracks0 = M.mission_tracks(m0, 49)
        _stage(still0 if still0.is_file() else None)
        _stage(tracks0 if tracks0.is_file() else None)
        vis0 = _vis_path(tracks0) if tracks0.is_file() else None

        def _suite_abs(p: str) -> str:
            if not p:
                return ""
            path = Path(p)
            if not path.is_absolute():
                path = DEFAULT_SUITE_ROOT / path
            return str(path.resolve()) if path.exists() else str(path)

        tb = m0.get("track_build") or {}
        analysis0 = _suite_abs(str(tb.get("analysis") or ""))
        src_still0 = _suite_abs(str(tb.get("src_still") or ""))
        apart0 = float(tb.get("apart_dx_default") or 100)
        uf0 = float(tb.get("uncross_frac") or 0.70)
        l1 = (m0.get("ladder") or {}).get("L1") or {}
        seed0 = int(l1.get("seed", 7))

        with gr.Column() as root:
            gr.Markdown(
                f"## Lab Bridge · researcher loop  \n"
                f"`{PLUGIN_VERSION}` · outputs `{DEFAULT_OUTPUTS.name}/` · "
                f"**L1 default** · L2 candidates only"
            )

            gate_hud = gr.Markdown(value=_load_last_gate_hud())

            with gr.Row():
                mission_dd = gr.Dropdown(
                    choices=choices,
                    value=default_id,
                    label="Mission",
                    scale=3,
                )
                btn_refresh = gr.Button("↻", size="sm", scale=0, min_width=48)
            mission_info = gr.Markdown(value=self._mission_md(m0))
            status = gr.Markdown(
                value=self._status_md(DEFAULT_LAB_ROOT, DEFAULT_WGP_ROOT, m0)
            )

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
                btn_paths = gr.Button("Check paths", size="sm")

            gr.Markdown("### 1 · Tracks")
            with gr.Row():
                frames = gr.Dropdown(
                    choices=[33, 49, 81],
                    value=33,
                    label="Frames",
                    info="33 = L1 iterate",
                )
                apart_dx = gr.Dropdown(
                    choices=[80, 100, 120, 140],
                    value=int(apart0) if int(apart0) in (80, 100, 120, 140) else 100,
                    label="apart-dx",
                )
                uncross_frac = gr.Dropdown(
                    choices=[0.55, 0.65, 0.70, 0.75, 0.80],
                    value=uf0 if uf0 in (0.55, 0.65, 0.70, 0.75, 0.80) else 0.70,
                    label="uncross-frac",
                    info="longer = more knee-level before apart",
                )
                btn_tracks = gr.Button("Build tracks", variant="secondary")
            track_preview = gr.Image(
                label="START cyan · END lime (6 control pts)",
                value=str(vis0) if vis0 else None,
                type="filepath",
                height=280,
            )

            gr.Markdown(
                "### 2 · Iterate  \n"
                "**L1** fills form + jumps to Media → Generate. "
                "After video: Gate last. Promote to L2 only if motion looks right."
            )
            with gr.Row():
                seed = gr.Number(value=seed0, label="Seed", precision=0, scale=1)
                steps = gr.Dropdown(
                    choices=[4, 8, 12, 16, 24, 30],
                    value=8,
                    label="Steps override (L2)",
                    scale=1,
                )
            with gr.Row():
                btn_l1 = gr.Button(
                    "▶ L1 iterate → Media",
                    variant="primary",
                    scale=3,
                )
                btn_l2 = gr.Button("L2 candidate", scale=1)
                btn_l0 = gr.Button("L0 smoke", scale=1)
            with gr.Row():
                btn_switch_l1 = gr.Button("Switch model (L1 smoke)", size="sm")
                btn_switch_l2 = gr.Button("Switch model (L2)", size="sm")
                btn_goto = gr.Button("Open Media Generator", size="sm")

            gr.Markdown("### 3 · Gate")
            video_or_frames = gr.Textbox(
                label="mp4 path (optional)",
                placeholder="empty → newest under _outputs/",
            )
            with gr.Row():
                btn_gate_last = gr.Button("Gate last UI output", variant="primary")
                btn_gate = gr.Button("Gate path above")
            gate_json_out = gr.Textbox(label="Gate JSON (detail)", lines=8, max_lines=16)
            last_video_preview = gr.Video(
                label="Last gated / newest output",
                value=None,
                height=240,
            )

            with gr.Accordion("Leaderboard (last gates)", open=False):
                leaderboard = gr.Markdown(
                    value=M.leaderboard_md(DEFAULT_EXPERIMENTS) if M else "_no mission_lib_"
                )

            log = gr.Textbox(label="Log", lines=6, max_lines=20)

        # ----- handlers -----
        def on_mission_change(mid: str):
            try:
                m = _load_m(mid)
            except Exception as e:
                return (
                    f"**Error:** {e}",
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    seed0,
                    8,
                    0.70,
                    _load_last_gate_hud(),
                )
            still = M.mission_still(m)
            tr = M.mission_tracks(m, 33)
            if not tr.is_file():
                tr = M.mission_tracks(m, 49)
            s_st = _stage(still if still.is_file() else None)
            s_tr = _stage(tr if tr.is_file() else None)
            vis = _vis_path(Path(s_tr or tr)) if (s_tr or tr.is_file()) else None
            tb_m = m.get("track_build") or {}
            l1m = (m.get("ladder") or {}).get("L1") or {}
            uf = float(tb_m.get("uncross_frac") or 0.70)
            return (
                self._mission_md(m),
                self._status_md(DEFAULT_LAB_ROOT, DEFAULT_WGP_ROOT, m),
                M.leaderboard_md(DEFAULT_EXPERIMENTS),
                _suite_abs(str(tb_m.get("analysis") or "")),
                _suite_abs(str(tb_m.get("src_still") or "")),
                str(s_st or still),
                str(s_tr or tr),
                str(vis) if vis else None,
                int(l1m.get("seed", 7)),
                8,
                uf if uf in (0.55, 0.65, 0.70, 0.75, 0.80) else 0.70,
                _load_last_gate_hud(),
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
                _load_last_gate_hud(),
            )

        def check_paths(mid, suite_s, lab_s, wgp_s):
            lab, wgp = Path(lab_s), Path(wgp_s)
            try:
                m = _load_m(mid)
            except Exception as e:
                return str(e), *refresh(mid, lab_s, wgp_s)[:3]
            still = M.mission_still(m)
            tr33 = M.mission_tracks(m, 33)
            tr49 = M.mission_tracks(m, 49)
            lines = [
                f"mission: {m.get('id')} — {m.get('title')}",
                f"Lab py: {_lab_py(lab).is_file()}",
                f"WanGP py: {(wgp / '.venv/bin/python').is_file()}",
                f"still: {still.is_file()} — {still}",
                f"tracks33: {tr33.is_file()} — {tr33}",
                f"tracks49: {tr49.is_file()} — {tr49}",
                f"staged still: {_stage(still if still.is_file() else None)}",
                f"staged tracks33: {_stage(tr33 if tr33.is_file() else None)}",
                f"gate mode: {(m.get('gate') or {}).get('mode')}",
                f"newest video: {_newest_video([DEFAULT_OUTPUTS, wgp / 'outputs'])}",
            ]
            st, lb, mi, _hud = refresh(mid, lab_s, wgp_s)
            return "\n".join(lines), st, lb, mi

        def build_tracks(
            mid, suite_s, lab_s, analysis_s, src_s, out_still_s, nframes, apart, uf
        ):
            lab = Path(lab_s)
            suite = Path(suite_s)
            try:
                m = _load_m(mid)
            except Exception as e:
                return str(e), gr.update(), gr.update()
            nframes = int(nframes)
            apart = float(apart)
            uf = float(uf)
            tb_m = m.get("track_build") or {}
            if not tb_m.get("enabled", True):
                return "track_build disabled for this mission", gr.update(), gr.update()

            still_p = Path(out_still_s) if out_still_s else M.mission_still(m)
            ms = M.mission_still(m)
            if ms.is_file():
                still_p = ms
            def _abs(p: str | Path) -> Path:
                path = Path(p)
                if not path.is_absolute():
                    path = DEFAULT_SUITE_ROOT / path
                return path

            src_p = _abs(src_s or tb_m.get("src_still") or "")
            analysis_p = _abs(analysis_s or tb_m.get("analysis") or "")
            analysis = str(analysis_p)
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
tw,th=int({int(tb_m.get('width') or 832)}),int({int(tb_m.get('height') or 480)})
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

            script = suite / (tb_m.get("script") or "suite/tools/mhr70_to_wanmove_tracks.py")
            if not script.is_file():
                script = suite / "suite/tools/mhr70_to_wanmove_tracks.py"
            if not script.is_file():
                return f"tracks script missing: {script}", gr.update(), gr.update()

            pat = tb_m.get("out_pattern") or "tracks_t{frames}.npy"
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
                    str(int(tb_m.get("width") or 832)),
                    "--height",
                    str(int(tb_m.get("height") or 480)),
                    "--apart-dx",
                    str(apart),
                    "--uncross-frac",
                    str(uf),
                    "--vis",
                ],
                timeout=300,
            )
            staged_t = _stage(out_t if out_t.is_file() else None)
            _stage(still_p if still_p.is_file() else None)
            for extra in (
                out_t.with_suffix(".vis.jpg"),
                out_t.with_name(out_t.stem + ".vis.jpg"),
            ):
                if extra.is_file():
                    _stage(extra)
            vis = _vis_path(out_t)
            return (
                f"exit={code}\ntracks={out_t}\nstaged={staged_t}\n"
                f"apart={apart} uncross_frac={uf} frames={nframes}\n{out}",
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
            # steps override only meaningful on L2; L1 keeps recipe 8
            steps_o = None
            if level == "L2" and steps_v is not None:
                steps_o = int(steps_v)
            elif level == "L1" and steps_v is not None and int(steps_v) in (4, 8, 12):
                # allow cheap step A/B on L1
                steps_o = int(steps_v)
            M.apply_ladder_to_settings(
                settings,
                m,
                level,
                seed_override=seed_o,
                steps_override=steps_o,
                wgp=DEFAULT_WGP_ROOT,
            )
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
                "(If Start image empty: drop from wangp/mask_outputs/)"
            )
            return time.time(), msg

        def apply_l1_and_goto(state, mid, seed_v, steps_v):
            """One-click: fill L1 form + jump to Media Generator."""
            trig, msg = apply_level(state, mid, "L1", seed_v, steps_v)
            tabs = self.goto_media_tab(state)
            return trig, msg, tabs

        def apply_l2_and_goto(state, mid, seed_v, steps_v):
            trig, msg = apply_level(state, mid, "L2", seed_v, steps_v)
            tabs = self.goto_media_tab(state)
            return trig, msg, tabs

        def switch_model(mid, level):
            try:
                m = _load_m(mid)
                model = (m.get("ladder") or {}).get(level, {}).get("model") or "lab_wanmove_e01"
            except Exception:
                model = "lab_wanmove_e01" if level == "L2" else "lab_wanmove_e01_smoke"
            return self.switch_to_model(model, True)

        def run_gate(lab_s, mid, path_s, level_hint="L2"):
            lab = Path(lab_s)
            try:
                m = _load_m(mid)
            except Exception as e:
                return str(e), "", _format_gate_hud(None), None
            path = Path(path_s.strip()) if path_s and str(path_s).strip() else None
            if path is None or not path.exists():
                return "Need existing mp4 or frames dir", "", _load_last_gate_hud(), None
            msg, summary, hud, vid = _gate(lab, m, path, level_hint)
            return msg, summary, hud, str(vid) if vid else None

        def gate_last(lab_s, mid, path_s):
            lab = Path(lab_s)
            try:
                m = _load_m(mid)
            except Exception as e:
                return str(e), "", _format_gate_hud(None), None
            path = Path(path_s.strip()) if path_s and str(path_s).strip() else None
            if path is None or not path.exists():
                path = _newest_video(
                    [DEFAULT_OUTPUTS, DEFAULT_WGP_ROOT / "outputs", DEFAULT_EXPERIMENTS]
                )
            if path is None:
                return (
                    "No video under _outputs/ or experiments/",
                    "",
                    _load_last_gate_hud(),
                    None,
                )
            msg, summary, hud, vid = _gate(lab, m, path, "L1")
            return f"gated: {path}\n{msg}", summary, hud, str(vid) if vid else None

        def _gate(lab: Path, m: dict, path: Path, level: str):
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
                    return f"frame extract failed:\n{out}", "", _format_gate_hud(None), path
                frames_dir = tmp
            elif not path.is_dir():
                return "path must be mp4 or directory", "", _format_gate_hud(None), path

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
                    summary = M.format_gate_summary(gate_d, level=level)
                except Exception as e:
                    summary = str(e)

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
            hud = _format_gate_hud(
                gate_d,
                path if path.is_file() else None,
                level=level,
            )
            return f"exit={code} (0=pass, 3=fail typical)\n{out}", summary, hud, path

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
                uncross_frac,
                gate_hud,
            ],
        )
        btn_refresh.click(
            fn=refresh,
            inputs=[mission_dd, lab_root, wgp_root],
            outputs=[status, leaderboard, mission_info, gate_hud],
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
                uncross_frac,
            ],
            outputs=[log, out_tracks, track_preview],
        )
        btn_l1.click(
            fn=apply_l1_and_goto,
            inputs=[self.state, mission_dd, seed, steps],
            outputs=[self.refresh_form_trigger, log, self.main_tabs],
        )
        btn_l2.click(
            fn=apply_l2_and_goto,
            inputs=[self.state, mission_dd, seed, steps],
            outputs=[self.refresh_form_trigger, log, self.main_tabs],
        )
        btn_l0.click(
            fn=lambda st, mid, sd, sp: apply_level(st, mid, "L0", sd, sp),
            inputs=[self.state, mission_dd, seed, steps],
            outputs=[self.refresh_form_trigger, log],
        )
        btn_switch_l1.click(
            fn=lambda mid: switch_model(mid, "L1"),
            inputs=[mission_dd],
            outputs=[self.model_choice_target, self.main_tabs],
            show_progress="hidden",
        )
        btn_switch_l2.click(
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
            outputs=[log, gate_json_out, gate_hud, last_video_preview],
        )
        btn_gate_last.click(
            fn=gate_last,
            inputs=[lab_root, mission_dd, video_or_frames],
            outputs=[log, gate_json_out, gate_hud, last_video_preview],
        )
        return root

    @staticmethod
    def _mission_md(m: dict) -> str:
        notes = m.get("notes") or []
        note_s = " · ".join(str(n) for n in notes[:3]) if notes else "—"
        research = m.get("research") or {}
        best = ""
        if research:
            best = (
                f" · best seed **{research.get('best_seed')}** "
                f"p**{research.get('best_progress')}** `{research.get('best_phase')}`"
            )
        return (
            f"**{m.get('title') or m.get('id')}** — {m.get('description') or ''}"
            f"{best}  \n"
            f"Gate `{((m.get('gate') or {}).get('mode'))}` · {note_s}"
        )

    @staticmethod
    def _status_md(lab: Path, wgp: Path, m: dict) -> str:
        ok_lab = _lab_py(lab).is_file()
        model = ((m.get("ladder") or {}).get("L1") or {}).get("model") or "lab_wanmove_e01_smoke"
        ok_ft = (wgp / "finetunes" / f"{model}.json").is_file() or (
            wgp / "finetunes" / "lab_wanmove_e01.json"
        ).is_file()
        still_ok = False
        tracks_ok = False
        if M is not None:
            try:
                still_ok = M.mission_still(m).is_file()
                tracks_ok = M.mission_tracks(m, 33).is_file() or M.mission_tracks(m, 49).is_file()
            except Exception:
                pass
        newest = _newest_video([DEFAULT_OUTPUTS, wgp / "outputs"])
        n_missions = len(_mission_choices())
        return (
            f"Lab `{'OK' if ok_lab else 'MISS'}` · "
            f"ft `{'OK' if ok_ft else 'install_bridge'}` · "
            f"still `{'OK' if still_ok else 'MISS'}` · "
            f"tracks `{'OK' if tracks_ok else 'MISS'}` · "
            f"missions **{n_missions}** · p4/sage  \n"
            f"newest: `{newest.name if newest else '—'}` · "
            f"**L1** iterate · **L2** candidate · gate=ship"
        )
