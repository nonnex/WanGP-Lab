#!/usr/bin/env bash
# Copy suite finetunes + plugin into local wangp/ (no core edits, no symlinks).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"
WGP="$WANGP_ROOT"
SRC_FT="$ROOT/suite/finetunes"
SRC_PL="$ROOT/suite/plugins/wan2gp-lab-bridge"

[[ -d "$WGP" ]] || { echo "wangp missing: $WGP — run bootstrap_wangp.sh" >&2; exit 2; }
[[ -d "$SRC_FT" && -d "$SRC_PL" ]] || { echo "suite bridge sources missing" >&2; exit 2; }

mkdir -p "$WGP/finetunes" "$WGP/plugins" "$WGP/mask_outputs"

echo "=== install bridge → $WGP ==="
# finetunes: real files (copy) so wangp git status stays clean of broken links
for f in "$SRC_FT"/*.json; do
  [[ -f "$f" ]] || continue
  cp -f "$f" "$WGP/finetunes/$(basename "$f")"
  echo "finetune $(basename "$f")"
done

# plugin: copy tree (or rsync)
rm -rf "$WGP/plugins/wan2gp-lab-bridge"
cp -a "$SRC_PL" "$WGP/plugins/wan2gp-lab-bridge"
echo "plugin wan2gp-lab-bridge"

# assets from suite cache
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
d.setdefault("attention_mode", "sage")
d.setdefault("transformer_quantization", "int8")
d.setdefault("text_encoder_quantization", "int8")
d["wangp_lab_suite"] = True
d["wangp_lab_root"] = "$ROOT"
p.write_text(json.dumps(d, indent=4) + "\n")
print("enabled_plugins:", d["enabled_plugins"])
print("profile:", d.get("profile"), "attention:", d.get("attention_mode"))
PY
else
  echo "WARN: no wgp_config.json yet — start WanGP once, re-run install"
fi

echo "OK → bash $ROOT/suite/scripts/start_wangp.sh"
