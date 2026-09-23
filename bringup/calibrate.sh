#!/usr/bin/env bash
# Calibrate one arm with lerobot-calibrate.
#
#   ./bringup/calibrate.sh phineas
#   ./bringup/calibrate.sh ferb
#
# This does NOT drive the motors: lerobot-calibrate calls disable_torque() first,
# then asks you to move each joint by hand. The arm goes limp.
#
# You will be asked to:
#   1. move the arm so every joint sits in the middle of its range, press ENTER
#   2. sweep each joint through its FULL range of motion, press ENTER
#
# Results are written into each motor's EEPROM and mirrored to
# ~/.cache/huggingface/lerobot/calibration/. Back that directory up — policies
# are tied to the calibration they were trained with.
set -euo pipefail

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$R/bringup/ports.sh" >/dev/null

WHO="${1:?usage: calibrate.sh <phineas|ferb>}"
case "$WHO" in
  phineas) PORT="$PHINEAS_PORT"; ARGS=(--teleop.type=so101_leader   --teleop.port="$PORT" --teleop.id=phineas) ;;
  ferb)    PORT="$FERB_PORT";    ARGS=(--robot.type=so101_follower  --robot.port="$PORT"  --robot.id=ferb) ;;
  *) echo "unknown arm '$WHO' (expected phineas or ferb)"; exit 2 ;;
esac

[ -e "$PORT" ] || { echo "ERROR: $PORT not present."; exit 1; }

echo "Pre-flight check on $WHO ($PORT)..."
if ! "$HOME/soarm101/.rosvenv/bin/python" "$R/tools/diagnose.py" --samples 5 "$PORT" | tee /tmp/precal.txt | grep -q "all motors healthy"; then
  echo
  echo "!! Not all motors are healthy. Calibration sweeps every joint and records"
  echo "!! its range — a joint that cannot report position cannot be calibrated."
  echo "!! See docs/hardware-issues.md. Aborting."
  exit 1
fi

echo
echo "Close any RViz session first — it holds the serial port open."
echo
source "$HOME/lerobot/.venv/bin/activate"
exec lerobot-calibrate "${ARGS[@]}"
