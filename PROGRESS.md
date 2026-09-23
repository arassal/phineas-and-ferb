# Progress

Updated 2026-09-23.

## Status

| Item | Phineas (leader) | Ferb (follower) |
| --- | --- | --- |
| USB adapter detected | yes — `5B42134825` | yes — `5B42134369` |
| All 6 motors respond to ping | yes | yes |
| All 6 report position | yes, 30/30 at 4.9 V | yes, 20/20 reliability |
| Motor IDs set in EEPROM | yes | yes |
| Calibrated | **yes — 2026-09-23** | yes — real ranges in EEPROM |
| Main power supply | 4.9 V — all motors in spec | **unplugged** |
| Renders in RViz | yes — all 6, leader URDF | yes |

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
- [x] **Phineas calibrated** (2026-09-23) after dropping its supply from 12 V to
      4.9 V, which put id 2 back inside its 8.0 V limit and cleared the alarm.
      Sweep quality is good — spans match the URDF and agree closely with Ferb:

      | joint | Phineas span | URDF | Ferb span |
      | --- | --- | --- | --- |
      | shoulder_pan | 2713 | 220 deg | 2717 |
      | shoulder_lift | 2558 | 200 deg | 2390 |
      | elbow_flex | 2208 | 194 deg | 2206 |
      | wrist_flex | 2338 | 190 deg | 2292 |
      | gripper | 1228 | 110 deg | 1475 |

      shoulder_pan within 4 counts of Ferb and elbow_flex within 2 - both arms
      were swept to their real hard stops.

## Blocked

- [ ] **Recalibrate Ferb's gripper** — body joints look right in RViz, the claw
      does not. Wants a fresh calibration sweep, ideally on proper power rather
      than USB 5 V.
- [ ] **Teleoperation** — needs both arms calibrated first.

## Next

1. Reconnect Ferb's motor power (barrel jack on its controller board).
2. Verify joint directions in RViz on both arms; add `--invert <joints>` for any
   that render backwards relative to the URDF.
3. Recheck Ferb's gripper mapping — body joints were right, the claw was not.
4. First teleoperation run.
6. Record a dataset (~50 episodes is the community baseline for a working ACT
      policy on pick-and-place; roughly 2 hours of teleoperation).

## Open questions

- Is Phineas id 2 physically a 7.4 V motor, or a 12 V motor whose
  `Max_Voltage_Limit` was written wrong? Determines repair vs one register write.
- Joint sign conventions between LeRobot degrees and the URDF axes are unverified
  — needs an empirical check per joint once both arms are calibrated.
