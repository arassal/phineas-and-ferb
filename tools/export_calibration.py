#!/usr/bin/env python3
"""
Reconstruct a LeRobot calibration JSON by reading it back out of motor EEPROM.

lerobot-calibrate writes the real calibration into each motor (Homing_Offset,
Min_Position_Limit, Max_Position_Limit) and mirrors it to a JSON file. If that
file is lost - cleared cache, new machine, arm calibrated elsewhere - the data
is still on the arm and can be recovered without another hands-on sweep.

READ-ONLY: only issues READ instructions. Never writes, never enables torque.

    ./tools/export_calibration.py /dev/soarm_a ferb > calibration/ferb.json
"""
import argparse
import json
import sys

from scservo_sdk import PacketHandler, PortHandler

BAUD = 1_000_000
ADDR = {"min_pos": 9, "max_pos": 11, "homing": 31}
JOINTS = {1: "shoulder_pan", 2: "shoulder_lift", 3: "elbow_flex",
          4: "wrist_flex", 5: "wrist_roll", 6: "gripper"}
SIGN_BIT = 11  # Homing_Offset is sign-magnitude encoded on protocol 0


def decode_sign(v, bit=SIGN_BIT):
    return -(v & ~(1 << bit)) if v >> bit & 1 else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("name", help="arm id, e.g. ferb")
    a = ap.parse_args()

    p = PortHandler(a.port)
    if not p.openPort():
        print(f"cannot open {a.port}", file=sys.stderr)
        return 1
    p.setBaudRate(BAUD)
    ph = PacketHandler(0)

    out, missing, uncal = {}, [], []
    for mid, joint in JOINTS.items():
        lo, c1, _ = ph.read2ByteTxRx(p, mid, ADDR["min_pos"])
        hi, c2, _ = ph.read2ByteTxRx(p, mid, ADDR["max_pos"])
        hm, c3, _ = ph.read2ByteTxRx(p, mid, ADDR["homing"])
        # comm result 0 == success. ANY failure means the values are garbage.
        if any(c != 0 for c in (c1, c2, c3)):
            missing.append(joint)
            continue
        if (lo, hi) == (0, 4095) and joint != "wrist_roll":
            uncal.append(joint)
        out[joint] = {
            "id": mid,
            "drive_mode": 0,
            "homing_offset": decode_sign(hm),
            "range_min": lo,
            "range_max": hi,
        }
    p.closePort()

    if missing:
        print(f"WARNING: no response from {missing} - export is incomplete", file=sys.stderr)
    if uncal:
        print(f"WARNING: {uncal} still have factory-default ranges - not calibrated", file=sys.stderr)
    if not out:
        print("nothing read; is the arm powered?", file=sys.stderr)
        return 1

    print(json.dumps(out, indent=4))
    print(f"exported {len(out)}/6 joints for '{a.name}'", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
