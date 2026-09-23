#!/usr/bin/env bash
# Put the launcher on the Desktop.
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
D="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
mkdir -p "$D"
sed "s|/home/alexander/phineas-and-ferb|$R|g" "$R/desktop/Phineas-and-Ferb.desktop" \
  > "$D/Phineas-and-Ferb.desktop"
chmod +x "$D/Phineas-and-Ferb.desktop"
gio set "$D/Phineas-and-Ferb.desktop" metadata::trusted true 2>/dev/null || true
echo "installed: $D/Phineas-and-Ferb.desktop"
