# Open hardware issues

## 1. Phineas id 2 (`shoulder_lift`) is over-volted — unresolved

Read from the motors on 2026-09-23:

```
id  name            MinVolt  MaxVolt  Present  err
 1  shoulder_pan        4.0     12.0     12.0    0
 2  shoulder_lift       4.0      8.0     11.9    1   <-- 
 3  elbow_flex          4.0     12.0     12.0    0
 4  wrist_flex          4.0     12.0     12.1    1   <-- marginal
 5  wrist_roll          4.0     12.0     11.9    0
 6  gripper             4.0     12.0     12.0    0
```

Id 2 declares a maximum of **8.0 V** and is being fed **11.9 V**. It raises the
voltage alarm (error byte 1) and refuses to report `Present_Position`. Every
other motor on the arm declares 12.0 V.

That pattern is consistent with a **7.4 V-variant STS3215 fitted to a 12 V arm**.
The SO-ARM101 ships in both 7.4 V and 12 V variants and they are not
interchangeable.

Id 4 is a milder case: limit 12.0 V, present 12.1 V. It alarms because the supply
sits a hair above its threshold.

Consequences:
- Phineas cannot be calibrated (two joints report no position).
- Those two joints are frozen in RViz.
- Probably explains the USB dropout observed at 15:26, when the whole adapter
  disappeared from `lsusb` — a motor in alarm can disturb the bus.

**Next step:** power the arm down and check whether id 2 is physically a
different part from its neighbours. If it is genuinely a 12 V motor whose EEPROM
limit was written wrong, raising `Max_Voltage_Limit` is a single register write.
Do not guess — writing a 12 V limit onto a real 7.4 V motor would remove the
protection that is currently doing its job.

## 2. Ferb has no main power

Every motor on Ferb reports a present voltage of **4.9 V** — USB bus voltage. The
power supply is not connected or not switched on.

Reads work fine (20/20 reliability on all six joints), which is why the arm looked
healthy at first. But it cannot actuate, and calibration writes to EEPROM, which
is better done on proper power.

## 3. Ferb's gripper renders wrong

Body joints track correctly in RViz; the claw does not. Ferb's gripper
calibration range is `[2044, 3519]`, and `MotorNormMode.RANGE_0_100` maps
`range_min` to 0 %. Whether `range_min` corresponds to open or closed depends on
which direction the joint was swept during calibration, so the mapping may simply
be reversed.

Two things to try, in order:
1. Recalibrate the gripper with a clean sweep.
2. If it is still mirrored, run with `--invert gripper`.
