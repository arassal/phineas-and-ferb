#!/usr/bin/env python3
"""
Read-only ROS 2 bridge: SO-ARM101 encoders -> /joint_states, for RViz.

SAFETY
------
Incapable of moving the arm. Only issues Feetech READ instructions, and on
startup replaces every write*/syncWrite*/regWrite*/reboot/factoryReset method
on the packet handler with one that raises. Torque state is left as found.

ANGLE CONVENTION (matches lerobot/src/lerobot/motors/motors_bus.py::_normalize)
------------------------------------------------------------------------------
Calibration lives in each motor's EEPROM, written by `lerobot-calibrate`:
    Homing_Offset          (addr 31) - the motor itself applies this, so
                                       Present_Position is ALREADY homed.
                                       Do NOT subtract it again.
    Min_Position_Limit     (addr  9)
    Max_Position_Limit     (addr 11)

For the 5 body joints (MotorNormMode.DEGREES):
    mid     = (range_min + range_max) / 2
    degrees = (raw - mid) * 360 / (resolution - 1)      # resolution-1 = 4095
    radians = degrees * pi / 180

For the gripper (MotorNormMode.RANGE_0_100):
    pct = (clamp(raw) - range_min) / (range_max - range_min) * 100
    then mapped linearly onto the URDF gripper joint limits.
"""

import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from scservo_sdk import PacketHandler, PortHandler
from sensor_msgs.msg import JointState

BAUD = 1_000_000
ADDR_MIN_POS, ADDR_MAX_POS, ADDR_PRESENT_POS = 9, 11, 56
MAX_RES = 4095  # resolution - 1, per model_resolution_table for sts3215

JOINTS = {
    1: "shoulder_pan",
    2: "shoulder_lift",
    3: "elbow_flex",
    4: "wrist_flex",
    5: "wrist_roll",
    6: "gripper",
}

# URDF revolute limits (so101_new_calib.urdf), radians
URDF_LIMITS = {
    "shoulder_pan": (-1.91986, 1.91986),
    "shoulder_lift": (-1.74533, 1.74533),
    "elbow_flex": (-1.69, 1.69),
    "wrist_flex": (-1.65806, 1.65806),
    "wrist_roll": (-2.74385, 2.84121),
    "gripper": (-0.174533, 1.74533),
}


def _forbid_writes(handler):
    def blocked(name):
        def _raise(*_a, **_k):
            raise RuntimeError(f"BLOCKED: {name}() - this bridge is read-only.")

        return _raise

    for attr in dir(handler):
        if attr.startswith(("write", "syncWrite", "regWrite")) or attr in {"reboot", "factoryReset"}:
            try:
                setattr(handler, attr, blocked(attr))
            except AttributeError:
                pass
    return handler


class JointStateBridge(Node):
    def __init__(self, port_name, rate_hz, invert, clamp, prefix=""):
        super().__init__("soarm101_joint_state_bridge")
        self.prefix = prefix
        self.invert = invert
        self.clamp = clamp

        self.port = PortHandler(port_name)
        if not self.port.openPort():
            raise RuntimeError(f"could not open {port_name}")
        if not self.port.setBaudRate(BAUD):
            raise RuntimeError(f"could not set baudrate {BAUD}")
        self.ph = _forbid_writes(PacketHandler(0))

        # Pull calibration from the motors themselves - the source of truth.
        self.rng = {}
        log = self.get_logger()
        log.info("reading calibration from motor EEPROM:")
        for mid, name in JOINTS.items():
            lo, c1, e1 = self.ph.read2ByteTxRx(self.port, mid, ADDR_MIN_POS)
            hi, c2, e2 = self.ph.read2ByteTxRx(self.port, mid, ADDR_MAX_POS)
            if c1 == 0 and c2 == 0 and hi != lo:
                self.rng[name] = (lo, hi)
                log.info(f"  {name:<14} range=[{lo:4d},{hi:4d}] mid={(lo + hi) / 2:6.1f}")
            else:
                self.rng[name] = None
                log.warn(f"  {name:<14} NO CALIBRATION READABLE - falling back to raw centre 2048")

        if all(v is None for v in self.rng.values()):
            log.warn("No calibration found on any motor. Run lerobot-calibrate; angles will be approximate.")

        self.pub = self.create_publisher(JointState, "joint_states", 10)
        self.create_timer(1.0 / rate_hz, self.tick)
        self.last = dict.fromkeys(JOINTS.values(), 0.0)
        self.warned_limit = set()
        log.info(f"READ-ONLY bridge up on {port_name} at {rate_hz} Hz. Motors will not move.")

    def convert(self, name, raw):
        rng = self.rng.get(name)
        lo, hi = rng if rng else (0, MAX_RES)
        if name == "gripper":
            pct = (min(hi, max(lo, raw)) - lo) / (hi - lo) * 100.0
            ulo, uhi = URDF_LIMITS[name]
            val = ulo + (pct / 100.0) * (uhi - ulo)
        else:
            mid = (lo + hi) / 2.0
            val = math.radians((raw - mid) * 360.0 / MAX_RES)
        if self.invert.get(name):
            val = -val
        if self.clamp:
            ulo, uhi = URDF_LIMITS[name]
            if not (ulo <= val <= uhi) and name not in self.warned_limit:
                self.warned_limit.add(name)
                self.get_logger().warn(
                    f"{name}: {val:+.3f} rad is outside URDF limits [{ulo:+.3f},{uhi:+.3f}] - clamping. "
                    "Usually means the joint is resting against its hard stop, or needs recalibration."
                )
            val = min(uhi, max(ulo, val))
        return val

    def tick(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        ok = 0
        for mid, name in JOINTS.items():
            raw, comm, err = self.ph.read2ByteTxRx(self.port, mid, ADDR_PRESENT_POS)
            if comm == 0 and err == 0:
                self.last[name] = self.convert(name, raw)
                ok += 1
            msg.name.append(self.prefix + name)
            msg.position.append(self.last[name])
        self.pub.publish(msg)
        if ok == 0:
            self.get_logger().warn("no motors responding", throttle_duration_sec=5.0)

    def destroy_node(self):
        try:
            self.port.closePort()
        finally:
            super().destroy_node()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--rate", type=float, default=30.0)
    ap.add_argument(
        "--invert",
        default="",
        help="comma-separated joints whose direction is flipped vs the URDF, "
        "e.g. --invert shoulder_lift,elbow_flex",
    )
    ap.add_argument("--no-clamp", action="store_true", help="do not clamp to URDF joint limits")
    ap.add_argument("--prefix", default="", help="joint-name prefix, must match the prefixed URDF")
    # Strip ROS args (--ros-args -r ...) before argparse sees them, and hand
    # the full argv to rclpy so remaps like -r __node:= still apply.
    a = ap.parse_args(rclpy.utilities.remove_ros_args(sys.argv)[1:])

    invert = {n.strip(): True for n in a.invert.split(",") if n.strip()}
    bad = set(invert) - set(JOINTS.values())
    if bad:
        print(f"unknown joint(s) in --invert: {sorted(bad)}", file=sys.stderr)
        return 2

    rclpy.init(args=sys.argv)
    node = JointStateBridge(a.port, a.rate, invert, not a.no_clamp, a.prefix)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
