#!/usr/bin/env python3
"""
launch.py — GroceryRobot launch manager.
Run via:  bash launch.sh
"""

import dataclasses
import datetime
import json
import os
import pathlib
import re
import select
import subprocess
import sys
import signal
import termios
import time
import tty
from typing import Optional


# ─── Paths ────────────────────────────────────────────────────────────────────

REPO_DIR  = pathlib.Path(__file__).parent.resolve()
LOGS_DIR  = REPO_DIR / "logs"
PREFS_FILE = REPO_DIR / "launch_prefs.json"


# ─── Preferences ──────────────────────────────────────────────────────────────

def _load_prefs() -> dict:
    try:
        return json.loads(PREFS_FILE.read_text())
    except Exception:
        return {}

def _save_node_prefs(nodes: list) -> None:
    prefs = _load_prefs()
    prefs["nodes"] = {n.name: {"selected": n.selected, "mode": n.mode} for n in nodes}
    PREFS_FILE.write_text(json.dumps(prefs, indent=2))


# ─── ANSI helpers ─────────────────────────────────────────────────────────────

RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CLEAR  = "\033[2J\033[H"

def _c(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"

def _vlen(s: str) -> int:
    """Visible length of a string (strips ANSI escape codes)."""
    return len(re.sub(r'\033\[[0-9;]*m', '', s))

def _pad(s: str, width: int) -> str:
    """Pad a (possibly ANSI-colored) string to a visible width."""
    return s + " " * max(0, width - _vlen(s))


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclasses.dataclass
class NodeEntry:
    name: str
    command: str
    selected: bool = False
    mode: str = "auto"                  # 'auto' | 'manual'
    process: Optional[subprocess.Popen] = dataclasses.field(default=None, repr=False)
    log_path: Optional[pathlib.Path]    = dataclasses.field(default=None)
    log_file: Optional[object]          = dataclasses.field(default=None, repr=False)
    started_at: Optional[float]         = dataclasses.field(default=None)

    def status_str(self) -> str:
        if self.process is None:
            if self.selected and self.mode == "manual":
                return _c("waiting", YELLOW)
            return _c("—", GRAY)
        code = self.process.poll()
        if code is None:
            return _c("running", GREEN)
        elapsed = time.monotonic() - self.started_at if self.started_at else 999.0
        if code != 0 and elapsed < 5.0:
            return _c(f"CRASHED (exit {code})", RED)
        return _c(f"done ({code})", GRAY)

    def is_early_crash(self) -> bool:
        if self.process is None or self.started_at is None:
            return False
        code = self.process.poll()
        return (code is not None and code != 0
                and time.monotonic() - self.started_at < 5.0)

    def start(self, timestamp: str) -> None:
        LOGS_DIR.mkdir(exist_ok=True)
        slug = self.name.lower().replace(" ", "_")
        self.log_path = LOGS_DIR / f"{slug}_{timestamp}.log"
        self.log_file = open(self.log_path, "w")
        self.process = subprocess.Popen(
            self.command,
            shell=True,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,   # own process group → killpg reaches all descendants
        )
        self.started_at = time.monotonic()

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        if self.log_file:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None


# ─── Node definitions ─────────────────────────────────────────────────────────

NODES: list[NodeEntry] = [
    NodeEntry("Simulation",                "ros2 launch ur3e_gazebo ur3e_gazebo.launch.py"),
    NodeEntry("Pick and Place",            "ros2 run ur3e_gazebo pick_and_place",             mode="manual"),
    NodeEntry("Arm Camera Localizer",      "ros2 run ur3e_gazebo arm_camera_localizer"),
    NodeEntry("Overhead Camera Localizer", "ros2 run ur3e_gazebo overhead_camera_localizer"),
    NodeEntry("Joint Control Panel",       "ros2 run ur3e_gazebo joint_control_panel"),
    NodeEntry("Image Viewer",              "QT_QPA_PLATFORM=xcb ros2 run rqt_image_view rqt_image_view /overhead_camera/annotated_image"),
    NodeEntry("MoveIt Pick from Camera",   "ros2 launch ur3e_gazebo moveit_pick_from_camera.launch.py", mode="manual"),
    NodeEntry("MoveIt",                    "ros2 launch ur3e_moveit_config move_group.launch.py",         mode="manual"),
]


# ─── Terminal input ───────────────────────────────────────────────────────────


def read_key(timeout: float = 2.0) -> Optional[str]:
    """
    Wait up to `timeout` seconds for a single keypress.
    Returns the character, or None on timeout.
    In raw mode, Ctrl-C arrives as '\\x03' instead of raising KeyboardInterrupt.
    """
    if not sys.stdin.isatty():
        time.sleep(timeout)
        return None
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            return sys.stdin.read(1)
        return None
    except Exception:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ─── Stage 1: Node selection ──────────────────────────────────────────────────

def stage_selection(nodes: list[NodeEntry]) -> None:
    node_prefs = _load_prefs().get("nodes", {})
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
        print(f"    {_c('1-6', CYAN)}      toggle node(s) on / off  (e.g. {_c('145', CYAN)} toggles 1, 4 and 5)")
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
                _save_node_prefs(nodes)
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


# ─── Stage 4: Dashboard ───────────────────────────────────────────────────────

def draw_dashboard(nodes: list[NodeEntry]) -> None:
    print(CLEAR, end="")
    print(_c("═" * 54, BOLD))
    print(_c("  GroceryRobot — Dashboard", BOLD))
    print(_c("═" * 54, BOLD))
    print()
    print(_c("  Controls:", BOLD))
    print(f"    {_c('1-5', CYAN)}      view live log  (if running)")
    print(f"             start node     (if {_c('waiting', YELLOW)})")
    print(f"    {_c('r', CYAN)}        refresh display")
    print(f"    {_c('q', CYAN)}        quit and stop all nodes")
    print()
    print(_c("  Log viewer:", BOLD))
    print(f"    {_c('q', CYAN)}        exit log and return to this dashboard")
    print()

    crashes = []
    for i, node in enumerate(nodes, 1):
        if not node.selected:
            continue
        status   = _pad(node.status_str(), 22)
        log_hint = _c(node.log_path.name if node.log_path else "", GRAY)
        print(f"  {_c(str(i), BOLD)}  {node.name:<32}  {status}  {log_hint}")
        if node.is_early_crash():
            crashes.append((i, node.name))

    if crashes:
        print()
        for i, name in crashes:
            print(_c(f"  ⚠  {name} crashed within 5s — press {i} to view log", RED))

    print()


def tail_log(node: NodeEntry) -> None:
    """Follow the node's log file. Press q to return to the dashboard."""
    print(CLEAR, end="")
    print(_c(f"─── {node.name} log  (q to return) ───", BOLD))
    print()
    try:
        with open(node.log_path, "r", errors="replace") as f:
            # Print the last 50 lines already in the file
            lines = f.readlines()
            for line in lines[-50:]:
                print(line, end="")
            sys.stdout.flush()
            # Follow new content, checking for q every 0.2 s
            while True:
                chunk = f.read()
                if chunk:
                    print(chunk, end="")
                    sys.stdout.flush()
                if read_key(timeout=0.2) in ("q", "\x03"):
                    break
    except FileNotFoundError:
        print(_c("  (log file not found)", GRAY))
        time.sleep(1.5)
    print()


def cleanup(nodes: list[NodeEntry]) -> None:
    print()
    print(_c("  Shutting down all nodes...", BOLD))
    # Run teardown.sh — uses pkill -f to kill ROS/Gazebo processes by name.
    # Simply terminating our child processes isn't enough because shell=True
    # means each Popen only owns a /bin/sh wrapper; the actual ros2/gz children
    # become orphans unless we hunt them down by name.
    subprocess.run(["bash", str(REPO_DIR / "teardown.sh")])
    for node in nodes:
        node.stop()
    print(_c("  Done.", GREEN))
    print()


def stage_dashboard(nodes: list[NodeEntry], timestamp: str) -> None:
    try:
        while True:
            draw_dashboard(nodes)
            key = read_key(timeout=2.0)

            if key is None:
                continue                         # timeout — just redraw
            if key in ("\x03", "q"):
                break                            # Ctrl-C or q — quit
            if key == "r":
                continue                         # force redraw
            if key.isdigit() and key != "0":
                idx = int(key) - 1
                if 0 <= idx < len(nodes) and nodes[idx].selected:
                    node = nodes[idx]
                    if node.process is None:
                        # Manual node — start it now
                        node.start(timestamp)
                    elif node.log_path:
                        # Running or done — tail the log
                        tail_log(node)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup(nodes)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if os.environ.get("ROS_DISTRO") != "kilted":
        print(_c("  WARNING: ROS 2 Kilted not sourced. Run via:  bash launch.sh", YELLOW))
        print()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    stage_selection(NODES)
    stage_launch(NODES, timestamp)
    stage_dashboard(NODES, timestamp)


if __name__ == "__main__":
    main()
