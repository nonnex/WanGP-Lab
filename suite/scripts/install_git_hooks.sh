#!/usr/bin/env bash
# Install repo git hooks (lab hygiene pre-commit).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$ROOT/.git/hooks/pre-commit"
mkdir -p "$ROOT/.git/hooks"
cat > "$HOOK" <<'EOF'
#!/usr/bin/env bash
# WanGP-Lab: block commit if lab is dirty (or auto-fix then re-check)
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
HYGIENE="$ROOT/suite/scripts/lab_hygiene.sh"
[[ -x "$HYGIENE" || -f "$HYGIENE" ]] || exit 0

# Auto-fix quiet, then verify
bash "$HYGIENE" --quiet || true
if ! bash "$HYGIENE" --check --quiet 2>/dev/null; then
  echo "lab hygiene: dirty after auto-fix — run: bash suite/scripts/lab_hygiene.sh" >&2
  bash "$HYGIENE" --check || true
  exit 1
fi
# never stage kilo spam if it reappeared
git rm -r --cached -f .kilo/node_modules .kilo/package.json .kilo/package-lock.json 2>/dev/null || true
exit 0
EOF
chmod +x "$HOOK"
echo "installed $HOOK"
