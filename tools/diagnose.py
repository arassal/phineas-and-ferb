#!/usr/bin/env python3
"""
Health check for both arms. READ-ONLY — never writes, never energises.

Reports per motor: ping, model, position, voltage vs its own limit, temperature,
error flags, EEPROM calibration range, and read reliability over N samples.

    ./tools/diagnose.py [--samples 20] [ports...]
"""
import argparse
import sys

from scservo_sdk import PacketHandler, PortHandler

BAUD = 1_000_000
A = dict(MIN_POS=9, MAX_POS=11, MAX_VOLT=14, MIN_VOLT=15, HOMING=31,
         TORQUE=40, PRESENT=56, VOLT=62, TEMP=63, STATUS=65, MODEL=3)
NAMES = {1: "shoulder_pan", 2: "shoulder_lift", 3: "elbow_flex",
         4: "wrist_flex", 5: "wrist_roll", 6: "gripper"}
FLAGS = ["voltage", "angle", "overheat", "overele", "?", "overload", "?", "?"]


def decode_sign(v, bit=11):
    return -(v & ~(1 << bit)) if v >> bit & 1 else v


def flags(b):
    if not b:
        return "ok"
    return "|".join(n for i, n in enumerate(FLAGS) if b >> i & 1) or f"raw{b}"


def diagnose(dev, samples):
    print("=" * 100)
    print(dev)
    try:
        p = PortHandler(dev)
        if not p.openPort():
            print("  cannot open (permissions? see udev rule)"); return
        p.setBaudRate(BAUD)
    except Exception as e:
        print(f"  {e}"); return
    ph = PacketHandler(0)

    hdr = f"{'id':>3} {'name':<14} {'pos':>6} {'volt':>6} {'maxV':>5} {'temp':>5} {'err':>9} {'range':>13} {'reads':>8}"
    print(hdr); print("-" * 100)
    problems = []
    for mid, name in NAMES.items():
        _, pc, _ = ph.ping(p, mid)
        if pc != 0:
            print(f"{mid:>3} {name:<14} {'NO PING — motor absent or wrong id':<70}")
            problems.append(f"{name}: no ping")
            continue
        pos, c, e = ph.read2ByteTxRx(p, mid, A["PRESENT"])
        v, _, _ = ph.read1ByteTxRx(p, mid, A["VOLT"])
        mv, _, _ = ph.read1ByteTxRx(p, mid, A["MAX_VOLT"])
        t, _, _ = ph.read1ByteTxRx(p, mid, A["TEMP"])
        lo, _, _ = ph.read2ByteTxRx(p, mid, A["MIN_POS"])
        hi, _, _ = ph.read2ByteTxRx(p, mid, A["MAX_POS"])
        ok = sum(1 for _ in range(samples)
                 if ph.read2ByteTxRx(p, mid, A["PRESENT"])[1:] == (0, 0))
        poss = str(pos) if (c == 0 and e == 0) else "ERR"
        rng = f"[{lo},{hi}]"
        # wrist_roll is legitimately set to the full turn by lerobot-calibrate,
        # so [0,4095] there is calibrated, not default.
        cal = " *uncal" if (lo, hi) == (0, 4095) and name != "wrist_roll" else ""
        print(f"{mid:>3} {name:<14} {poss:>6} {v/10:>6.1f} {mv/10:>5.1f} {t:>5} {flags(e):>9} {rng:>13}{cal} {ok:>3}/{samples}")
        if e:
            problems.append(f"{name}: {flags(e)} (present {v/10:.1f} V vs limit {mv/10:.1f} V)")
        if ok < samples:
            problems.append(f"{name}: only {ok}/{samples} reads succeeded")
    print()
    if problems:
        print("  PROBLEMS:")
        for x in problems:
            print(f"    - {x}")
    else:
        print("  all motors healthy")
    p.closePort()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=20)
    ap.add_argument("ports", nargs="*", default=["/dev/soarm_b", "/dev/soarm_a"])
    a = ap.parse_args()
    print("* = factory-default range, i.e. never calibrated\n")
    for d in a.ports:
        diagnose(d, a.samples)
    sys.exit(0)
