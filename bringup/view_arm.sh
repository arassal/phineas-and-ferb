#!/usr/bin/env bash
# Show ONE arm live in RViz. READ-ONLY — nothing commands the motors.
#
#   ./bringup/view_arm.sh /dev/soarm_a                       # Ferb (follower)
#   ./bringup/view_arm.sh /dev/soarm_b                       # Phineas (leader)
#   ./bringup/view_arm.sh /dev/soarm_a --invert gripper
#
# Calibration is read from each motor's EEPROM; no JSON needed.
set -euo pipefail

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-/dev/soarm_a}"
shift || true
BRIDGE_ARGS=("$@")

# Pick the URDF that matches the arm: Phineas has a trigger, Ferb has a claw.
source "$R/bringup/joint_signs.sh" >/dev/null
case "$(readlink -f "$PORT")" in
  "$(readlink -f /dev/soarm_b 2>/dev/null)")
      URDF="$R/urdf/phineas_leader.urdf"; WHO=Phineas; SIGNS="$PHINEAS_INVERT" ;;
  *)  URDF="$R/urdf/ferb_follower.urdf";  WHO=Ferb;    SIGNS="$FERB_INVERT" ;;
esac
# Recorded sign corrections apply unless --invert is given explicitly.
if [ -n "$SIGNS" ] && [[ " ${BRIDGE_ARGS[*]} " != *" --invert "* ]]; then
  BRIDGE_ARGS+=(--invert "$SIGNS")
fi

[ -e "$PORT" ] || { echo "[view_arm] ERROR: $PORT not present."; exit 1; }

# ROS setup.bash reads unset vars; -u must be off while sourcing it.
set +u; source /opt/ros/jazzy/setup.bash; set -u

mkdir -p "$R/urdf/generated"
PARAMS="$R/urdf/generated/single_params.yaml"
python3 - "$URDF" "$PARAMS" <<'PY'
import sys
from pathlib import Path
urdf = Path(sys.argv[1]).read_text()
body = "\n".join("      " + ln for ln in urdf.splitlines())
Path(sys.argv[2]).write_text("robot_state_publisher:\n  ros__parameters:\n    robot_description: |\n" + body + "\n")
PY

cleanup() { echo; echo "[view_arm] shutting down..."; kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "[view_arm] $WHO  <- $PORT  ($(basename "$URDF"))"
ros2 run robot_state_publisher robot_state_publisher --ros-args --params-file "$PARAMS" &
sleep 2
"$HOME/soarm101/.rosvenv/bin/python" "$R/tools/joint_state_bridge.py" --port "$PORT" "${BRIDGE_ARGS[@]}" &
sleep 2
echo "[view_arm] Move the arm by hand — the model follows. Nothing is energised."
rviz2 -d "$R/bringup/rviz/single.rviz"
