#!/usr/bin/env python3
"""
launch_lib.py — Shared infrastructure for all GroceryRobot launch scripts.

Exports:
  Constants     REPO_DIR, LOGS_DIR, PREFS_FILE
  ANSI          RED/GREEN/YELLOW/CYAN/GRAY/BOLD/RESET/CLEAR, _c, _vlen, _pad
  Data          NodeEntry, NODES
  Prefs         load_prefs, save_node_prefs
  Process       run_teardown, run_setup, cleanup
  Terminal      read_key, tail_log
  Dashboard     draw_dashboard, stage_dashboard
  Automation    wait_for_topic, wait_for_action, gazebo_unpause
"""

import dataclasses
import json
import os
import pathlib
import re
import select
import signal
import subprocess
import sys
import termios
import time
import tty
from typing import Optional


# ─── Paths ────────────────────────────────────────────────────────────────────

REPO_DIR   = pathlib.Path(__file__).parent.resolve()
LOGS_DIR   = REPO_DIR / "logs"
PREFS_FILE = REPO_DIR / "launch_prefs.json"


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
    return len(re.sub(r'\033\[[0-9;]*m', '', s))

def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _vlen(s))


# ─── Preferences ──────────────────────────────────────────────────────────────

def load_prefs() -> dict:
    try:
        return json.loads(PREFS_FILE.read_text())
    except Exception:
        return {}

def save_node_prefs(nodes: list) -> None:
    prefs = load_prefs()
    prefs["nodes"] = {n.name: {"selected": n.selected, "mode": n.mode} for n in nodes}
    PREFS_FILE.write_text(json.dumps(prefs, indent=2))


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclasses.dataclass
class NodeEntry:
    name: str
    command: str
    selected: bool = False
    mode: str = "auto"                   # 'auto' | 'manual'
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
            start_new_session=True,
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
    NodeEntry("Pick and Place",            "ros2 run ur3e_gazebo pick_and_place",                                          mode="manual"),
    NodeEntry("Arm Camera Localizer",      "ros2 run ur3e_gazebo arm_camera_localizer"),
    NodeEntry("Overhead Camera Localizer", "ros2 run ur3e_gazebo overhead_camera_localizer"),
    NodeEntry("Joint Control Panel",       "ros2 run ur3e_gazebo joint_control_panel"),
    NodeEntry("Image Viewer",              "QT_QPA_PLATFORM=xcb ros2 run rqt_image_view rqt_image_view /overhead_camera/annotated_image"),
    NodeEntry("MoveIt Pick from Camera",   "ros2 launch ur3e_gazebo moveit_pick_from_camera.launch.py",                   mode="manual"),
    NodeEntry("MoveIt",                    "ros2 launch ur3e_moveit_config move_group.launch.py",                         mode="manual"),
    NodeEntry("Apple Detection Test",      "ros2 run ur3e_gazebo test_apple_detection",                                   mode="manual"),
]


# ─── Process utilities ────────────────────────────────────────────────────────

def run_teardown() -> None:
    subprocess.run(["bash", str(REPO_DIR / "teardown.sh")])

def run_setup() -> None:
    subprocess.run(["bash", str(REPO_DIR / "setup.sh")])

def cleanup(nodes: list[NodeEntry]) -> None:
    print()
    print(_c("  Shutting down all nodes...", BOLD))
    run_teardown()
    for node in nodes:
        node.stop()
    print(_c("  Done.", GREEN))
    print()


# ─── Terminal input ───────────────────────────────────────────────────────────

def read_key(timeout: float = 2.0) -> Optional[str]:
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


# ─── Log viewer ───────────────────────────────────────────────────────────────

def tail_log(node: NodeEntry) -> None:
    print(CLEAR, end="")
    print(_c(f"─── {node.name} log  (q to return) ───", BOLD))
    print()
    try:
        with open(node.log_path, "r", errors="replace") as f:
            lines = f.readlines()
            for line in lines[-50:]:
                print(line, end="")
            sys.stdout.flush()
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


# ─── Dashboard ────────────────────────────────────────────────────────────────

def draw_dashboard(nodes: list[NodeEntry]) -> None:
    print(CLEAR, end="")
    print(_c("═" * 54, BOLD))
    print(_c("  GroceryRobot — Dashboard", BOLD))
    print(_c("═" * 54, BOLD))
    print()
    print(_c("  Controls:", BOLD))
    print(f"    {_c('1-9', CYAN)}      view live log  (if running)")
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


def stage_dashboard(nodes: list[NodeEntry], timestamp: str) -> None:
    try:
        while True:
            draw_dashboard(nodes)
            key = read_key(timeout=2.0)
            if key is None:
                continue
            if key in ("\x03", "q"):
                break
            if key == "r":
                continue
            if key.isdigit() and key != "0":
                idx = int(key) - 1
                if 0 <= idx < len(nodes) and nodes[idx].selected:
                    node = nodes[idx]
                    if node.process is None:
                        node.start(timestamp)
                    elif node.log_path:
                        tail_log(node)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup(nodes)


# ─── Automation helpers ───────────────────────────────────────────────────────

def wait_for_topic(topic: str, label: str, timeout_sec: int = 60) -> None:
    print(f"  Waiting for {label} ({topic})...")
    elapsed = 0
    while True:
        result = subprocess.run(["ros2", "topic", "list"], capture_output=True, text=True)
        if topic in result.stdout.splitlines():
            print(f"  ✓ {label} is up")
            return
        time.sleep(2)
        elapsed += 2
        if elapsed >= timeout_sec:
            print(f"  ✗ Timed out waiting for {label} after {timeout_sec}s", file=sys.stderr)
            sys.exit(1)


def wait_for_action(action: str, label: str, timeout_sec: int = 60) -> None:
    print(f"  Waiting for {label} ({action})...")
    elapsed = 0
    while True:
        result = subprocess.run(["ros2", "action", "list"], capture_output=True, text=True)
        if action in result.stdout.splitlines():
            print(f"  ✓ {label} is ready")
            return
        time.sleep(2)
        elapsed += 2
        if elapsed >= timeout_sec:
            print(f"  ✗ Timed out waiting for {label} after {timeout_sec}s", file=sys.stderr)
            sys.exit(1)


def gazebo_unpause() -> None:
    print("  Unpausing Gazebo...")
    result = subprocess.run(
        [
            "gz", "service",
            "-s", "/world/empty/control",
            "--reqtype", "gz.msgs.WorldControl",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "3000",
            "--req", "pause: false",
        ],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("  ✓ Gazebo unpaused")
    else:
        print("  ✗ gz service call failed — Gazebo may already be running or world name changed")
