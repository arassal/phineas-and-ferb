#!/usr/bin/env python3
"""
Identify which port is the LEADER and which is the FOLLOWER.

READ-ONLY: never enables torque, never commands motion. Reads Present_Position
(addr 56) from ids 1-6 on each bus, then watches for movement.

Usage: identify_arms.py [--seconds 60] [ports...]
"""
import argparse, sys, time
from scservo_sdk import PacketHandler, PortHandler

BAUD, PRESENT_POSITION = 1_000_000, 56
IDS = [1, 2, 3, 4, 5, 6]
NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
THRESH = 30  # raw counts (~2.6 deg) to count as deliberate movement


def read_all(port, ph):
    out = {}
    for mid in IDS:
        pos, comm, err = ph.read2ByteTxRx(port, mid, PRESENT_POSITION)
        out[mid] = pos if comm == 0 and err == 0 else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("ports", nargs="*", default=["/dev/soarm_a", "/dev/soarm_b"])
    a = ap.parse_args()

    buses = {}
    for dev in a.ports:
        try:
            p = PortHandler(dev)
            if not p.openPort():
                print(f"[!] {dev}: cannot open"); continue
            p.setBaudRate(BAUD)
            buses[dev] = (p, PacketHandler(0))
        except Exception as e:
            print(f"[!] {dev}: {e}")
    if len(buses) < 2:
        print(f"Need 2 buses, opened {len(buses)}.")
        return 1

    print("=" * 74)
    print("BASELINE")
    base = {}
    for dev, (p, ph) in buses.items():
        base[dev] = read_all(p, ph)
        live = sum(1 for v in base[dev].values() if v is not None)
        vals = "  ".join(f"{NAMES[m-1][:9]}={'----' if v is None else v}" for m, v in base[dev].items())
        print(f"  {dev}  [{live}/6]  {vals}")

    print("=" * 74)
    print(f"Watching {a.seconds:.0f}s for hand movement...")

    # track cumulative absolute travel per bus, and peak deviation from baseline
    travel = {d: 0 for d in buses}
    peak = {d: 0 for d in buses}
    prev = {d: dict(base[d]) for d in buses}
    deadline = time.time() + a.seconds
    while time.time() < deadline:
        for dev, (p, ph) in buses.items():
            now = read_all(p, ph)
            for mid in IDS:
                pv, nv, bv = prev[dev][mid], now[mid], base[dev][mid]
                if pv is not None and nv is not None:
                    d = abs(nv - pv)
                    if THRESH < d < 2000:       # ignore noise and 0/4095 wraparound
                        travel[dev] += d
                if bv is not None and nv is not None:
                    dev_from_base = abs(nv - bv)
                    if dev_from_base < 2000:
                        peak[dev] = max(peak[dev], dev_from_base)
                if nv is not None:
                    prev[dev][mid] = nv
        time.sleep(0.05)

    print("=" * 74)
    for dev in buses:
        print(f"  {dev}:  cumulative travel={travel[dev]:6d}   peak deviation={peak[dev]:5d}")
    print("=" * 74)

    ranked = sorted(travel.items(), key=lambda kv: kv[1], reverse=True)
    top, second = ranked[0], ranked[1]
    if top[1] < 200:
        print("RESULT: no clear movement detected. Nothing identified.")
        print("        Re-run and move one arm further.")
        rc = 2
    elif top[1] < second[1] * 3:
        print("RESULT: AMBIGUOUS - both buses moved similar amounts.")
        print("        Re-run and move ONLY the leader arm.")
        rc = 2
    else:
        print(f"LEADER   (moved by hand) : {top[0]}")
        print(f"FOLLOWER (stayed still)  : {second[0]}")
        rc = 0

    for p, _ in buses.values():
        p.closePort()
    return rc


if __name__ == "__main__":
    sys.exit(main())
