#!/usr/bin/env bash
# check_deploy.sh — clone origin/main into a temp dir, build a clean venv
# from requirements.txt only, and run pytest.  Mirrors exactly what the
# deployed app sees.  Run after every push to catch "works locally, breaks
# in prod" failures before they reach users.
#
# Usage:
#   bash scripts/check_deploy.sh
#
# Prerequisites: git, python3 (3.9+), internet access to PyPI.

set -euo pipefail

REMOTE_URL=$(git remote get-url origin)
TMPDIR_BASE=$(mktemp -d /tmp/college-match-deploy-XXXXXX)

cleanup() {
    echo ""
    echo "Cleaning up $TMPDIR_BASE …"
    rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

REPO_DIR="$TMPDIR_BASE/repo"
VENV_DIR="$TMPDIR_BASE/venv"

echo "=== check_deploy.sh ==="
echo "Remote : $REMOTE_URL"
echo "Workdir: $TMPDIR_BASE"
echo ""

# ── 1. Clone exactly what's on origin/main ───────────────────────────────────
echo "--- Step 1: clone origin/main ---"
git clone --depth 1 --branch main "$REMOTE_URL" "$REPO_DIR"
echo "Cloned to $REPO_DIR"
echo ""

# ── 2. Create a clean venv and install only requirements.txt ─────────────────
echo "--- Step 2: create venv and install requirements.txt ---"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"
# Also install pytest (test runner only — not a runtime dependency)
"$VENV_DIR/bin/pip" install --quiet pytest
echo "Installed packages:"
"$VENV_DIR/bin/pip" list --format=columns | grep -E "streamlit|pandas|numpy|altair|pydeck|pytest"
echo ""

# ── 3. Run pytest in the cloned repo ─────────────────────────────────────────
echo "--- Step 3: pytest ---"
cd "$REPO_DIR"
"$VENV_DIR/bin/python" -m pytest tests/ -v

echo ""
echo "=== check_deploy.sh PASSED ==="
