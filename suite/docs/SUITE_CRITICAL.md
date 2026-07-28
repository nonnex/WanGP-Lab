# Suite critical design — WanGP Cockpit + Lab Motor (2026-07-28)

## One sentence

**WanGP is the cockpit; Lab is the motor; never merge the engines.**

---

## What “perfect” means here

| Dimension | Perfect = |
|-----------|-----------|
| Pose hard-case | Measurable open/flip, not “looks ok” |
| 16 GB / 24 GB RAM | Profile 4 + int8 + sage; no thrash |
| Update safety | `git pull` WanGP without losing Lab |
| Iterate speed | Queue zips + finetunes + short smokes |
| Scale | Fixture-agnostic tracks/gates, not day21-only hacks |
| Trust | Wrong tracks / wrong still res cannot silently ship |

---

## Non‑negotiable boundaries

```
┌─────────────────────────────────────────────────────────────┐
│ WanGP (.venv)                                               │
│  Gen · UI · Queue · Motion Designer · DA3 preprocess · mmgp │
│  finetunes/ lab_* · plugin wan2gp-lab-bridge                │
└───────────────────────────┬─────────────────────────────────┘
                            │ zips / plugin subprocess / paths
┌───────────────────────────▼─────────────────────────────────┐
│ Lab (pipeline/.venv)                                        │
│  SAM3D · MHR JIT · tracks · pose_gate · lattice · ship      │
│  fixtures · auto_motion · docs · experiments                │
└─────────────────────────────────────────────────────────────┘
```

| Never | Why |
|-------|-----|
| Mix venvs | Torch/SAM3D vs WanGP/mmgp ABI wars |
| Patch `defaults/` or `wgp.py` for Lab | Breaks `git pull` |
| Put pose_gate inside WanGP process as default | VRAM fight + wrong truth layer |
| Treat FastWan pass as pose pass | Documented 5B plateau |
| Full Momentum in WanGP | Lab Path B only, optional |
| Profile 2 as always-on on 24 GB RAM | Swap thrash |

---

## Optimal product surface

### A. Cockpit (WanGP) — daily

1. **Models (finetunes only, not core forks)**  
   - `lab_wanmove_e01` — real pose path  
   - `lab_wanmove_e01_smoke` — 33f×8 iterate  
   - `lab_ti2v5b_fast_e01` — smoke A/B only  

2. **Lab Bridge tab**  
   - Build tracks (Lab subprocess)  
   - Apply preset → main form  
   - Switch finetune  
   - Gate last output (Lab subprocess)  

3. **Motion Designer** (bundled) — visual track edit when auto tracks fail  

4. **Queue zips** — handoff / reload mission runs  

### B. Motor (Lab) — truth

1. Analyze stills (SAM3D full + project + trust)  
2. `mhr70_to_wanmove_tracks.py` (cover-crop + hands)  
3. `pose_gate` open_end / flip  
4. Lattice / ship only after gate pass  
5. Docs + experiments under `_data/` / `_docs/`  

### C. Bridge assets

| Asset | Location |
|-------|----------|
| Source of truth finetunes/plugin | `lab/wangp/` |
| Installed copies/links | `Wan2GP/finetunes`, `Wan2GP/plugins/wan2gp-lab-bridge` |
| Shared media | `_data/cache/wanmove/` + `Wan2GP/mask_outputs/` |
| Installer | `lab/wangp/install_to_wangp.sh` |

---

## Critical failure modes (design against them)

| Failure | Mitigation |
|---------|------------|
| Tracks off-body (wrong src res) | cover-crop + `--src-still`; vis overlay before gen |
| Hand glued to knee | wrists in tracks + neg + CFG&gt;1 |
| Silent ship on junk motion | pose_gate hard; FastWan never ship |
| OOM / 40 GB Move myth | int8 + profile 4; no bf16 14B default |
| 34 GB log spam | headless sparse logs only |
| Config lost on pull | gitignore settings/config; re-run installer |
| Two truths for depth | Lab DA2 vs WanGP DA3 both OK; don’t dual-drive gates |
| Plugin imports Lab torch | subprocess only |

---

## Iterate ladder (suite version)

```
L0  FastWan smoke zip          — UI/pipeline alive?
L1  Move smoke 33f×8           — tracks on-body? hand leave?
L2  Move e01 49f×16            — open_end gate
L3  Multi-seed Move / track A/B — best progress
L4  Lab e12 + stitch + ship    — only if L2/L3 open_end
```

Turbo/FastWan never replaces L2.

---

## What we deliberately do *not* build

- Full Lab rewrite inside WanGP Gradio  
- SAM3D weights inside WanGP venv as default  
- Automatic e12 in UI before open_end  
- WHAM / noise-push / mid-denoise branching as core  
- “One model to rule them all”  

---

## Success metrics

| Metric | Target |
|--------|--------|
| open_end pass rate on Move e01 | rising over track/prompt A/B |
| Time to first smoke | &lt;15 min after cold load |
| `git pull` WanGP | zero Lab merge conflicts |
| False ship | 0 (gate before promote) |

---

## One-page ops

```bash
# install / refresh bridge
bash lab/wangp/install_to_wangp.sh

# cockpit
cd ~/AI/_COMMON/VENDORS/Wan2GP && source .venv/bin/activate
python wgp.py --profile 4 --attention sage

# motor headless (optional)
cd ~/AI/Projects/ai-img-seq-kimi
bash lab/tools/wan2gp_move_e01.sh --profile 4 --frames 49 --steps 16
```
