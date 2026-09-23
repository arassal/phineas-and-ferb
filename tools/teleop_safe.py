#!/usr/bin/env python3
"""
Leader-follower teleoperation with a safe start: Phineas -> Ferb.

Two protections the stock lerobot path does not provide.

1. ANTI-SNAP
   SOFollower.configure() wraps its setup in bus.torque_disabled(), and that
   context manager RE-ENABLES torque on exit. In position mode, enabling torque
   makes every motor drive to its stored Goal_Position - which reads 0 after a
   power cycle, i.e. the extreme end of travel. On a 12 V arm that is a hard
   slam on all six joints at once.

   Before connecting, this script writes Goal_Position = Present_Position on
   each follower motor while torque is still OFF. Enabling torque then holds
   position instead of lunging. Nothing moves during the seeding itself,
   because torque is off while it happens.

2. SOFT ALIGNMENT
   The follower is walked to the leader's pose by linear interpolation over
   several seconds, using lerobot's own follower_smooth_move_to - a helper that
   exists in lerobot/common/control_utils.py but which no CLI script calls.
   Without it the first teleop frame jumps the follower straight to the
   leader's pose, however far away that is.

   Upstream tracking issue: https://github.com/huggingface/lerobot/issues/3537
   ("snap the robot directly to the target action, risking a hardware jerk ...
   can damage gears / strain the cable")

Per-step motion is additionally capped through max_relative_target.

Units: body joints are degrees, the gripper is 0-100.
"""

import argparse
import signal
import sys
import time

from scservo_sdk import PacketHandler, PortHandler

ADDR_PRESENT_POSITION = 56
ADDR_GOAL_POSITION = 42
ADDR_TORQUE_ENABLE = 40
BAUD = 1_000_000
MOTOR_IDS = range(1, 7)


def seed_goal_positions(port_name: str) -> bool:
    """Write Goal_Position = Present_Position while torque is off.

    Returns False if any motor is already energised - in that case seeding is
    unsafe to reason about and the caller should stop.
    """
    port = PortHandler(port_name)
    if not port.openPort():
        print(f"[seed] cannot open {port_name}", file=sys.stderr)
        return False
    port.setBaudRate(BAUD)
    ph = PacketHandler(0)

    # A motor that is energised but already sitting at its goal is holding
    # station harmlessly - that is the state seeding produces, and writing
    # Goal_Position on these servos enables torque as a side effect. Only an
    # energised motor being driven somewhere far away is dangerous to touch.
    driving = []
    for mid in MOTOR_IDS:
        tq, c1, e1 = ph.read1ByteTxRx(port, mid, ADDR_TORQUE_ENABLE)
        pos, c2, e2 = ph.read2ByteTxRx(port, mid, ADDR_PRESENT_POSITION)
        goal, c3, e3 = ph.read2ByteTxRx(port, mid, ADDR_GOAL_POSITION)
        if 0 in (c1, c2, c3) and tq == 1 and abs(pos - goal) > 50:
            driving.append((mid, pos, goal))
    if driving:
        print("[seed] REFUSING: these motors are energised and being driven:", file=sys.stderr)
        for mid, pos, goal in driving:
            print(f"[seed]   id {mid}: present={pos} goal={goal} delta={abs(pos - goal)}", file=sys.stderr)
        print("[seed] Power-cycle the arm so it is limp, then retry.", file=sys.stderr)
        port.closePort()
        return False

    seeded, failed = [], []
    for mid in MOTOR_IDS:
        pos, comm, err = ph.read2ByteTxRx(port, mid, ADDR_PRESENT_POSITION)
        if comm != 0 or err != 0:
            failed.append(mid)
            continue
        # write*TxRx returns (comm_result, error), unlike read* which returns
        # (data, comm_result, error).
        comm, err = ph.write2ByteTxRx(port, mid, ADDR_GOAL_POSITION, pos)
        (seeded if (comm == 0 and err == 0) else failed).append(mid)

    port.closePort()
    if failed:
        print(f"[seed] FAILED on ids {failed} - those joints may still lunge.", file=sys.stderr)
        return False
    print(f"[seed] Goal_Position seeded to Present_Position on {len(seeded)}/6 motors")
    return True


# URDF revolute limits, radians - the gripper needs its 0-100 range mapped onto
# these; body joints come out of lerobot in degrees already.
_URDF_GRIPPER = (-0.174533, 1.74533)


class _RosPublisher:
    """Publish both arms' joint states so RViz can render them during teleop.

    Lives inside this process because teleop holds both serial ports; the
    standalone read-only bridge cannot open them at the same time. Joint names
    are prefixed to match the prefixed URDFs used by the dual-arm view.
    """

    def __init__(self):
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import JointState

        self._rclpy = rclpy
        self._JointState = JointState
        rclpy.init(args=None)
        self.node = Node("teleop_joint_state_publisher")
        self.pub_leader = self.node.create_publisher(JointState, "/phineas/joint_states", 10)
        self.pub_follower = self.node.create_publisher(JointState, "/ferb/joint_states", 10)
        print("[ros] publishing /phineas/joint_states and /ferb/joint_states")

    def _msg(self, prefix, action):
        import math

        msg = self._JointState()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        for key, val in action.items():
            joint = key.removesuffix(".pos")
            if joint == "gripper":
                lo, hi = _URDF_GRIPPER
                rad = lo + (max(0.0, min(100.0, val)) / 100.0) * (hi - lo)
            else:
                rad = math.radians(val)
            msg.name.append(prefix + joint)
            msg.position.append(rad)
        return msg

    def publish(self, leader_action, follower_obs):
        self.pub_leader.publish(self._msg("phineas_", leader_action))
        self.pub_follower.publish(self._msg("ferb_", follower_obs))

    def shutdown(self):
        try:
            self.node.destroy_node()
        finally:
            self._rclpy.try_shutdown()


