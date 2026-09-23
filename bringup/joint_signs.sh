#!/usr/bin/env bash
# Per-arm joint sign corrections.
#
# LeRobot reports each joint in its own convention; the URDF declares its own
# axis directions. Where the two disagree a joint renders backwards, and there
# is no way to derive this from the data - it has to be observed once by eye and
# recorded. Calibration does NOT fix it: a re-sweep produces the same mapping.
#
# Comma-separated joint names, or empty for none.

FERB_INVERT="wrist_flex"      # observed 2026-09-23: wrist rendered backwards
PHINEAS_INVERT=""             # none observed yet

export FERB_INVERT PHINEAS_INVERT
