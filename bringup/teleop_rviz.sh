#!/usr/bin/env bash
# Teleoperation WITH both arms live in RViz.
#
#   ./bringup/teleop_rviz.sh [--align-seconds 15] [...]
#
# Teleop owns both serial ports, so the standalone read-only bridge cannot run
# alongside it. Instead the teleop process publishes /phineas/joint_states and
# /ferb/joint_states itself, and robot_state_publisher + RViz consume those.
#
# THIS MOVES FERB. Phineas stays limp. Ctrl-C releases torque and stops RViz.
set -euo pipefail

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$R/bringup/ports.sh" >/dev/null

for p in "$PHINEAS_PORT" "$FERB_PORT"; do
  [ -e "$p" ] || { echo "ERROR: $p not present."; exit 1; }
  if fuser "$(readlink -f "$p")" >/dev/null 2>&1; then
    echo "ERROR: $p is held by another process. Close it first."; exit 1
  fi
done

set +u; source /opt/ros/jazzy/setup.bash; set -u

mkdir -p "$R/urdf/generated"
python3 "$R/tools/prefix_urdf.py" "$R/urdf/phineas_leader.urdf" "$R/urdf/generated/phineas.urdf" phineas_ >/dev/null
python3 "$R/tools/prefix_urdf.py" "$R/urdf/ferb_follower.urdf"  "$R/urdf/generated/ferb.urdf"    ferb_    >/dev/null

mkparams() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
from pathlib import Path
urdf = Path(sys.argv[1]).read_text()
body = "\n".join("      " + ln for ln in urdf.splitlines())
Path(sys.argv[2]).write_text(f"{sys.argv[3]}:\n  ros__parameters:\n    robot_description: |\n" + body + "\n")
PY
}
mkparams "$R/urdf/generated/phineas.urdf" "$R/urdf/generated/phineas_params.yaml" rsp_phineas
mkparams "$R/urdf/generated/ferb.urdf"    "$R/urdf/generated/ferb_params.yaml"    rsp_ferb

cleanup() { echo; echo "[teleop_rviz] shutting down..."; kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

ros2 run tf2_ros static_transform_publisher \
  --x 0 --y 0.35 --z 0 --frame-id world --child-frame-id phineas_base_link &
ros2 run tf2_ros static_transform_publisher \
  --x 0 --y -0.35 --z 0 --frame-id world --child-frame-id ferb_base_link &

ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -r __node:=rsp_phineas -r robot_description:=/phineas/robot_description \
  -r joint_states:=/phineas/joint_states \
  --params-file "$R/urdf/generated/phineas_params.yaml" &

ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -r __node:=rsp_ferb -r robot_description:=/ferb/robot_description \
  -r joint_states:=/ferb/joint_states \
  --params-file "$R/urdf/generated/ferb_params.yaml" &

sleep 2
rviz2 -d "$R/bringup/rviz/both.rviz" &

# Teleop last, and in the foreground, so Ctrl-C reaches it and torque is released.
source "$HOME/lerobot/.venv/bin/activate"
python "$R/tools/teleop_safe.py" \
  --leader-port "$PHINEAS_PORT" --follower-port "$FERB_PORT" --publish-ros "$@"
