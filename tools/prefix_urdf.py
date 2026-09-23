#!/usr/bin/env python3
"""
Prefix every link and joint name in a URDF.

Showing two arms in one RViz means two robot_state_publishers writing into the
same /tf tree. Both URDFs use the same link names (base_link, shoulder_link...),
so without prefixing the trees collide and the models fight over the same frames.

    prefix_urdf.py in.urdf out.urdf phineas_
"""
import sys
import xml.etree.ElementTree as ET


def main(src, dst, prefix):
    tree = ET.parse(src)
    root = tree.getroot()
    root.set("name", prefix.rstrip("_"))

    # link/joint declarations
    for tag in ("link", "joint"):
        for el in root.findall(tag):
            el.set("name", prefix + el.get("name"))

    # references: joint parent/child links, and mimic joints
    for j in root.findall("joint"):
        for ref in ("parent", "child"):
            e = j.find(ref)
            if e is not None and e.get("link"):
                e.set("link", prefix + e.get("link"))
        m = j.find("mimic")
        if m is not None and m.get("joint"):
            m.set("joint", prefix + m.get("joint"))

    tree.write(dst, xml_declaration=True, encoding="utf-8")
    n_l = len(root.findall("link"))
    n_j = len(root.findall("joint"))
    print(f"{dst}: prefixed {n_l} links and {n_j} joints with '{prefix}'")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:])
