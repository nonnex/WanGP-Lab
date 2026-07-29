# WanGP Python stack (lab host)

**Channels:** base = rock-solid · edge = frontier/nightlies — [STACK_CHANNELS.md](./STACK_CHANNELS.md).  
This file fingerprints **base** (and notes edge when present).

## Active base (2026-07-29)

| | |
|--|--|
| Path | `wangp/.venv` |
| Python | **3.11.14** (uv-managed CPython) |
| PyTorch | **2.10.0+cu130** |
| GPU | RTX 5060 Ti sm_120 |
| Sage | `sageattention==1.0.6` (Sage2 needs system `nvcc`; 1.0.6 works with `--attention sage`) |
| GGUF CUDA | `llamacpp_gguf_cuda` 1.0.2+torch210cu13py311 — **kernels available** |
| ORT | from `requirements.txt` (nightly gpu) |

Matches WanGP docs for RTX 30–50 (`docs/INSTALLATION.md`).

## Rollback

```bash
cd wangp
mv .venv .venv-py311-torch210-cu130   # optional rename current
mv .venv-py312-torch271-cu128 .venv
```

Old stack: Python 3.12 · Torch 2.7.1+cu128 · kept as `wangp/.venv-py312-torch271-cu128`.

## Recreate (no sudo)

```bash
# Python 3.11 via uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11.14
cd wangp
uv venv .venv --python "$(uv python find 3.11)"
uv pip install --python .venv/bin/python pip setuptools wheel
.venv/bin/python -m pip install torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 \
  --index-url https://download.pytorch.org/whl/cu130
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install \
  https://github.com/deepbeepmeep/kernels/releases/download/GGUF_Kernels/llamacpp_gguf_cuda-1.0.2+torch210cu13py311-cp311-cp311-linux_x86_64.whl
.venv/bin/python -m pip install sageattention==1.0.6
bash ../suite/scripts/install_bridge.sh
```

## Sage2 later

Needs system CUDA toolkit (`nvcc`) + build of thu-ml/SageAttention with `TORCH_CUDA_ARCH_LIST=12.0`. Optional; not required for current lab Move path.

## Not done in-place

Never upgrade the live base `.venv` across major torch/python mid-research —  
**swap directories** or use **edge** (`stack_channel.sh init-edge-from-base`).

## Edge / nightlies

- Allowed and expected for SoTA (Torch RC, ORT nightly, new kernels, new weights).
- Live in `wangp/.venv-edge` (or parked snap), not by silently mutating base.
- Promote to base only after smoke + mission signal (gate).
- `bash suite/scripts/stack_channel.sh status`
