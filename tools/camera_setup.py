#!/usr/bin/env python3
"""
Put a UVC camera's controls into a sane state before lerobot opens it.

Why this exists: UVC control values live on the device and persist across
open/close, and across processes, until it is unplugged. The Innomaker
U20CAM-1080p on this rig was found with BRIGHTNESS=0, which produces a
completely black frame at every resolution and format - easily mistaken for a
broken camera. Conversely, forcing manual exposure with high gain leaves the
image blown out for every later session.

lerobot's OpenCVCameraConfig does not expose brightness/gain/exposure, so this
runs first and leaves the device on auto-exposure with neutral gain.

    ./tools/camera_setup.py /dev/video4
"""

import sys

import cv2

# Values the device reported before anything touched it; auto-exposure on.
DEFAULTS = [
    (cv2.CAP_PROP_AUTO_EXPOSURE, 3),   # 3 = aperture priority / auto on UVC
    (cv2.CAP_PROP_BRIGHTNESS, 0),
    (cv2.CAP_PROP_GAIN, 0),
    (cv2.CAP_PROP_CONTRAST, 32),
    (cv2.CAP_PROP_SATURATION, 64),
    (cv2.CAP_PROP_AUTO_WB, 1),
]


def main(device):
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"[camera_setup] cannot open {device}", file=sys.stderr)
        return 1
    for prop, val in DEFAULTS:
        cap.set(prop, val)
    # Let auto-exposure converge, otherwise the first frames lerobot sees are dark.
    for _ in range(30):
        cap.read()
    ok, frame = cap.read()
    if ok and frame is not None:
        mean, std = float(frame.mean()), float(frame.std())
        print(f"[camera_setup] {device}: mean={mean:.1f} std={std:.1f}", end="")
        if std < 5:
            print("  WARNING: frame is nearly featureless - lens cover still on?")
        else:
            print("  looks like a real image")
    else:
        print(f"[camera_setup] {device}: could not read a frame", file=sys.stderr)
    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/dev/video4"))
