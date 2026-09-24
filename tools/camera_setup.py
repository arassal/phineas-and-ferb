#!/usr/bin/env python3
"""
Diagnostic: check a UVC camera and reset its controls to sane values.

DO NOT run this immediately before lerobot opens the camera. lerobot
configures the device correctly by itself, and opening/releasing it just
beforehand leaves it unable to read - lerobot's background read thread then
fails with "read failed (status=False)" and dies.

Use it on its own, to answer "is this camera actually producing an image?":

    ./tools/camera_setup.py /dev/video4

It reports mean and standard deviation of one frame. A very low standard
deviation means a featureless frame, which is what a lens cover looks like -
and is indistinguishable from broken hardware without this check.

It also restores auto-exposure and neutral gain, which matters because UVC
control values live on the camera and persist across open/close, across
processes, and until it is unplugged. So a session that forces manual exposure
or high gain to diagnose something leaves the image wrong for every session
afterwards.
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
