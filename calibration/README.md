# Calibration backups

Copies of the LeRobot calibration files, kept in git so a machine rebuild or a
cleared cache does not cost another hands-on sweep.

Live location: `~/.cache/huggingface/lerobot/calibration/`

```
teleoperators/so_leader/phineas.json
robots/so_follower/ferb.json
```

## These are copies, not the source of truth

`lerobot-calibrate` writes the real calibration into each motor's **EEPROM**
(`Homing_Offset` addr 31, `Min_Position_Limit` 9, `Max_Position_Limit` 11). The
JSON is a mirror. An arm carries its own calibration between machines, which is
why `tools/joint_state_bridge.py` reads from the motors rather than from a file.

Restoring a JSON writes it back to the motors: `lerobot-calibrate` offers this at
startup when a file already exists for that id — press ENTER to reuse the file
rather than `c` to re-sweep.

## Phineas — calibrated 2026-09-23, re-swept 15:59

Verified against the URDF and against Ferb's independent calibration:

| joint | range | span | degrees | URDF | Ferb span |
| --- | --- | --- | --- | --- | --- |
| shoulder_pan | [661, 3379] | 2718 | 238.9 | 220 | 2717 |
| shoulder_lift | [912, 3458] | 2546 | 223.8 | 200 | 2390 |
| elbow_flex | [805, 3023] | 2218 | 195.0 | 194 | 2206 |
| wrist_flex | [700, 3038] | 2338 | 205.5 | 190 | 2292 |
| wrist_roll | [0, 4095] | 4095 | 360.0 | 320 | 4095 |
| gripper | [2037, 3274] | 1237 | 108.7 | 110 | 1475 |

`shoulder_pan` landed within **1 count** of Ferb's independent sweep and
`elbow_flex` within 12 — both arms were taken to their real hard stops, which is
what leader/follower tracking depends on.

Two notes:

- `wrist_roll` is always `[0, 4095]`. LeRobot designates it the full-turn joint
  and hardcodes that range; it is not a calibration fault.
- `wrist_flex` measured 2338 counts on two independent sweeps, identical to the
  count. Its physical travel really is 205.5 degrees while the URDF declares
  190, so the model clamps at the extremes unless run with `--no-clamp`. That is
  a limitation of the upstream URDF, not of the calibration.
