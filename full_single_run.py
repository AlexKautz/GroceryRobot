#!/usr/bin/env python3
"""
full_single_run.py — Fully automated GroceryRobot launch sequence.
Run via:  bash full_single_run.sh
"""

import datetime
import os
import sys
import time

from launch_lib import (
    NODES,
    _c, BOLD, GREEN, YELLOW, GRAY,
    cleanup, run_teardown,
    wait_for_topic, wait_for_action, gazebo_unpause,
)


def _node(name: str):
    return next(n for n in NODES if n.name == name)


def main() -> None:
    if os.environ.get("ROS_DISTRO") != "kilted":
        print(_c("  WARNING: ROS 2 Kilted not sourced. Run via:  bash full_single_run.sh", YELLOW))
        print()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    active_nodes = []

    print()
    print("=============================================")
    print("  GroceryRobot — Automated Launch")
    print(f"  {timestamp}")
    print("=============================================")
    print()

    run_teardown()

    try:
        sim = _node("Simulation")
        sim.selected = True
        print("  Starting Simulation...")
        sim.start(timestamp)
        active_nodes.append(sim)

        wait_for_topic("/clock", "Gazebo clock", timeout_sec=90)
        print("  Letting controllers settle (5s)...")
        time.sleep(5)

        gazebo_unpause()

        ocl = _node("Overhead Camera Localizer")
        ocl.selected = True
        print("  Starting Overhead Camera Localizer...")
        ocl.start(timestamp)
        active_nodes.append(ocl)

        moveit = _node("MoveIt")
        moveit.selected = True
        print("  Starting MoveIt...")
        moveit.start(timestamp)
        active_nodes.append(moveit)

        wait_for_action("/move_action", "MoveIt /move_action", timeout_sec=90)

        pick = _node("MoveIt Pick from Camera")
        pick.selected = True
        print("  Starting MoveIt Pick from Camera...")
        pick.start(timestamp)
        active_nodes.append(pick)

        print()
        print("=============================================")
        print(_c("  ✓ All nodes running", GREEN))
        print()
        print("  Logs:")
        for n in active_nodes:
            print(f"    {n.name:<32}  {_c(n.log_path.name, GRAY)}")
        print()
        print("  Ctrl+C to stop everything.")
        print("=============================================")
        print()

        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        pass
    finally:
        cleanup(active_nodes)


if __name__ == "__main__":
    main()
