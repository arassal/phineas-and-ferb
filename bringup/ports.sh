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

# Camera on Ferb. Empty string disables it.
#
# Use the /dev/v4l/by-id/ path, NOT /dev/videoN. This camera re-enumerates on
# its own - observed live in dmesg:
#     usb 3-1.1: USB disconnect, device number 24
#     usb 3-1.1: new high-speed USB device number 25
# and every re-enumeration gives it a new node (video4 -> video5). The by-id
# path is keyed on the device identity and serial, so it follows the camera.
# "-index0" is the capture node; "-index1" is metadata and cannot be read.
#
#   Innomaker U20CAM-1080p  SN0001   <- the USB camera
#   Integrated_Webcam_HD             <- the laptop, two streams (0c45:6d1f)
export FERB_CAMERA=/dev/v4l/by-id/usb-Innomaker_Innomaker-U20CAM-1080p-S1_SN0001-video-index0
export FERB_CAMERA_W=640
export FERB_CAMERA_H=480

# Workspace overview camera. The laptop's built-in webcam works well for this:
# point the laptop at the table. A wrist camera alone cannot see the block
# during the approach, which is exactly when the policy needs to know where it
# is. Set to "" to record with the wrist camera only.
# NOTE: the laptop exposes TWO UVC interfaces - a colour sensor and an IR one.
# /dev/v4l/by-id/...-video-index0 points at the IR sensor (all three channels
# identical), which is not what you want. by-path distinguishes the interfaces:
# usb-0:6:1.0 is colour, usb-0:6:1.2 is IR.
export TOP_CAMERA=/dev/v4l/by-path/pci-0000:00:14.0-usb-0:6:1.0-video-index0
