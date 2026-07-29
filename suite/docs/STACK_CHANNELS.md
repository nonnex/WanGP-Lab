# Stack channels — rock-solid base + bleeding edge

Lab is a **research cockpit**. Two truths at once:

1. **Base must be rock-solid** — UI starts, Move runs, pose_gate gates, PASS is reproducible.  
2. **Frontier is allowed** — nightlies, new Torch, new kernels, new model weights when the question needs SoTA.

These are **channels**, not moods. Never mix them in one venv.

---

## Channels

| Channel | Role | Default path | When to use |
|---------|------|--------------|-------------|
| **base** | Ship / daily research | `wangp/.venv` | e01 ladder, gate, demos, anything you must trust tomorrow |
| **edge** | SoTA experiments | `wangp/.venv-edge` (create when needed) | nightlies, Torch RC, new attention kernels, unreleased ORT, FP4 trials |
| **rollback** | Last known good | `wangp/.venv-*` snapshots | edge or base broke — swap back in minutes |

Motor pose_gate stays on **its own** venv (`$LAB_MOTOR_ROOT/pipeline/.venv`) — never merge with WanGP channels.

---

## Base (rock-solid)

**Pin to WanGP-tested + this GPU**, not “latest on PyPI”.

Current base (see [WANGP_STACK.md](./WANGP_STACK.md)):

- Python **3.11.x**
- Torch **2.10.x + cu130** (RTX 50xx path)
- Matching sage / GGUF wheels when available
- `requirements.txt` from WanGP tree you actually run

Rules:

- Change base only on purpose (planned cutover), not mid-pose-series.
- After base change: L0 → L1 → Gate smoke + one known mission clip.
- Document fingerprint in `WANGP_STACK.md` (date, py, torch, cuda, key pkgs).
- Prefer **directory swap** over in-place major upgrades.

---

## Edge (frontier)

Create when base is green and you need a capability base lacks:

```bash
cd wangp
# example: clone base then mutate
cp -a .venv .venv-edge   # or fresh uv venv with same py
# then pip install nightlies / torch-test / custom wheels ONLY in .venv-edge
```

Point UI at edge **explicitly**:

```bash
WANGP_VENV="$WANGP_ROOT/.venv-edge" bash suite/scripts/start_wangp_ui.sh
# or temporarily:
# mv .venv .venv-base && mv .venv-edge .venv
```

Rules:

- Edge may break. That is OK. **Base stays untouched.**
- Log every edge run: torch build, commit, wheel URL, mission id, gate result.
- Promote edge → base only after: smoke + **your** hard-case signal (e.g. open_end still PASS or better) + written note in `WANGP_STACK.md`.
- Nightlies are first-class on **edge**, second-class on **base**.

---

## What “up to date” means here

| Layer | Up to date means |
|-------|------------------|
| Suite / Bridge / missions | git main, hygiene, iterate policy |
| **Base** venv | Latest **WanGP-supported** stack for this GPU that still passes lab smoke |
| **Edge** venv | Latest **useful** nightly/RC for the experiment — can lag or lead PyPI |
| Weights / models | As new as the research question; cache under `ckpts` / HF, not in git |
| Driver | Host/WSL; keep modern enough for cu13 apps (you already are) |

“Newest Torch on the index” is **not** automatically base. It is a candidate for **edge**, then maybe promote.

---

## Decision tree

```
Need reliability for e01 / gate / ship?
  → base only

Need feature that only exists on nightly / new torch / new kernel?
  → edge venv
  → one mission A/B vs base
  → if better and stable enough → promote

Base feels old but still works?
  → check WanGP INSTALLATION.md for new recommended pin
  → new venv alongside, smoke, then swap (not fear — process)
```

---

## Anti-patterns

| Don’t | Do |
|-------|-----|
| pip upgrade base mid-experiment | edge clone |
| One venv for “everything latest” | base + edge |
| Promote without gate smoke | promote after smoke + mission signal |
| Mix motor SAM3D venv with WanGP | keep `LAB_MOTOR_ROOT` separate |
| Delete rollback “to free space” same day | keep ≥1 rollback until next base is proven |

---

## Scripts / ops

- Fingerprint: `suite/docs/WANGP_STACK.md`
- Start UI: `bash suite/scripts/start_wangp_ui.sh` (uses `wangp/.venv` or `WANGP_VENV`)
- Switch helper: `bash suite/scripts/stack_channel.sh status|use base|use edge`

Research posture: **base is boring on purpose; edge is where we live at the frontier.**
