# GitHub issue draft → deepbeepmeep/Wan2GP

**Title:** WSL2: ORT spam `card0/device/vendor` on every import (vgem ≠ GPU) — suggest clean launch-time fix

**Repo:** https://github.com/deepbeepmeep/Wan2GP/issues/new

---

## Body (paste below)

### Summary

On **WSL2 + NVIDIA**, every first `import onnxruntime` prints:

```text
[W:onnxruntime:Default, device_discovery.cc:…] GPU device discovery failed:
  ReadFileContents Failed to open file: "/sys/class/drm/card0/device/vendor"
```

Looks like a broken GPU. It is **not**. CUDA EP and Torch CUDA still work. The noise hits DWPose / SeedVC / SCAIL / any ORT path and confuses users.

### Root cause (host)

| Path | Reality |
|------|---------|
| `/sys/class/drm/card0` | **platform vgem** (virtual), not the RTX |
| `card0/device/vendor` | **missing** (not PCI) |
| Real GPU | `nvidia-smi` OK · `/dev/dxg` · dxgkrnl PCI `0x1414:0x008e` |
| ORT | Linux DRM discovery reads `cardN/device/vendor` (ORT ≥1.24) |

Repro (WSL2):

```bash
ls -l /sys/class/drm/card0/device          # → …/vgem
test -e /sys/class/drm/card0/device/vendor && echo yes || echo ABSENT
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
# → WARNING above, then still CUDAExecutionProvider
```

Upstream context: [onnxruntime#26763](https://github.com/microsoft/onnxruntime/issues/26763). Skip non-PCI DRM cards: [PR #29858](https://github.com/microsoft/onnxruntime/pull/29858) (2026-07-25). Many wheels (incl. common nightlies) still predate that.

### What does *not* need fixing

- Not a missing driver / dead CUDA on typical WSL+NVIDIA setups  
- Not “force CPU”  
- Prefer **not** to hide this with stderr filters (masks real ORT errors)

### Proposed clean fix (WanGP)

**Launch-time, before any ORT import** (shared helper + `wgp.py` / start scripts):

1. **Detect** broken DRM: `card0` exists, `device/vendor` absent, device resolves to `vgem` / `simple-framebuffer`.
2. **Handle** (pick one, prefer A then B):
   - **A.** User+mount namespace: mount empty tmpfs on `/sys/class/drm`, then exec Python. ORT skips DRM probe; CUDA stays on `/dev/dxg`. No log spam.  
     (We verified: warning gone, `torch.cuda` + CUDA EP OK.)
   - **B.** When available: pin `onnxruntime-gpu` that includes non-PCI DRM skip **and** matches WanGP’s CUDA/Torch stack.
3. **Log once** (info):  
   `ORT DRM: non-PCI card0 (vgem) — discovery adjusted; CUDA via NVIDIA/dxg`
4. **Real error only if** `nvidia-smi` / CUDA EP actually missing.

Optional: short **WSL** note in docs with the one-liner diagnose.

### Minimal API sketch

```text
shared/utils/ort_env.py   # detect + optional ns re-exec
wgp.py / launcher         # call before ORT-using imports
docs: one WSL subsection
```

Env escape hatch: `WANGP_ORT_DRM_NS=0` to disable ns path for debugging.

### Why WanGP (not only ORT pin)

ORT is pulled transitively; users stay on mixed nightlies. A **one-time host-aware launch path** fixes all plugins that touch ORT without waiting on wheel lag or teaching everyone to ignore yellow spam.

Happy to refine a PR against current tree if useful.

---

### Meta for opener

- Lab/repro host: WSL2 · RTX 5060 Ti · ORT `1.25.0.dev*` / also seen on `1.25.1` / `1.28.0` still warns until skip lands in the loaded `.so`
- Related suite notes (optional link if public): WanGP-Lab `suite/docs/ORT_WSL_DRM.md`
