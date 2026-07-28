#!/usr/bin/env bash
# Lab hygiene — keep WanGP-Lab structured and clean.
# Idempotent. Safe to run anytime (start UI, after Move, pre-commit, /status).
#
#   bash suite/scripts/lab_hygiene.sh           # fix + prune
#   bash suite/scripts/lab_hygiene.sh --check   # report only (exit 1 if dirty)
#   bash suite/scripts/lab_hygiene.sh --quiet   # fix, minimal output
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/config/suite.env"

CHECK=0
QUIET=0
for a in "$@"; do
  case "$a" in
    --check) CHECK=1 ;;
    --quiet|-q) QUIET=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
  esac
done

log() { [[ "$QUIET" == "1" ]] || echo "$@"; }
DIRTY=0
note_dirty() { DIRTY=1; log "  ! $*"; }

# --- layout constants ---
OUT_REAL="${WANGP_LAB_OUTPUTS:-$ROOT/_outputs}"
EXP="${WANGP_LAB_EXPERIMENTS:-$ROOT/data/experiments}"
CACHE="${WANGP_LAB_CACHE:-$ROOT/data/cache/wanmove}"
WGP="${WANGP_ROOT:-$ROOT/wangp}"
KEEP="${WANGP_LAB_KEEP_RUNS:-2}"

ensure_dirs() {
  mkdir -p \
    "$OUT_REAL" \
    "$EXP" \
    "$CACHE" \
    "$ROOT/data/cache" \
    "$ROOT/_logs" \
    "$ROOT/suite/scripts" \
    "$ROOT/suite/tools" \
    "$ROOT/suite/docs" \
    "$ROOT/.kilo/memory"
  touch "$OUT_REAL/.gitkeep" "$EXP/.gitkeep" "$CACHE/.gitkeep" 2>/dev/null || true
}

