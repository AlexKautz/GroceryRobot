#!/usr/bin/env python3
"""
launch.py — GroceryRobot interactive launch manager.
Run via:  bash launch.sh
"""

import datetime
import json
import os
import sys
import time

from launch_lib import (
    REPO_DIR, PREFS_FILE,
    RED, GREEN, YELLOW, CYAN, GRAY, BOLD, RESET, CLEAR,
    _c, _vlen, _pad,
    NodeEntry, NODES,
    load_prefs, save_node_prefs,
    run_teardown, run_setup,
    stage_dashboard,
)


# ─── Stage 0: Rebuild prompt (was in launch.sh) ───────────────────────────────

def stage_rebuild() -> None:
    last = "s" if load_prefs().get("rebuild", False) else "skip"
    print(_c("═" * 54, BOLD))
    print(_c("  GroceryRobot — Startup", BOLD))
    print(_c("═" * 54, BOLD))
    print()
    try:
        choice = input(
            f"  Rebuild workspace? [s = run setup.sh, Enter = skip]  (last: {last}): "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)
    print()
    if choice == "s":
        run_setup()
        prefs = load_prefs()
        prefs["rebuild"] = True
    else:
        print("  Skipping rebuild.")
        prefs = load_prefs()
        prefs["rebuild"] = False
    PREFS_FILE.write_text(json.dumps(prefs, indent=2))


# ─── Stage 1: Node selection ──────────────────────────────────────────────────

def stage_selection(nodes: list[NodeEntry]) -> None:
    node_prefs = load_prefs().get("nodes", {})
    for node in nodes:
        if node.name in node_prefs:
            node.selected = node_prefs[node.name].get("selected", node.selected)
            node.mode     = node_prefs[node.name].get("mode",     node.mode)

    while True:
        print(CLEAR, end="")
        print(_c("═" * 54, BOLD))
        print(_c("  GroceryRobot — Node Selection", BOLD))
        print(_c("═" * 54, BOLD))
        print()
        print(_c("  Controls:", BOLD))
        print(f"    {_c('1-9', CYAN)}      toggle node(s) on / off  (e.g. {_c('145', CYAN)} toggles 1, 4 and 5)")
        print(f"    {_c('m<n>', CYAN)}     flip start mode  (e.g. {_c('m2', CYAN)} flips node 2)")
        print(f"           {_c('auto', CYAN)} = starts immediately   {_c('manual', YELLOW)} = you trigger it from the dashboard")
        print(f"    {_c('Enter', CYAN)}    confirm selection and launch")
        print(f"    {_c('q', CYAN)}        quit")
        print()
        for i, node in enumerate(nodes, 1):
            check    = _c("x", GREEN) if node.selected else " "
            mode_tag = _c(f"[{node.mode}]", CYAN if node.mode == "auto" else YELLOW)
            print(f"  [{check}] {i}.  {node.name:<32}  {mode_tag}")
        print()
        try:
            raw = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)

        if raw in ("q", "quit"):
            sys.exit(0)
        elif raw == "":
            if any(n.selected for n in nodes):
                save_node_prefs(nodes)
                return
            print(_c("  Select at least one node.", RED))
            time.sleep(1.0)
        elif len(raw) == 2 and raw[0] == "m" and raw[1].isdigit():
            idx = int(raw[1]) - 1
            if 0 <= idx < len(nodes):
                nodes[idx].mode = "manual" if nodes[idx].mode == "auto" else "auto"
        elif raw.isdigit():
            for ch in raw:
                idx = int(ch) - 1
                if 0 <= idx < len(nodes):
                    nodes[idx].selected = not nodes[idx].selected


# ─── Stage 2: Launch ──────────────────────────────────────────────────────────

def stage_launch(nodes: list[NodeEntry], timestamp: str) -> None:
    print(CLEAR, end="")
    print(_c("═" * 54, BOLD))
    print(_c("  GroceryRobot — Launching", BOLD))
    print(_c("═" * 54, BOLD))
    print()

    for node in nodes:
        if not node.selected:
            continue
        if node.mode == "manual":
            print(f"  {node.name:<34}  {_c('queued  (press key in dashboard to start)', YELLOW)}")
            continue
        node.start(timestamp)
        print(f"  {node.name:<34}  {_c('started', GREEN)}  →  {_c(node.log_path.name, GRAY)}")

    print()
    print("  Entering dashboard in 2 seconds...")
    time.sleep(2.0)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if os.environ.get("ROS_DISTRO") != "kilted":
        print(_c("  WARNING: ROS 2 Kilted not sourced. Run via:  bash launch.sh", YELLOW))
        print()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    stage_rebuild()
    stage_selection(NODES)
    run_teardown()
    stage_launch(NODES, timestamp)
    stage_dashboard(NODES, timestamp)


if __name__ == "__main__":
    main()
