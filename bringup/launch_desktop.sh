#!/usr/bin/env bash
# Desktop entry point: teleoperation + both arms in RViz.
# Kept separate from teleop_rviz.sh so the window stays open on failure and the
# user gets a readable message instead of a terminal that vanishes.

R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cat <<'BANNER'
==========================================================
  PHINEAS  ->  FERB     teleoperation + RViz
==========================================================
  Phineas (trigger) is limp - move it by hand.
  Ferb (claw) is ENERGISED and follows.

  Ferb is walked slowly to Phineas's pose first.
  Keep the workspace clear.

  Press Ctrl-C to stop. That releases Ferb's torque.
==========================================================
BANNER

hold() { echo; read -r -p "Press Enter to close this window... " _ ; }

# Anything already holding a serial port will make this fail confusingly.
for p in /dev/soarm_a /dev/soarm_b; do
  if [ ! -e "$p" ]; then
    echo "ERROR: $p is not present. Is the arm plugged in and powered?"; hold; exit 1
  fi
  if fuser "$(readlink -f "$p")" >/dev/null 2>&1; then
    echo "ERROR: $p is already in use - an RViz or teleop session is still running."
    echo "       Close it, or run:  pkill -f teleop_safe ; pkill -x rviz2"
    hold; exit 1
  fi
done

"$R/bringup/teleop_rviz.sh" --align-seconds 15 "$@"
rc=$?
echo
[ $rc -eq 0 ] && echo "Stopped cleanly. Ferb's torque has been released." \
              || echo "Exited with status $rc - see the messages above."
hold
