# Runtime paths (lab)

## Path A — JIT (default)

```text
AIIMGSEQ_USE_MHR_MOMENTUM unset/0
bootstrap → MOMENTUM_ENABLED=0
mhr_head → torch.jit.load(mhr_model.pt)
```

Use for: analyze, pose_gate, all ship/dev lattice scoring.

## Path B — Full MHR (opt-in research)

```text
AIIMGSEQ_USE_MHR_MOMENTUM=1
assets: VENDORS/MHR/assets complete
bootstrap → MHR on PYTHONPATH, MOMENTUM_ENABLED unset
mhr_head → MHR.from_files(folder=assets, device=…, lod=1, wants_pose_correctives=True)
requires: working pymomentum geometry (prefer pixi)
```

Use for: LOD experiments, IK/solver spikes, Blender high-fidelity mesh — **after** smoke that from_files returns without hang.

## Switch test

```bash
# Must print MOMENTUM_ENABLED=0 in normal lab scripts
pipeline/.venv/bin/python -c "import sys; sys.path.insert(0,'pipeline'); import _bootstrap, os; print(os.environ.get('MOMENTUM_ENABLED'))"
```
