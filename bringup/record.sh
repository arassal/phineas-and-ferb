#!/usr/bin/env bash
# Record demonstrations for imitation learning.
#
#   ./bringup/record.sh <dataset-name> [--dataset.num_episodes=50] [...]
#
# Phineas (leader) is moved by hand; Ferb (follower) mirrors it, and everything
# both arms do is recorded along with the camera frames.
#
# Cameras: "wrist" is the camera on Ferb's claw. "top" is the laptop webcam,
# used as a workspace overview - a wrist camera alone cannot see the block until
# the gripper is already on top of it, which is when the policy most needs to
# know where to go. Set TOP_CAMERA="" in bringup/ports.sh to record wrist-only.
set -euo pipefail

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$R/bringup/ports.sh" >/dev/null

NAME="${1:?usage: record.sh <dataset-name> [extra lerobot-record args...]}"
shift || true

for p in "$PHINEAS_PORT" "$FERB_PORT"; do
  [ -e "$p" ] || { echo "ERROR: $p not present."; exit 1; }
  fuser "$(readlink -f "$p")" >/dev/null 2>&1 && { echo "ERROR: $p busy (RViz/teleop still running?)"; exit 1; }
done

CAMS="wrist: {type: opencv, index_or_path: $FERB_CAMERA, width: ${FERB_CAMERA_W:-640}, height: ${FERB_CAMERA_H:-480}, fps: 30}"
if [ -n "${TOP_CAMERA:-}" ] && [ -e "${TOP_CAMERA}" ]; then
  CAMS="$CAMS, top: {type: opencv, index_or_path: $TOP_CAMERA, width: 640, height: 480, fps: 30}"
else
  echo "NOTE: recording with the wrist camera only. An overview camera markedly"
  echo "      improves pick-and-place, since the wrist cam cannot see the block"
  echo "      during the approach. Set TOP_CAMERA in bringup/ports.sh."
fi

HF_USER="${HF_USER:-arassal}"
source "$HOME/lerobot/.venv/bin/activate"

exec lerobot-record \
  --robot.type=so101_follower --robot.port="$FERB_PORT" --robot.id=ferb \
  --robot.cameras="{$CAMS}" \
  --teleop.type=so101_leader --teleop.port="$PHINEAS_PORT" --teleop.id=phineas \
  --dataset.repo_id="$HF_USER/$NAME" \
  --dataset.single_task="Pick up the block and place it in the bowl" \
  --dataset.num_episodes=50 \
  --dataset.push_to_hub=false \
  --display_data=true \
  "$@"