# wangp/outputs → ../_outputs
ensure_outputs_link() {
  mkdir -p "$OUT_REAL"
  if [[ -L "$WGP/outputs" ]]; then
    local tgt
    tgt=$(readlink "$WGP/outputs" || true)
    if [[ "$tgt" == "../_outputs" || "$tgt" == "$OUT_REAL" ]]; then
      return 0
    fi
  fi
  if [[ "$CHECK" == "1" ]]; then
    note_dirty "wangp/outputs not linked to _outputs"
    return 0
  fi
  if [[ -d "$WGP/outputs" && ! -L "$WGP/outputs" ]]; then
    shopt -s nullglob
    for f in "$WGP/outputs"/*; do
      bn=$(basename "$f")
      [[ -e "$OUT_REAL/$bn" ]] || mv -f "$f" "$OUT_REAL/"
    done
    shopt -u nullglob
    rm -rf "$WGP/outputs"
  fi
  [[ -e "$WGP" ]] || return 0
  ln -sfn ../_outputs "$WGP/outputs"
  log "  fix outputs → _outputs"
}

# Drop IDE / bytecode / temp spam
clean_spam() {
  local paths=(
    "$ROOT/.kilo/node_modules"
    "$ROOT/.kilo/package.json"
    "$ROOT/.kilo/package-lock.json"
    "$ROOT/.kilo/agents/data.md"
  )
  for p in "${paths[@]}"; do
    if [[ -e "$p" ]]; then
      if [[ "$CHECK" == "1" ]]; then note_dirty "spam $(basename "$(dirname "$p")")/$(basename "$p")"
      else rm -rf "$p"; log "  rm spam ${p#"$ROOT"/}"; fi
    fi
  done
  # suite pycache only (never touch wangp/.venv trees heavily — only suite)
  while IFS= read -r -d '' d; do
    if [[ "$CHECK" == "1" ]]; then note_dirty "pycache ${d#"$ROOT"/}"
    else rm -rf "$d"; fi
  done < <(find "$ROOT/suite" -type d -name __pycache__ -print0 2>/dev/null || true)

  # gate frame temps
  for d in "$ROOT"/data/cache/_gate_frames_*; do
    [[ -e "$d" ]] || continue
    if [[ "$CHECK" == "1" ]]; then note_dirty "gate temp $(basename "$d")"
    else rm -rf "$d"; log "  rm $(basename "$d")"; fi
  done

  # empty junk under _logs
  find "$ROOT/_logs" -type f ! -name '.gitkeep' 2>/dev/null | while read -r f; do
    if [[ "$CHECK" == "1" ]]; then note_dirty "log $(basename "$f")"
    else rm -f "$f"; fi
  done
}

# experiments: incomplete out; keep N complete; normalize names
clean_experiments() {
  [[ -d "$EXP" ]] || return 0
  # normalize handoff name
  if [[ -f "$EXP/HANDOFF_L3.md" && ! -f "$EXP/HANDOFF.md" ]]; then
    if [[ "$CHECK" == "1" ]]; then note_dirty "rename HANDOFF_L3.md → HANDOFF.md"
    else mv -f "$EXP/HANDOFF_L3.md" "$EXP/HANDOFF.md"; log "  rename HANDOFF.md"; fi
  elif [[ -f "$EXP/HANDOFF_L3.md" && -f "$EXP/HANDOFF.md" ]]; then
    if [[ "$CHECK" != "1" ]]; then rm -f "$EXP/HANDOFF_L3.md"; fi
  fi

  if [[ "$CHECK" == "1" ]]; then
    # count only
    local n_all n_ok
    n_all=$(find "$EXP" -mindepth 1 -maxdepth 1 -type d -name '*_wan2gp_move_e01' 2>/dev/null | wc -l)
    n_ok=0
    while IFS= read -r d; do
      [[ -z "$d" ]] && continue
      if [[ -f "$d/result.json" ]] && grep -q '"success": true' "$d/result.json" 2>/dev/null; then
        n_ok=$((n_ok + 1))
      elif find "$d/outputs" -name '*.mp4' -print -quit 2>/dev/null | grep -q .; then
        n_ok=$((n_ok + 1))
      else
        note_dirty "incomplete run $(basename "$d")"
      fi
    done < <(find "$EXP" -mindepth 1 -maxdepth 1 -type d -name '*_wan2gp_move_e01' 2>/dev/null)
    if (( n_ok > KEEP )); then
      note_dirty "too many complete runs ($n_ok > keep $KEEP)"
    fi
    local nlog
    nlog=$(ls -1 "$EXP"/l3_*.log "$EXP"/*_console.log 2>/dev/null | wc -l || true)
    if (( nlog > KEEP )); then
      note_dirty "too many console logs ($nlog > $KEEP)"
    fi
    return 0
  fi

  bash "$ROOT/suite/scripts/prune_experiments.sh" "$KEEP" ${QUIET:+>/dev/null} || \
    bash "$ROOT/suite/scripts/prune_experiments.sh" "$KEEP"
}

# root clutter: no random dumps
check_root_clean() {
  local allowed='^(AGENTS\.md|README\.md|WanGP-Lab\.code-workspace|\.gitignore|\.kilocodeignore|\.rgignore)$'
  local f
  for f in "$ROOT"/*; do
    [[ -e "$f" ]] || continue
    local b
    b=$(basename "$f")
    case "$b" in
      suite|wangp|data|config|_outputs|_logs|.kilo|.vscode|.git|.gitignore|.kilocodeignore|.rgignore|AGENTS.md|README.md|WanGP-Lab.code-workspace) continue ;;
      *)
        if [[ -f "$f" ]]; then
          note_dirty "root file: $b"
        elif [[ -d "$f" ]]; then
          note_dirty "root dir: $b"
        fi
        ;;
    esac
  done
}

report() {
  log "=== lab hygiene ==="
  log "keep_runs=$KEEP  check=$CHECK"
  log "outputs: $OUT_REAL  link=$(readlink "$WGP/outputs" 2>/dev/null || echo none)"
  log "experiments:"
  if [[ "$QUIET" != "1" ]]; then
    du -sh "$EXP"/* 2>/dev/null | sort -h | sed 's/^/  /' || true
  fi
  local n_mp4
  n_mp4=$(find "$OUT_REAL" -maxdepth 1 -name '*.mp4' 2>/dev/null | wc -l)
  log "ui_videos: $n_mp4 (cap $KEEP)"
  if [[ -f "$EXP/LEADERBOARD.tsv" ]]; then
    log "leaderboard: $(wc -l < "$EXP/LEADERBOARD.tsv") lines"
  fi
}

# --- main ---
ensure_dirs
ensure_outputs_link
clean_spam
if [[ "$CHECK" == "1" ]]; then
  clean_experiments
  check_root_clean
  report
  if [[ "$DIRTY" == "1" ]]; then
    log "DIRTY — run: bash suite/scripts/lab_hygiene.sh"
    exit 1
  fi
  log "CLEAN"
  exit 0
fi

# fix mode: prune is loud unless quiet
if [[ "$QUIET" == "1" ]]; then
  bash "$ROOT/suite/scripts/prune_experiments.sh" "$KEEP" >/dev/null 2>&1 || true
else
  bash "$ROOT/suite/scripts/prune_experiments.sh" "$KEEP" || true
fi
# handoff rename after prune
if [[ -f "$EXP/HANDOFF_L3.md" && ! -f "$EXP/HANDOFF.md" ]]; then
  mv -f "$EXP/HANDOFF_L3.md" "$EXP/HANDOFF.md"
fi
[[ -f "$EXP/HANDOFF_L3.md" && -f "$EXP/HANDOFF.md" ]] && rm -f "$EXP/HANDOFF_L3.md"

report
log "CLEAN"
