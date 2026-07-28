# Bridge-Search strategy (pose-first) — 2026-07-26

## One line

**5B proposes; live pose gates decide; lattice splits time; trajectory/Move only after plateau.**

## Layers

| P | What | Done when |
|---|------|-----------|
| P0 | Live SAM3D gate (`pipeline/pose_gate.py`) | e01 open / e12 flip measured |
| P0 | `search_e01` multi-seed stop-on-open | ≥1 open or plateau doc |
| P1 | e12 only from open anchor | flip gate pass |
| P1 | `hard_ok` requires pose_ok | no kick-as-ship |
| P2 | Wan-Move spike (14B) | go/no-go after 5B plateau |
| P3 | ID-LoRA / multi-seed ship | after pose green |

## Commands

```bash
# Validate gate on existing bad e01 (expect FAIL open_end)
pipeline/.venv/bin/python pipeline/pose_gate.py hop \
  --frames _data/experiments/20260726_151117_lattice_dev/candidates/e01/seed_0011/frames \
  --mode open_end

# P0 search (stop on first open knees)
bash lab/run.sh lattice_search_e01
# or: bash lab/run.sh lattice_dev search_e01=1 seeds="11 22 33 42"

# Disable live gate (debug only)
AIIMGSEQ_LEG_GATE=0 bash lab/run.sh …
```

## Gate heuristics (480p seated)

- **open_end:** `|dy_knees| < 45` and `|dx_knees| > 55`
- **flip:** early/late `on_top` differ; optional expect start/end from auto_motion

## Plateau

If `pose_gates/e01_search_summary.json` has `pass=0` after budget → **do not** L3/L4; consider Wan-Move spike.
