# Progress

Updated 2026-09-23.

## Status

| Item | Phineas (leader) | Ferb (follower) |
| --- | --- | --- |
| USB adapter detected | yes — `5B42134825` | yes — `5B42134369` |
| All 6 motors respond to ping | yes | yes |
| All 6 report position | **no — ids 2, 4 fault** | yes, 20/20 reliability |
| Motor IDs set in EEPROM | yes | yes |
| Calibrated | **no — factory default ranges** | yes — real ranges in EEPROM |
| Main power supply | 12.0 V (**over-volts id 2**) | **off — running on USB 5 V** |
| Renders in RViz | partially (2 joints frozen) | yes |

## Done

- [x] LeRobot 0.6.2 installed, editable source install at `~/lerobot`, Python 3.12.3,
      PyTorch 2.11.0+cu128, CUDA available (RTX 3050 Laptop, 4 GB)
- [x] Serial access: user added to `dialout`, plus a udev rule pinning permissions
      and creating `/dev/soarm_a` and `/dev/soarm_b` by adapter serial
- [x] Read-only encoder bridge publishing `/joint_states` at 30 Hz
- [x] Single-arm RViz view (`bringup/view_arm.sh`)
- [x] Dual-arm RViz view with prefixed TF trees (`bringup/view_both.sh`)
- [x] Angle conversion matched to LeRobot's `_normalize`, reading calibration
      straight from motor EEPROM
- [x] Arms identified: the trigger arm is Phineas, the claw arm is Ferb

## Blocked

- [ ] **Calibrate Phineas** — impossible until ids 2 and 4 report position.
      Calibration works by sweeping each joint and recording the range; two
      silent joints means no range to record. See `docs/hardware-issues.md`.
- [ ] **Recalibrate Ferb's gripper** — body joints look right in RViz, the claw
      does not. Wants a fresh calibration sweep, ideally on proper power rather
      than USB 5 V.
- [ ] **Teleoperation** — needs both arms calibrated first.

## Next

1. Resolve Phineas id 2 over-voltage (hardware — needs eyes on the motor).
2. Connect Ferb's power supply.
3. `lerobot-calibrate` on both. Hands-on: sweep every joint through full range.
4. Verify joint directions in RViz; add `--invert <joints>` for any that render
      backwards relative to the URDF.
5. First teleoperation run.
6. Record a dataset (~50 episodes is the community baseline for a working ACT
      policy on pick-and-place; roughly 2 hours of teleoperation).

## Open questions

- Is Phineas id 2 physically a 7.4 V motor, or a 12 V motor whose
  `Max_Voltage_Limit` was written wrong? Determines repair vs one register write.
- Joint sign conventions between LeRobot degrees and the URDF axes are unverified
  — needs an empirical check per joint once both arms are calibrated.
