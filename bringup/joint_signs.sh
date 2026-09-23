#!/usr/bin/env bash
# Per-arm joint corrections between LeRobot's convention and the URDF.
#
# Neither of these is derivable from the data and neither is fixed by
# recalibration - they have to be observed once by eye and recorded.
#
#   *_INVERT  comma-separated joints that rotate the wrong way
#   *_OFFSET  joint=degrees, a constant rotation added after inversion.
#             Needed where a joint's true neutral is not the calibrated
#             midpoint. wrist_roll is the usual case: lerobot forces its range
#             to [0,4095] so its midpoint is always 2047.5 no matter where the
#             joint physically sits, which can leave the gripper rendered
#             rotated relative to the real arm.

FERB_INVERT=""
FERB_OFFSET=""                   # re-evaluate after unwrapping

PHINEAS_INVERT=""
PHINEAS_OFFSET=""

export FERB_INVERT FERB_OFFSET PHINEAS_INVERT PHINEAS_OFFSET
