# Momentum / MHR — Lab reference

**Status:** verified against local vendors + SAM3D integration (2026-07-26)  
**Stack pieces:**

| Piece | Path | Size (lab) | License |
|-------|------|------------|---------|
| **MHR** (param body model) | `_COMMON/VENDORS/MHR` → may link via `pipeline/vendor/MHR` | **~11 GB** (assets dominate) | **Apache-2.0** |
| **Momentum** (C++/kinematics lib) | `_COMMON/VENDORS/momentum` | ~902 MB source tree | Meta open (see LICENSE) |
| **pymomentum** (Python wheels) | lab `pipeline/.venv` site-packages | pip `pymomentum-core` / cpu/gpu variants | experimental on PyPI |
| **JIT runtime used by SAM3D** | hub `…/sam-3d-body-dinov3/assets/mhr_model.pt` **or** `MHR/assets/mhr_model.pt` | **~664–696 MB** | ships with SAM3D / MHR assets |

**Papers:** [MHR arXiv:2511.15586](https://arxiv.org/abs/2511.15586) · related ATLAS (ICCV 2025)  
**Code:** [facebookresearch/MHR](https://github.com/facebookresearch/MHR) · [facebookresearch/momentum](https://github.com/facebookresearch/momentum) · docs [facebookresearch.github.io/momentum](https://facebookresearch.github.io/momentum/) · [facebookresearch.github.io/MHR](https://facebookresearch.github.io/MHR/)

Canonical lab note for **what Momentum/MHR is**, how SAM3D uses it, and what we can/cannot do on 16 GB Linux.

---

## 1. Identity (three layers — do not collapse names)

```text
┌─────────────────────────────────────────────────────────────┐
│  SAM 3D Body (HMR net)                                      │
│  predicts MHR *parameters* from an image                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ body/hand/shape/scale/face params
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  MHR — Momentum Human Rig (parametric character)            │
│  skeleton + mesh LODs + blendshapes + pose correctives      │
│  Python package `mhr` · assets FBX/npz/model          │
└──────────────────────────┬──────────────────────────────────┘
                           │ Character.load_fbx / skin / solve
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Momentum / PyMomentum — kinematics + optimization runtime  │
│  C++ library + Python bindings (geometry, solver, …)        │
└─────────────────────────────────────────────────────────────┘
```

| Name | What it is | Lab default |
|------|------------|-------------|
| **Momentum** | Foundational **human kinematics + numerical solvers** (FK/IK, tracking, etc.) | dependency of full MHR path |
| **MHR** | **Parametric full-body digital human** built *on* Momentum ideas/APIs | **assets present**; full Python path **opt-in only** |
| **mhr_model.pt (JIT)** | TorchScript graph of MHR LOD1 skinning path | **Production path inside SAM3D** |
| **pymomentum** | Python bindings / wheels | installed in venv; full `from_files` still risky |

**One-line:** Momentum is the *engine*; MHR is the *character model*; SAM3D is the *image→params* net that drives MHR.

---

## 2. MHR model facts (paper + package)

### 2.1 Design

- Decoupled **internal skeleton** vs **surface shape** (ATLAS lineage).
- Linear blend skinning (LBS) + **non-linear pose correctives** (local non-linear + sparse geodesic linear).
- CG- and CV-friendly; FBX / GLTF friendly upstream.
- Output representation of **SAM 3D Body**.

### 2.2 Counts (paper / package)

| Quantity | Value |
|----------|------:|
| Joints \(n_j\) | **127** |
| Pose / model parameters | **204** (incl. skeleton transform params; SAM3D npz often stores `mhr_model_params` **204**) |
| Identity (shape) blendshapes | **45** |
| Face expression blendshapes | **72** |
| Scale-related comps (SAM3D head) | **28** scale comps in head buffers |
| Hand pose comps (SAM3D head) | **54** per side (compact) |
| Keypoints full MHR | **308** (SAM3D lab uses **MHR70** = first 70) |
| Mesh LODs | **0–6** (7 levels) |

### 2.3 LOD vertex counts (paper)

| LOD | Vertices (approx.) | Lab note |
|-----|-------------------:|----------|
| 0 | 73639 | heaviest assets |
| **1** | **18439** | **SAM3D default mesh**; matches our `pred_vertices` shape |
| 2 | 10661 | |
| 3 | 4899 | |
| 4 | 2461 | |
| 5 | 971 | |
| 6 | 595 | lightest |

Corrective blendshape NPZs on disk: lod0 ~2.5 GB … lod6 ~21 MB (see assets table).

---

## 3. Local assets (`VENDORS/MHR/assets`)

| File | Role |
|------|------|
| `lod0.fbx` … `lod6.fbx` | Rigged mesh LODs |
| `compact_v6_1.model` | Model parameterization |
| `corrective_blendshapes_lod*.npz` | Pose correctives per LOD |
| `corrective_activation.npz` | Corrective activation |
| `mhr_model.pt` | TorchScript MHR (LOD1-oriented) |
| `LICENSE.txt` | asset license |

Bootstrap requires for “assets present”: `lod1.fbx`, `compact_v6_1.model`, `corrective_blendshapes_lod1.npz`.

---

## 4. Two runtime paths (critical for lab)

### 4.1 Path A — JIT (default, proven)

```text
MOMENTUM_ENABLED=0   # env SET to any value → mhr_head disables Momentum import
# sam_3d_body MHRHead:
self.mhr = torch.jit.load(mhr_model_path)  # mhr_model.pt
```

| Pros | Cons |
|------|------|
| No FBX / full assets load at SAM3D init | LOD1-oriented; limited property access |
| Stable on lab host with Wan 16 GB | Not full Momentum solver API |
| Same mesh/joint tensors SAM3D expects | |

**This is what analyze_anchors / pose_gate use today.**

### 4.2 Path B — Full MHR + PyMomentum (opt-in)

```text
AIIMGSEQ_USE_MHR_MOMENTUM=1
# + assets present
# bootstrap: puts VENDORS/MHR on path, unsets MOMENTUM_ENABLED
# mhr_head: MHR.from_files(folder=assets, device=cuda|cpu, lod=1, wants_pose_correctives=True)
```

`MHR.from_files` loads:

1. `lod{N}.fbx` + `compact_v6_1.model` via `pymomentum.geometry.Character.load_fbx(..., load_blendshapes=True)`
2. Identity + face blendshapes
3. Corrective blendshapes NPZ + activation
4. Builds torch character for `forward(...)`

| Pros | Cons |
|------|------|
| Full LODs, correctives, solver hooks | **Lab: hang / SEGFAULT risk** with pip pymomentum + GPU |
| Pixi env recommended upstream | ~GB asset I/O; heavier RAM |
| Artist/CG export paths | Must not mix casually with Wan peak VRAM |

**Lab rule:** full Momentum path only after planned verification window — never default mid-ship.

### 4.3 Env cheat-sheet (`pipeline/_bootstrap.py`)

| Env | Default | Effect |
|-----|---------|--------|
| `MOMENTUM_ENABLED` | **set to `0`** when Momentum path off | Any set value → mhr_head **disables** `from mhr.mhr import MHR` and uses JIT |
| `AIIMGSEQ_USE_MHR_MOMENTUM` | **0** | `1` only if assets OK **and** from_files known-good |

Quirk (upstream mhr_head):  
`MOMENTUM_ENABLED = os.environ.get("MOMENTUM_ENABLED") is None`  
→ Momentum import attempted only when env var is **unset**. Setting `MOMENTUM_ENABLED=0` correctly forces JIT.

---

## 5. Parameterization (what SAM3D writes)

From SAM3D `MHRHead` / lab npz (LOD1):

| Block | Dim (lab) | Meaning |
|-------|----------:|---------|
| Global rot (cont) | 6 | 6D rotation |
| Body continuous | 260 | compact body pose |
| Shape | 45 | identity |
| Scale | 28 | skeleton/scale comps |
| Hand ×2 | 54×2 | hands |
| Face | 72 | expression |
| **mhr_model_params** | **204** | packed model params (npz) |
| **pred_joint_coords** | **(127, 3)** | full joint coords |
| **pred_global_rots** | **(127, 3, 3)** | per-joint global rotations |
| **pred_vertices** | **(18439, 3)** | LOD1 mesh |
| **pred_keypoints_3d** | **(70, 3)** | MHR70 subset for CV |

Lab gates use **MHR70** (knees 11/12), not all 127 joints. Full 127/308 available for Blender / future biomechanics.

---

## 6. Momentum library capabilities (upstream — useful if Path B works)

From Momentum README / docs (not all wired in lab):

| Area | Capability |
|------|------------|
| Forward / inverse kinematics | Interpretable parameterization |
| Solvers | Numerical optimization for tracking |
| RGB-D / mono body tracking | Example applications in docs |
| Python modules (wheels) | `geometry`, `solver2`, `marker_tracking`, `camera`, `renderer`, `torch` helpers; cpu/gpu add `diff_geometry`, `solver` |
| Formats | FBX, GLTF load/export (character pipeline) |

**Mission angle:** if full MHR+Momentum is stable, possible lab uses:

- IK refine of SAM3D params under joint limits  
- Marker/trajectory fitting (still not video diffusion)  
- Better mesh LOD for Blender realtime vs quality  
- Export animation curves for tools outside Wan  

None of that replaces TI2V-5B motion; it strengthens **pose truth and editing**.

---

## 7. Lab integration map

```text
SAM3D Body ──params──► MHRHead ──┬── JIT mhr_model.pt ──► verts, j3d, MHR70   [DEFAULT]
                                 └── MHR.from_files + pymomentum ──► same     [OPT-IN]

verts/j3d/kp ──project_2d──► trust ──► auto_motion / pose_gate / Blender
```

| Consumer | Needs from MHR |
|----------|----------------|
| `analyze_anchors` | verts optional; kp3d+cam+focal required |
| `pose_gate` / `auto_motion` | MHR70 knees (11/12) in 2D |
| Blender DebugTool | mesh LOD1 + skeleton edges |
| `interpolate_mid_poses` | kp3d leg_switch open mid (QA) |

---

## 8. Capabilities vs non-capabilities (lab-honest)

### Can (Path A JIT — now)

- Skin SAM3D parameters to **18439-vert** mesh + 70/127 joints  
- Stable analyze + live gates  
- Blender mesh/skel QA  
- Param tensors in npz for offline experiments  

### Can (Path B — if stabilized)

- Choose LOD 0–6  
- Explicit pose correctives on/off  
- Momentum solvers / IK / tracking APIs  
- Richer CG export  

### Cannot / must not assume

| Desire | Reality |
|--------|---------|
| “Momentum animates the VN” | No — still parametric mesh, not I2V |
| Default full Momentum on 5060 Ti lab | **No** — hang/SEGFAULT history |
| pip pymomentum = pixi quality | Experimental; ABI/torch pin pain |
| JIT = full property access | Limited vs from_files |
| Multi-person MHR IDs | Same 1-person lab assumption |
| Drive Wan DiT with MHR params natively | No adapter in stack |

---

## 9. Install notes (upstream vs lab)

| Method | Upstream | Lab |
|--------|----------|-----|
| Pixi in MHR repo | **Recommended** | Optional separate env; not lab venv default |
| TorchScript only | `mhr-download-assets` → `mhr_model.pt` | **What SAM3D uses** |
| pip mhr + pymomentum-cpu/gpu | Experimental | venv has pymomentum; full from_files not default |
| Assets download | `pixi run download-assets` / `mhr-download-assets` | Already under `VENDORS/MHR/assets` (~11 GB) |

---

## 10. Failure modes (lab memory)

| Failure | Symptom | Mitigation |
|---------|---------|------------|
| Import MHR without assets | crash/hang in from_files | bootstrap keeps MHR off path |
| `MOMENTUM_ENABLED` unset + mhr importable | mhr_head tries from_files | set `MOMENTUM_ENABLED=0` |
| pymomentum ABI ≠ torch | import/runtime errors | pin wheels or pixi |
| `with_blend_shape` SEGFAULT | known risk notes | stay on JIT |
| Loading lod0 correctives | multi-GB RAM | stay LOD1 |
| Concurrent Wan + full MHR load | OOM | sequential jobs |

---

## 11. Mission relevance (still→motion lab)

| Goal | Momentum/MHR role |
|------|-------------------|
| Leg-cross geometry truth | MHR70 knees via SAM3D+JIT |
| Bridge-Search gates | open/flip on projected joints |
| Lattice mid QA | mesh/skel in Blender (skeleton-only mids preferred) |
| Future structure/IK | Path B solvers — research spike only |
| Ship video | Still Wan TI2V-5B (+ later Move etc.) |

**Do not** block ship on full Momentum. **Do** keep assets on disk for when Path B is verified.

---

## 12. Commands

```bash
# Confirm lab is on JIT path
pipeline/.venv/bin/python - <<'PY'
import os, sys
sys.path.insert(0,"pipeline")
import _bootstrap
print("MOMENTUM_ENABLED", os.environ.get("MOMENTUM_ENABLED"))
print("USE_MHR_MOMENTUM", os.environ.get("AIIMGSEQ_USE_MHR_MOMENTUM"))
PY

# Demo MHR package (pixi shell inside VENDORS/MHR recommended for full path)
# cd /home/nick/AI/_COMMON/VENDORS/MHR && pixi shell && python demo.py

# SAM3D still analyze (uses JIT MHR inside)
pipeline/.venv/bin/python pipeline/analyze_anchors.py …
```

---

## 13. Related lab docs

| Doc | Relation |
|-----|----------|
| `_docs/SAM3D-Body/` | Who *predicts* MHR params |
| `_docs/SAM3D-Body/MHR70_INDICES.md` | Joint index cheat-sheet |
| `_docs/Wan2_2-TI2V-5B/` | Who *animates* pixels |
| `pipeline/_bootstrap.py` | Path A vs B switch |

---

## 14. One-line essence

**Momentum = kinematics/solver runtime; MHR = 127-joint / multi-LOD parametric human (Apache); lab production path is TorchScript MHR LOD1 inside SAM3D (`MOMENTUM_ENABLED=0`), while full `MHR.from_files`+pymomentum is an opt-in research path with known stability risk — use MHR for pose truth and Blender QA, not as a video generator.**
