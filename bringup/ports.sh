#!/usr/bin/env bash
# Phineas & Ferb — stable device paths.
#
#   PHINEAS = leader   (the arm with the TRIGGER)   adapter serial 5B42134825
#   FERB    = follower (the arm with the CLAW)      adapter serial 5B42134369
#
# /dev/soarm_a and /dev/soarm_b come from /etc/udev/rules.d/99-soarm101.rules,
# which keys off each adapter's burned-in serial. Unlike /dev/ttyACM0 and
# ttyACM1 they never swap on reboot or replug.
#
# Usage:  source bringup/ports.sh

export FERB_PORT=/dev/soarm_a        # follower, claw
export PHINEAS_PORT=/dev/soarm_b     # leader, trigger

_st() { [ -e "$1" ] && echo "connected -> $(readlink -f "$1")" || echo "NOT CONNECTED"; }
echo "PHINEAS (leader, trigger) $PHINEAS_PORT : $(_st "$PHINEAS_PORT")"
echo "FERB    (follower, claw)  $FERB_PORT : $(_st "$FERB_PORT")"

# Camera mounted on/near Ferb. Empty string disables it.
#
# Mapped with `udevadm info -q property -n /dev/videoN`:
#   /dev/video0, /dev/video2  0c45:6d1f  Integrated_Webcam_HD       (laptop, 2 streams)
#   /dev/video4, /dev/video5  0c45:6366  Innomaker-U20CAM-1080p-S1  (the USB camera)
#
# video2 is the laptop's SECOND sensor, not an external camera - it looks
# plausible in a still, which is how it got picked by mistake once.
export FERB_CAMERA=/dev/video4
export FERB_CAMERA_W=640
export FERB_CAMERA_H=480
