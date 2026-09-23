# Phineas & Ferb

Two SO-ARM101 arms running on [LeRobot](https://github.com/huggingface/lerobot),
with a read-only ROS 2 / RViz visualisation layer built on top.

| Name | Role | Distinguishing feature | Adapter serial | Device |
| --- | --- | --- | --- | --- |
| **Phineas** | Leader | trigger / handle | `5B42134825` | `/dev/soarm_b` |
| **Ferb** | Follower | claw / moving jaw | `5B42134369` | `/dev/soarm_a` |

See [PROGRESS.md](PROGRESS.md) for current status and [docs/hardware-issues.md](docs/hardware-issues.md)
for open hardware faults.

## Quick start

```bash
source ~/lerobot/.venv/bin/activate     # LeRobot 0.6.2, editable install at ~/lerobot
source bringup/ports.sh                 # $PHINEAS_PORT / $FERB_PORT

./bringup/view_both.sh                  # both arms, live, in one RViz
./bringup/view_arm.sh /dev/soarm_a      # just Ferb
```

## Why RViz needed building from scratch

LeRobot is not ROS-based; its own visualiser is Rerun. The upstream
[SO-ARM100 repo](https://github.com/TheRobotStudio/SO-ARM100) ships URDFs but no
ROS 2 packages — its entire `Software/` directory is one markdown file about a
web calibration UI. So the bridge, the prefixing, and the launch scripts here are
original work.

## Everything here is read-only

`tools/joint_state_bridge.py` only ever issues Feetech **READ** instructions for
`Present_Position` (address 56). At startup it walks the packet handler and
replaces every `write*`, `syncWrite*`, `regWrite*`, `reboot` and `factoryReset`
method with one that raises, so even a future edit cannot silently start driving
motors. Torque state is left exactly as found.

| Command | Drives motors? |
| --- | --- |
| `tools/identify_arms.py` | No — read-only |
| `bringup/view_arm.sh`, `view_both.sh` | No — writes hard-blocked |
| `lerobot-calibrate` | No — calls `disable_torque()`, you move it by hand |
| `lerobot-teleoperate` | **Yes** |
| `lerobot-record`, `lerobot-replay` | **Yes** |

## How joint angles are computed

Calibration is not primarily a JSON file. `lerobot-calibrate` writes
`Homing_Offset` (addr 31), `Min_Position_Limit` (9) and `Max_Position_Limit` (11)
into each motor's **EEPROM**; the JSON is a copy. This bridge reads calibration
from the motors themselves, so it works on any machine without needing the file.

Matching `lerobot/motors/motors_bus.py::_normalize`:

```
# five body joints — MotorNormMode.DEGREES
mid     = (range_min + range_max) / 2          # NOT 2048
degrees = (raw - mid) * 360 / 4095

# gripper — MotorNormMode.RANGE_0_100
pct     = (clamp(raw) - range_min) / (range_max - range_min) * 100
```

The motor applies `Homing_Offset` itself (`Present_Position = Actual_Position −
Homing_Offset`), so it must **not** be subtracted again in software.

## Joint sign conventions

LeRobot reports each joint in its own convention and the URDF declares its own
axis directions. Where they disagree a joint renders backwards. This cannot be
derived from the data and **calibration does not fix it** - a re-sweep produces
the same mapping. It has to be observed once and recorded.

`bringup/joint_signs.sh` holds the corrections per arm; both launchers apply them
automatically, so there is no flag to remember. Observed so far:

| arm | inverted joints |
| --- | --- |
| Ferb | `wrist_roll` |
| Phineas | none yet |

To test a new one without editing the file, pass `--invert <joints>` explicitly -
that overrides the recorded set for that run.

## Layout

```
bringup/     launch scripts, port definitions, RViz configs
tools/       bridge, URDF prefixer, diagnostics
urdf/        SO-101 URDFs (from SO-ARM100) + STL meshes
  generated/ prefixed URDFs for the dual-arm view (gitignored)
docs/        hardware notes
```

## Host setup

Ubuntu 24.04, ROS 2 Jazzy, Python 3.12.3, LeRobot 0.6.2 (PyTorch 2.11.0+cu128).

Serial access comes from `/etc/udev/rules.d/99-soarm101.rules`, which pins
permissions and creates the `soarm_a` / `soarm_b` symlinks by adapter serial.
`/dev/ttyACM0` and `ttyACM1` are assigned in enumeration order and can swap on
reboot — which would send leader commands to the follower — so nothing here
refers to them directly.
