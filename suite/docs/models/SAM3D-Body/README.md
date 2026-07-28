# SAM 3D Body — Lab reference

**Status:** verified against local weights + lab stack (2026-07-26)  
**Checkpoint:** `facebook/sam-3d-body-dinov3`  
**Snapshot:** `11aaa346c7204874a1cbafe3d39a979080b2c55a`  
**On disk:** `pipeline/models` → `/home/nick/AI/_COMMON/MODELS/hub/models--facebook--sam-3d-body-dinov3` (~2.7 GB hub; **model.ckpt ~2.0 GB**, **mhr_model.pt ~664 MB**)  
**Code:** `pipeline/vendor/sam-3d-body` → `_COMMON/VENDORS/sam-3d-body`  
**License:** **SAM License** (Meta) — not Apache; gated HF access (`nonnex` / request required)  
**Paper:** [arXiv:2602.15989](https://arxiv.org/abs/2602.15989) · Meta Research page · [github.com/facebookresearch/sam-3d-body](https://github.com/facebookresearch/sam-3d-body)

This folder is the **canonical lab note** for SAM 3D Body in *our* still→motion stack. Prefer this over chat memory when changing analyze / pose gates / Blender push.

---

## 1. Identity

| | |
|--|--|
| Full name | **SAM 3D Body (3DB)** — promptable single-image full-body **3D human mesh recovery (HMR)** |
| Role in lab | **Pose truth** for stills + gen frames: MHR70 joints, mesh, cam/focal → auto_motion, lattice, pose_gate, Blender QA |
| Not | Video model, I2V, optical flow, or a drop-in ControlNet for Wan |
| Backbone (ours) | **DINOv3-H+** (~840M class encoder path); alternate HF release: ViT-H |
| Mesh / rig | **Momentum Human Rig (MHR)** — skeletal structure decoupled from surface shape |
| Keypoint set we use | **MHR70** (first 70 of 308 MHR kpts; body+feet+hands subset) |

Official claims: strong in-the-wild generalization, occlusions/hard poses, promptable (masks / 2D kpts), open weights + dataset.

---

## 2. What we run (exact lab path)

### 2.1 Import / bootstrap

```text
import _bootstrap   # FIRST in every script
# adds pipeline/vendor/sam-3d-body (+ sam3) to sys.path
# MOMENTUM_ENABLED=0 by default → JIT mhr_model.pt (not full pymomentum FBX)
from sam_3d_body import load_sam_3d_body_hf, SAM3DBodyEstimator
```

| Env | Default | Meaning |
|-----|---------|---------|
| `MOMENTUM_ENABLED` | **0** | Force JIT `mhr_model.pt` path in `mhr_head` |
| `AIIMGSEQ_USE_MHR_MOMENTUM` | **0** | Opt-in full MHR.from_files + assets (hangs/SEGFAULT risk on this host) |
| HF cache | `pipeline/models` via `_bootstrap` | not `~/.cache/huggingface` |

### 2.2 Estimator setup (lab convention)

```python
model, model_cfg = load_sam_3d_body_hf("facebook/sam-3d-body-dinov3", device=device)
estimator = SAM3DBodyEstimator(
    sam_3d_body_model=model,
    model_cfg=model_cfg,
    human_detector=None,   # full-image box [0,0,W,H]
    human_segmentor=None,
    fov_estimator=None,    # model focal, not MoGe2
)
outputs = estimator.process_one_image(
    img_rgb,                 # HxWx3 RGB uint8
    bboxes=None,
    masks=None,
    use_mask=False,
    inference_type="full",
)
```

**Proven path:** `mode=full` — no external SAM3 mask/bbox required for default anchors.  
**Optional:** `mode=masked` with SAM3 person bbox+mask when person pick is trustworthy.

### 2.3 API surface (`process_one_image`)

| Arg | Lab default | Notes |
|-----|-------------|--------|
| `img` | RGB ndarray | str path also supported upstream |
| `bboxes` | `None` | full frame when detector=None |
| `masks` | `None` | |
| `use_mask` | `False` | |
| `inference_type` | `"full"` | |
| `cam_int` | `None` | optional intrinsics |
| `bbox_thr` / `nms_thr` | 0.5 / 0.3 | if detector used |

---

## 3. Outputs (raw model + lab npz)

### 3.1 Upstream dict (per person)

| Key | Role |
|-----|------|
| `pred_vertices` | Mesh verts, camera space |
| `pred_keypoints_3d` | 3D joints |
| `pred_keypoints_2d` | Model-projected 2D (we often **overwrite**) |
| `pred_cam_t` | Camera translation |
| `focal_length` / `focal` | Estimated focal |
| `body_pose_params` / `hand_pose_params` / `shape_params` | MHR params |
| `global_rot`, `pred_global_rots`, `pred_joint_coords`, … | extra |

### 3.2 Lab `sam3d_body.npz` schema (example: `_data/analysis/0009/`)

| Key | Shape (lab) | Notes |
|-----|-------------|--------|
| `pred_keypoints_3d` | **(70, 3)** | MHR70 |
| `pred_keypoints_2d` | **(70, 2)** | **reprojected** via lab `project_keypoints_2d` |
| `pred_keypoints_2d_raw` | (70, 2) | model raw 2D before overwrite |
| `keypoints_2d_source` | str | `"project_3d_cam_focal"` when trusted path |
| `pred_vertices` | **(18439, 3)** | mesh |
| `pred_cam_t` | (3,) | |
| `focal_length` | scalar | e.g. ~2200 @ 1920-wide stills |
| `bbox` | (4,) | often from projected joints in full mode |
| `bbox_source` | str | e.g. `from_projected_joints` |
| `skeleton_trust` | bool | lab gate |
| `skeleton_trust_score` | float | |
| `skeleton_trust_json` | JSON str | full trust dict |
| `body_pose_params` | (133,) | |
| `hand_pose_params` | (108,) | |
| `shape_params` | (45,) | |
| `mhr_model_params` | (204,) | |
| … | | expr, scale, hand bboxes, etc. |

**Critical lab fix (do not regress):**  
Raw model `pred_keypoints_2d` can be misaligned for our gates. We **always** prefer:

```text
kp2d = project(kp3d, pred_cam_t, focal_length, W, H)
# u = f * X/Z + W/2 ; v = f * Y/Z + H/2
```

See `pipeline/analyze_anchors.py` → `project_keypoints_2d`.

---

## 4. MHR70 skeleton (what we measure)

Source: `sam_3d_body/metadata/mhr70.py` — **first 70 of 308** MHR keypoints.

### 4.1 Body indices used for leg gates

| Idx | Name | Lab use |
|-----|------|---------|
| 9 | left-hip | |
| 10 | right-hip | |
| **11** | **left-knee** | `on_top`, open gate |
| **12** | **right-knee** | `on_top`, open gate |
| 13 | left-ankle | tie-break |
| 14 | right-ankle | tie-break |
| 15–20 | toes / heels | feet |
| 0–8 | face / shoulders / elbows | trust body subset |
| 21–69 | hands + extras | not for leg_cross primary |

### 4.2 Lab semantics (image space)

| Metric | Definition | Code |
|--------|------------|------|
| **on_top** | Knee with **smaller image-y** (higher on screen) when seated cross | `auto_motion.leg_on_top_mhr70` |
| **open knees** | `\|dy\| < 45` and `\|dx\| > 55` (480–1080p seated heuristic) | `pose_gate.knees_open_mhr70` |
| **side switch** | start on_top ≠ end on_top + conf | `auto_motion` + `pose_gate` flip mode |

**Not anatomical stick edges:** old lattice sequential i→i+1 overlay was spaghetti (70 joints). Skeleton QA = **Blender DebugTool** (real MHR edges) or gate metrics, not PNG spaghetti.

---

## 5. Trust gate (`skeleton_trust`)

Lab-only (not Meta). Rejects wall-art / broken projection before motion specs.

| Check | Fail if |
|-------|---------|
| Joints in image | frac too low (0.7 default; 0.60 if knees OK + tall bbox) |
| Knees in image | idx 11/12 outside frame |
| Mask overlap | if mask given and frac_mask < 0.35 |
| Tiny bbox | height frac very small without strong mask |

Stored on every analyze / mid / gate analyze.  
**Rule:** untrusted skeleton → **do not** drive auto_motion side_switch or pose_pass.

---

## 6. Architecture / assets (local)

| Asset | Path / size | Role |
|-------|-------------|------|
| DiT/HMR ckpt | `model.ckpt` ~**2.0 GB** | main network |
| MHR JIT | `assets/mhr_model.pt` ~**664 MB** | default decode path |
| Config | `model_config.yaml` | |
| DINOv3 hub | `MODELS/torch/hub/facebookresearch_dinov3_main` | backbone weights via torch hub |
| Full MHR FBX assets | `_COMMON/VENDORS/MHR/assets` | optional; not default |
| Code | VENDORS/sam-3d-body | editable vendor |

### MHR decode paths

| Path | When | Status on lab host |
|------|------|---------------------|
| **JIT** `torch.jit.load(mhr_model.pt)` | `MOMENTUM_ENABLED=0` (default) | **Production path** |
| **Momentum** `MHR.from_files` + FBX | assets + `AIIMGSEQ_USE_MHR_MOMENTUM=1` | hang / SEGFAULT risk with pip wheels; pixi CPU optional |

Do not “fix Momentum” mid-run without a planned upgrade window.

---

## 7. Performance (official + lab)

### 7.1 Official (Meta table, 2025-11 release)

| Backbone | 3DPW MPJPE | EMDB MPJPE | RICH PVE | notes |
|----------|------------|------------|----------|--------|
| DINOv3-H+ (ours) | 54.8 | 61.7 | 60.3 | primary release |
| ViT-H | 54.8 | 62.9 | 61.7 | alternate HF repo |

### 7.2 Lab measurements (practical)

| Workload | Behavior |
|----------|----------|
| Still analyze (1920×1080 full) | loads DINOv3 + ckpt; seconds–tens of s first call |
| pose_gate 2 frames / hop | singleton estimator; cache under `_data/cache/pose_gate/` |
| VRAM | shares GPU with Wan — **do not** run heavy Wan denoise + cold SAM3D load in parallel without headroom |
| Multi-person | estimator can return list; lab is **1-identity** (Sophia); multi-person = silent wrong assign risk |

---

## 8. Lab integration map

```text
Stills ──analyze_anchors (full SAM3D)──► _data/analysis/<id>/sam3d_body.npz
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              auto_motion                pose_lattice              Blender DebugTool
           (side_switch, phases)      (nodes, hop prompts)        (mesh + MHR70 skel)
                    │                         │
                    ▼                         ▼
              FX_MOTION_SPEC              lattice hops (Wan TI2V-5B)
                    │
                    ▼
         score_bridge + pose_gate (live SAM3D on gen frames)
              open_end (e01) / flip (e12, stitch)
```

| Module | SAM3D role |
|--------|------------|
| `analyze_anchors.py` | Authoritative still analysis + trust + project 2D |
| `auto_motion.py` | Leg facts → motion_hint / phase_directives / verifier labels |
| `pose_lattice.py` | Load trusted npz; interpolate mid nodes (no spaghetti overlay) |
| `interpolate_mid_poses.py` | leg_switch open mid for **QA** (Blender); not Wan last_image |
| `pose_gate.py` | Live open/flip on **generated** frames |
| `score_bridge_candidate.py` | hard_ok requires pose_ok when gate active |
| Blender DebugTool | Visual mesh/skel; skeleton-only mids preferred |

---

## 9. Capabilities vs non-capabilities

### Can (and should)

- Single-image full body+hands+feet mesh/pose  
- Trusted 2D knees for **on_top** / **open** after projection  
- Drive fixture-agnostic auto_motion from still pairs  
- Live-gate gen frames (Bridge-Search pose-first)  
- Blender QA of 3D pose/mesh  
- Optional mask/bbox prompts (upstream) when detector path enabled  

### Cannot / must not assume

| Desire | Reality |
|--------|---------|
| Temporal track across video | **Per-frame independent**; no built-in tracker |
| Perfect depth/metric scale | Weak-perspective-ish cam; good for **relative** leg order |
| Multi-person identity | Lab assumes 1 person; wrong box → wrong Sophia |
| Replace Wan motion | Analysis/gates only — does not animate |
| Feed mesh-lerp as TI2V-5B last_image | TI2V expand_timesteps ignores last_image |
| Sequential joint stick = anatomy | 70 kpts need MHR edge list (Blender) |
| Default full Momentum GPU MHR | Not stable here; JIT only |

### Known failure modes (lab)

| Failure | Symptom | Mitigation |
|---------|---------|------------|
| Unprojected raw kp2d | Stick/gates off body | Always `project_3d_cam_focal` |
| Masked mode bad crop | Wall-art / partial body | Prefer **full** mode |
| Untrusted skeleton | Gates on noise | `skeleton_trust` hard fail |
| Crossed legs occlusion | on_top conf low | conf thresholds; human contact |
| Gen-frame domain shift | SAM3D on I2V junk | integrity gate before pose; trust score |
| Load with Wan resident | VRAM fight | sequential jobs; free CUDA between |

---

## 10. License / access

- **SAM License** (Meta), last updated 2025-11-19 — research/use with redistribution terms; **not** Apache-2.0 like Wan weights.  
- HF repo is **gated** (contact info / accept terms). Lab account: access required for `facebook/sam-3d-body-dinov3` (+ dinov3 hub).  
- Cite Meta SAM 3D Body paper if publishing results.

---

## 11. Related models (do not confuse)

| ID | Role |
|----|------|
| `facebook/sam-3d-body-dinov3` | **Ours** — DINOv3 backbone |
| `facebook/sam-3d-body-vith` | Alternate ViT-H backbone |
| `facebook/sam3` | 2D segmentation (masks); optional person pick |
| `facebook/sam-3d-objects` | Objects, not human body |
| DWPose / OpenPose | Older 2D pose; **replaced** by SAM3D in lab analyze layer |
| Full MHR + pymomentum | Optional decode stack; not default |

---

## 12. Lab defaults (doctrine)

| | Recommendation |
|--|----------------|
| Analyze mode | **`full`** + project 2D + trust |
| Decode | JIT MHR (`MOMENTUM_ENABLED=0`) |
| Gates | Live pose_gate on e01 `open_end`, e12/stitch `flip` |
| Untrusted | Never set side_switch / pose_pass |
| Overlay PNG | Optional; Blender for real skel |
| Parallel with Wan | Avoid simultaneous peak VRAM |
| Multi-person fixtures | Unsupported |

---

## 13. Commands

```bash
# Still analyze (writes sam3d_body.npz + trust)
pipeline/.venv/bin/python pipeline/analyze_anchors.py …

# Smoke
pipeline/.venv/bin/python pipeline/smoke_sam3dbody.py --image _src/….jpeg

# Live gate on gen hop
pipeline/.venv/bin/python pipeline/pose_gate.py hop \
  --frames _data/experiments/…/candidates/e01/seed_0011/frames \
  --mode open_end

# Single frame
pipeline/.venv/bin/python pipeline/pose_gate.py frame path.jpg

# Mid poses for Blender QA (not Wan cond)
pipeline/.venv/bin/python pipeline/interpolate_mid_poses.py \
  --a _data/analysis/0009 --b _data/analysis/0011 --mode leg_switch …
```

---

## 14. One-line essence

**SAM 3D Body = single-image MHR70 mesh/pose oracle (DINOv3, JIT MHR) that supplies trusted 2D/3D joints for auto_motion and live pose gates — not a video model, not multi-person ID, and not a substitute for Wan motion; always project 3D→2D with focal/cam_t and refuse untrusted skeletons.**