class _Stop(Exception):
    """Raised from a SIGTERM handler so the finally block still runs."""


def _on_sigterm(_signum, _frame):
    raise _Stop()


def main():
    # Without this, `kill` terminates the process before the finally block runs
    # and the follower is left energised and rigid. Turning SIGTERM into an
    # exception lets the normal shutdown path release torque.
    signal.signal(signal.SIGTERM, _on_sigterm)

    ap = argparse.ArgumentParser()
    ap.add_argument("--leader-port", default="/dev/soarm_b")
    ap.add_argument("--follower-port", default="/dev/soarm_a")
    ap.add_argument("--leader-id", default="phineas")
    ap.add_argument("--follower-id", default="ferb")
    ap.add_argument("--align-seconds", type=float, default=8.0,
                    help="how long to take walking the follower to the leader's pose")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--max-step", type=float, default=5.0,
                    help="max per-step motion (degrees, or gripper percent)")
    ap.add_argument("--publish-ros", action="store_true",
                    help="also publish /phineas/joint_states and /ferb/joint_states for RViz. "
                         "Needed because teleop owns both serial ports, so the standalone "
                         "read-only bridge cannot run at the same time.")
    ap.add_argument("--keep-cap", action="store_true",
                    help="keep max_relative_target during following (default: drop it once aligned)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report how far apart the arms are, then stop without moving anything")
    a = ap.parse_args()

    pub = None
    if a.publish_ros:
        pub = _RosPublisher()

    from lerobot.common.control_utils import follower_smooth_move_to
    from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig
    from lerobot.teleoperators.so_leader import SOLeader, SOLeaderTeleopConfig

    robot = SOFollower(SOFollowerRobotConfig(
        port=a.follower_port, id=a.follower_id, max_relative_target=a.max_step))
    teleop = SOLeader(SOLeaderTeleopConfig(port=a.leader_port, id=a.leader_id))

    # Seeding must happen immediately before connect, and the arm must not be
    # moved in between: the seed records where each joint IS, and connect()
    # enables torque, which drives to whatever goal was last written. If the
    # arm is moved after seeding, that goal is stale and the joint lunges.
    # lerobot's handshake also does not retry, so a single dropped packet
    # aborts the connect - hence the retry, which re-seeds each attempt.
    print("[connect] DO NOT MOVE FERB until alignment finishes.")
    last_err = None
    for attempt in range(1, 4):
        if not seed_goal_positions(a.follower_port):
            return 1
        try:
            print(f"[connect] follower (attempt {attempt}/3; torque enables, held at present position)...")
            robot.connect()
            last_err = None
            break
        except Exception as e:
            last_err = e
            msg = str(e).splitlines()[0]
            print(f"[connect] attempt {attempt} failed: {msg}", file=sys.stderr)
            time.sleep(0.5)
    if last_err is not None:
        print("[connect] giving up after 3 attempts.", file=sys.stderr)
        return 1
    print("[connect] leader (stays limp, backdrivable)...")
    teleop.connect()

    try:
        current = {k: v for k, v in robot.get_observation().items() if k.endswith(".pos")}
        target = teleop.get_action()

        print("\n  joint              Ferb      Phineas    difference")
        print("  " + "-" * 52)
        worst = 0.0
        for k in sorted(current):
            if k in target:
                d = target[k] - current[k]
                worst = max(worst, abs(d))
                print(f"  {k.removesuffix('.pos'):<16} {current[k]:>8.2f} {target[k]:>10.2f} {d:>12.2f}")
        print(f"\n  largest difference: {worst:.2f}")

        if a.dry_run:
            print("\n[dry-run] nothing moved. Re-run without --dry-run to align and teleoperate.")
            return 0

        rate = worst / a.align_seconds if a.align_seconds else float("inf")
        print(f"\n[align] walking Ferb to Phineas over {a.align_seconds:.1f}s "
              f"(~{rate:.1f} units/s on the worst joint)")
        print("[align] keep hands clear; Ferb is moving now.")
        follower_smooth_move_to(robot, current, target, duration_s=a.align_seconds, fps=int(a.fps))
        print("[align] done - arms are matched.")

        if not a.keep_cap:
            # The cap exists to protect the alignment move. Once the arms match,
            # the leader is moved by hand so step sizes are inherently bounded,
            # and the cap only adds lag. It also costs an extra Present_Position
            # read per cycle - send_action only reads the follower back when
            # max_relative_target is set - so dropping it speeds up the loop too.
            robot.config.max_relative_target = None
            print("\n[teleop] per-step cap released - tracking is now 1:1")
        cap = a.max_step if a.keep_cap else "none"
        print(f"[teleop] following at {a.fps:.0f} Hz, cap {cap}. Ctrl-C to stop.\n")
        period = 1.0 / a.fps
        n = 0
        while True:
            t0 = time.perf_counter()
            leader_action = teleop.get_action()
            robot.send_action(leader_action)
            if pub is not None:
                follower_obs = {k: v for k, v in robot.get_observation().items()
                                if k.endswith(".pos")}
                pub.publish(leader_action, follower_obs)
            n += 1
            if n % 60 == 0:
                print(f"\r  frames: {n}", end="", flush=True)
            dt = period - (time.perf_counter() - t0)
            if dt > 0:
                time.sleep(dt)
    except (KeyboardInterrupt, _Stop):
        print("\n[teleop] stopping.")
    finally:
        # disable_torque_on_disconnect defaults True, so Ferb goes limp here.
        print("[shutdown] disconnecting; Ferb's torque will be released.")
        try:
            if pub is not None:
                pub.shutdown()
        finally:
            try:
                teleop.disconnect()
            finally:
                robot.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
