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
