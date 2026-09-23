#!/usr/bin/env bash
# Phineas (leader) drives Ferb (follower), with a safe start.
#
#   ./bringup/teleop.sh --dry-run     # report how far apart the arms are, move nothing
#   ./bringup/teleop.sh               # align slowly, then follow
#   ./bringup/teleop.sh --align-seconds 15
#
# THIS MOVES FERB. Phineas stays limp and backdrivable; Ferb is energised.
# Keep the workspace clear. Ctrl-C releases torque.
set -euo pipefail

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$R/bringup/ports.sh" >/dev/null

for p in "$PHINEAS_PORT" "$FERB_PORT"; do
  [ -e "$p" ] || { echo "ERROR: $p not present."; exit 1; }
  if fuser "$(readlink -f "$p")" >/dev/null 2>&1; then
    echo "ERROR: $p is held by another process (RViz?). Close it first."
    exit 1
  fi
done

source "$HOME/lerobot/.venv/bin/activate"
exec python "$R/tools/teleop_safe.py" \
  --leader-port "$PHINEAS_PORT" --follower-port "$FERB_PORT" "$@"
