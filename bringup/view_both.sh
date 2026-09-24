#!/usr/bin/env bash
# Show BOTH arms live in one RViz. READ-ONLY — nothing commands the motors.
#
#   ./bringup/view_both.sh [extra bridge args...]
#
# Phineas (leader, trigger) is drawn on the +Y side, Ferb (follower, claw) on -Y.
# Calibration is read from each motor's EEPROM; no JSON needed.
#
# Ctrl-C stops everything.
set -euo pipefail

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$R/bringup/ports.sh" >/dev/null

# ROS setup.bash reads unset vars; -u must be off while sourcing it.
set +u; source /opt/ros/jazzy/setup.bash; set -u

mkdir -p "$R/urdf/generated"
python3 "$R/tools/prefix_urdf.py" "$R/urdf/phineas_leader.urdf"  "$R/urdf/generated/phineas.urdf" phineas_ >/dev/null
python3 "$R/tools/prefix_urdf.py" "$R/urdf/ferb_follower.urdf"   "$R/urdf/generated/ferb.urdf"    ferb_    >/dev/null

mkparams() {  # $1=urdf  $2=out yaml  $3=node name
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

_cleaned=0
cleanup() {
  [ "$_cleaned" = 1 ] && return
  _cleaned=1          # kill 0 re-triggers this trap; only run once
  echo; echo "[both] shutting down..."
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Place the two arms either side of a shared 'world' frame so they don't overlap.
ros2 run tf2_ros static_transform_publisher \
  --x 0 --y 0.35 --z 0 --frame-id world --child-frame-id phineas_base_link &
ros2 run tf2_ros static_transform_publisher \
  --x 0 --y -0.35 --z 0 --frame-id world --child-frame-id ferb_base_link &

# Separate node names + remapped topics keep the two robots apart.
# /tf and /tf_static stay global: link names are prefixed, so they cannot collide.
ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -r __node:=rsp_phineas \
  -r robot_description:=/phineas/robot_description \
  -r joint_states:=/phineas/joint_states \
  --params-file "$R/urdf/generated/phineas_params.yaml" &

ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -r __node:=rsp_ferb \
  -r robot_description:=/ferb/robot_description \
  -r joint_states:=/ferb/joint_states \
  --params-file "$R/urdf/generated/ferb_params.yaml" &

sleep 2

echo "[both] PHINEAS bridge <- $PHINEAS_PORT"
"$HOME/soarm101/.rosvenv/bin/python" "$R/tools/joint_state_bridge.py" \
  --port "$PHINEAS_PORT" --prefix phineas_ \
  --ros-args -r __node:=bridge_phineas -r joint_states:=/phineas/joint_states "$@" &

echo "[both] FERB bridge    <- $FERB_PORT"
"$HOME/soarm101/.rosvenv/bin/python" "$R/tools/joint_state_bridge.py" \
  --port "$FERB_PORT" --prefix ferb_ \
  --ros-args -r __node:=bridge_ferb -r joint_states:=/ferb/joint_states "$@" &

sleep 2
echo "[both] RViz — move either arm by hand, both models follow. Nothing is energised."
rviz2 -d "$R/bringup/rviz/both.rviz"
