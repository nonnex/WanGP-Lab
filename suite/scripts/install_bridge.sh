#!/usr/bin/env bash
# Install suite → local wangp/ (finetunes, plugin, settings, assets).
# No core edits (defaults/, wgp.py). No symlinks.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
WGP="$WANGP_ROOT"
SRC_FT="$ROOT/suite/finetunes"
SRC_PL="$ROOT/suite/plugins/wan2gp-lab-bridge"
SRC_SET="$ROOT/suite/settings"

[[ -d "$WGP" ]] || { echo "wangp missing: $WGP — run bootstrap_wangp.sh" >&2; exit 2; }
[[ -d "$SRC_FT" && -d "$SRC_PL" ]] || { echo "suite bridge sources missing" >&2; exit 2; }

mkdir -p "$WGP/finetunes" "$WGP/plugins" "$WGP/mask_outputs" "$WGP/settings"

echo "=== install bridge → $WGP ==="

for f in "$SRC_FT"/*.json; do
  [[ -f "$f" ]] || continue
  cp -f "$f" "$WGP/finetunes/$(basename "$f")"
  echo "finetune $(basename "$f")"
done

rm -rf "$WGP/plugins/wan2gp-lab-bridge"
cp -a "$SRC_PL" "$WGP/plugins/wan2gp-lab-bridge"
# drop pyc
rm -rf "$WGP/plugins/wan2gp-lab-bridge/__pycache__"
echo "plugin wan2gp-lab-bridge"

# Model UI defaults from suite SoT
if [[ -d "$SRC_SET" ]]; then
  for f in "$SRC_SET"/*_settings.json; do
    [[ -f "$f" ]] || continue
    cp -f "$f" "$WGP/settings/$(basename "$f")"
    echo "settings $(basename "$f")"
  done
fi

# Assets
if [[ -d "$WANGP_LAB_CACHE" ]]; then
  for f in still_675_832x480.jpg still_675_640x352.jpg \
           tracks_e01_open_hands_t33.npy tracks_e01_open_hands_t49.npy tracks_e01_open_hands_t81.npy; do
    if [[ -f "$WANGP_LAB_CACHE/$f" ]]; then
      cp -f "$WANGP_LAB_CACHE/$f" "$WGP/mask_outputs/$f"
      echo "asset $f"
    fi
  done
fi

CFG="$WGP/wgp_config.json"
TPL="$SRC_SET/wgp_config.template.json"
if [[ ! -f "$CFG" && -f "$TPL" ]]; then
  cp -f "$TPL" "$CFG"
  echo "seeded wgp_config.json from template"
fi

if [[ -f "$CFG" ]]; then
  python3 - <<PY
import json
from pathlib import Path
p = Path("$CFG")
d = json.loads(p.read_text())
en = list(d.get("enabled_plugins") or [])
for x in ("wan2gp-lab-bridge", "motion_designer"):
    if x not in en:
        en.append(x)
d["enabled_plugins"] = en
d["profile"] = int(d.get("profile") or 4)
d["video_profile"] = int(d.get("video_profile") or d["profile"])
d["image_profile"] = int(d.get("image_profile") or d["profile"])
d.setdefault("attention_mode", "sage")
d.setdefault("transformer_quantization", "int8")
d.setdefault("text_encoder_quantization", "int8")
d["enable_int8_kernels"] = 1
d["wangp_lab_suite"] = True
d["wangp_lab_root"] = "$ROOT"
d["last_resolution_choice"] = d.get("last_resolution_choice") or "832x480"
p.write_text(json.dumps(d, indent=4) + "\n")
print("enabled_plugins:", d["enabled_plugins"])
print("profile:", d.get("profile"), "attention:", d.get("attention_mode"))
PY
else
  echo "WARN: no wgp_config.json"
fi

echo "OK → bash $ROOT/suite/scripts/start_wangp.sh"
