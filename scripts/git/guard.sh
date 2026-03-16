#!/bin/sh
set -e

branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo "")"
if [ -z "$branch" ]; then
  echo "[WARN] Detached HEAD (no branch). Avoid committing/pushing in this state."
  exit 2
fi

echo "[INFO] repo: $(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
echo "[INFO] branch: $branch"

if [ "$branch" = "master" ]; then
  echo "[BLOCK] master: commit is blocked by pre-commit hook"
  echo "[BLOCK] master: push   is blocked by pre-push hook"
  echo "[HINT ] switch to dev/feature branch:"
  echo "        git checkout dev"
  exit 1
fi

# For non-master branches, allow
echo "[OK] commit allowed on '$branch'"
echo "[OK] push   allowed on '$branch'"
exit 0
