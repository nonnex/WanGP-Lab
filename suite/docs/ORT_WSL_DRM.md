# ORT DRM warning on WSL2

## Symptom

```
[W:onnxruntime:Default, device_discovery.cc:…] GPU device discovery failed:
  ReadFileContents Failed to open file: "/sys/class/drm/card0/device/vendor"
```

## What it is (and is not)

| | |
|--|--|
| **Not** | Missing NVIDIA driver / dead CUDA |
| **Is** | ORT Linux **hardware device discovery** probing DRM sysfs |

On this lab host:

- `/sys/class/drm/card0` → **platform vgem** (virtual gem), not the RTX
- `card0/device/vendor` **does not exist** (vgem is not PCI)
- Real GPU path: **dxgkrnl** PCI `0x1414:0x008e` + `/dev/dxg` + `nvidia-smi`
- `onnxruntime-gpu` still lists `CUDAExecutionProvider`; Torch CUDA works

ORT ≥1.24 scans `/sys/class/drm/cardN/device/vendor`. Older builds treat a
missing vendor as hard failure of the DRM pass and log WARNING
([onnxruntime#26763](https://github.com/microsoft/onnxruntime/issues/26763)).
Upstream later **skips** non-PCI DRM cards (PR [#29858](https://github.com/microsoft/onnxruntime/pull/29858), 2026-07-25).
Pinned wheels here may still be pre-fix.

## Lab handling (clean)

**Do not** swallow stderr with fd filters as the primary fix.

1. **Preflight** — detect broken vgem:
   ```bash
   bash suite/scripts/with_ort_wsl_env.sh --diagnose
   ```
2. **Namespace fix** — empty `/sys/class/drm` in a user+mount namespace so ORT
   does not probe vgem; CUDA stays on `/dev/dxg`:
   ```bash
   bash suite/scripts/with_ort_wsl_env.sh wangp/.venv/bin/python -c 'import onnxruntime as ort; print(ort.get_available_providers())'
   ```
3. **Entry points** — `start_wangp_ui.sh` and `gate_output.sh` wrap via
   `with_ort_wsl_env.sh` automatically.

Disable namespace (debug only):

```bash
WANGP_ORT_DRM_NS=0 bash suite/scripts/start_wangp_ui.sh
```

## Status env

| `WANGP_ORT_DRM_STATUS` | Meaning |
|------------------------|---------|
| `ok` | vendor readable / no fake card |
| `broken_vgem_ns` / `ns_active` | fix applied |
| `broken_vgem_no_ns` | broken host, unshare failed |

## When to revisit

- Upgrade `onnxruntime-gpu` to a build that includes non-PCI DRM skip **and**
  matches WanGP CUDA (currently cu12/cu13 mix is delicate).
- Or Microsoft ships WSL DRM nodes with proper vendor attributes.
