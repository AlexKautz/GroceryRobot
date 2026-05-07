#!/usr/bin/env python3
"""
multi_run.py — Run 5 pick cycles with different ball positions in a single Gazebo session.
Run via:  bash multi_run.sh
"""

import datetime
import os
import subprocess
import sys
import time

import csv
import pathlib

from launch_lib import (
    NODES, LOGS_DIR, REPO_DIR,
    _c, BOLD, GREEN, YELLOW, GRAY, RED,
    cleanup, run_teardown,
    wait_for_topic, wait_for_action, gazebo_unpause,
)


# ─── Test configuration ───────────────────────────────────────────────────────
# Edit these values to change the test behaviour across all 5 runs.

BALL_POSITIONS = [
    (0.35,  0.0,  0.065),   # 1 — center
    (0.3,   0.1,  0.065),   # 2 — left edge
    (0.3,  -0.1,  0.065),   # 3 — right edge
    (0.4,   0.1,  0.065),   # 4 — far from arm
    (0.4,  -0.1,  0.065),   # 5 — near-left
]

POSITION_TOLERANCE    = 0.01   # metres   — MoveIt goal position tolerance
ORIENTATION_TOLERANCE = 0.01   # radians  — MoveIt goal orientation tolerance

VELOCITY_SCALING      = 0.5    # 0.0–1.0  — fraction of maximum joint velocity
ACCELERATION_SCALING  = 0.5    # 0.0–1.0  — fraction of maximum joint acceleration
STEP_SETTLE_TIME      = 1.0    # seconds  — pause between arm movement steps

PICK_SUCCESS_Z_THRESHOLD = 0.15  # metres  — ball must exceed this Z after lift to count as picked
                                 #           table ≈ 0.065 m, lift target ≈ 0.315 m

PICK_TIMEOUT_SEC      = 120    # seconds  — per-cycle wall-clock timeout

CSV_FILE = REPO_DIR / "multi_run_results.csv"

_CSV_HEADER = [
    "timestamp", "run", "ball_x", "ball_y", "ball_z",
    "pos_tol", "ori_tol", "vel_scale", "accel_scale", "settle_s",
    "result",
]


# ─── Apple SDF (mirrors the definition in grocery_world.sdf) ─────────────────
# Used by move_ball() to respawn the apple at a new position with zero velocity.

_APPLE_SDF = (
    '<sdf version="1.9">'
    '<model name="apple">'
    '<link name="apple_link">'
    '<collision name="collision">'
    '<geometry><sphere><radius>0.04</radius></sphere></geometry>'
    '</collision>'
    '<visual name="visual">'
    '<geometry><sphere><radius>0.04</radius></sphere></geometry>'
    '<material>'
    '<ambient>0.8 0.1 0.1 1</ambient>'
    '<diffuse>0.8 0.1 0.1 1</diffuse>'
    '</material>'
    '</visual>'
    '<inertial><mass>0.15</mass>'
    '<inertia>'
    '<ixx>0.000096</ixx><iyy>0.000096</iyy><izz>0.000096</izz>'
    '<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz>'
    '</inertia>'
    '</inertial>'
    '</link>'
    '</model>'
    '</sdf>'
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _node(name):
    return next(n for n in NODES if n.name == name)


def write_csv_results(timestamp, results):
    write_header = not CSV_FILE.exists() or CSV_FILE.stat().st_size == 0
    with CSV_FILE.open("a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(_CSV_HEADER)
        for i, x, y, z, status in results:
            label = {"ok": "SUCCESS", "missed": "MISSED", "failed": "FAILED", "move_failed": "MOVE_FAILED"}.get(status, status.upper())
            writer.writerow([
                timestamp, i, x, y, z,
                POSITION_TOLERANCE, ORIENTATION_TOLERANCE,
                VELOCITY_SCALING, ACCELERATION_SCALING, STEP_SETTLE_TIME,
                label,
            ])
    print(f"  Results appended to {CSV_FILE.name}")


def move_ball(x, y, z):
    """
    Respawn the apple at (x, y, z) with guaranteed zero velocity/acceleration.
    Uses remove + create instead of set_pose because set_pose preserves
    whatever momentum the ball had from the previous pick cycle.
    """
    # Step 1: remove the existing apple entity
    remove_result = subprocess.run(
        [
            "gz", "service", "-s", "/world/empty/remove",
            "--reqtype", "gz.msgs.Entity",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "2000",
            "--req", 'name: "apple" type: MODEL',
        ],
        capture_output=True, text=True,
    )
    if remove_result.returncode != 0:
        print(_c(f"  ✗ gz remove failed: {remove_result.stderr.strip()}", RED))
        return False

    # Brief pause so the physics engine processes the removal before we create
    time.sleep(0.3)

    # Step 2: recreate at the new position — fresh entity starts with zero velocity
    escaped_sdf = _APPLE_SDF.replace('"', '\\"')
    create_req = (
        f'sdf: "{escaped_sdf}" '
        f'name: "apple" '
        f'pose: {{position: {{x: {x} y: {y} z: {z}}} orientation: {{w: 1.0}}}}'
    )
    create_result = subprocess.run(
        [
            "gz", "service", "-s", "/world/empty/create",
            "--reqtype", "gz.msgs.EntityFactory",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "2000",
            "--req", create_req,
        ],
        capture_output=True, text=True,
    )
    if create_result.returncode != 0:
        print(_c(f"  ✗ gz create failed: {create_result.stderr.strip()}", RED))
        return False

    print(f"  Apple respawned at ({x:.3f}, {y:.3f}, {z:.3f}) — zero velocity")
    return True


def run_pick_cycle(run_idx, x, y, z, timestamp):
    """
    Launch one instance of moveit_pick_from_camera with exit_on_complete=true.
    Blocks until the process exits or times out.
    Returns True on exit code 0 (success), False otherwise.
    """
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / f"multi_run_{timestamp}_run{run_idx:02d}.log"

    cmd = (
        "ros2 run ur3e_gazebo moveit_pick_from_camera --ros-args"
        " -p use_sim_time:=true"
        f" -p position_tolerance:={POSITION_TOLERANCE}"
        f" -p orientation_tolerance:={ORIENTATION_TOLERANCE}"
        f" -p velocity_scaling:={VELOCITY_SCALING}"
        f" -p acceleration_scaling:={ACCELERATION_SCALING}"
        f" -p step_settle_time:={STEP_SETTLE_TIME}"
        " -p pre_grasp_z_offset:=0.20"
        " -p grasp_z_offset:=0.08"
        " -p lift_z_offset:=0.25"
        " -p gripper_open:=0.08"
        " -p gripper_closed:=-0.006"
        f" -p pick_success_z_threshold:={PICK_SUCCESS_Z_THRESHOLD}"
        " -p go_home_before_pick:=true"
        " -p go_home_after_pick:=true"
        " -p exit_on_complete:=true"
    )

    print(f"  Launching pick node → {log_path.name}")

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            proc.wait(timeout=PICK_TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), 9)
            except ProcessLookupError:
                pass
            print(_c(f"  ✗ Run {run_idx}: TIMED OUT after {PICK_TIMEOUT_SEC}s", RED))
            return False

    rc = proc.returncode
    if rc == 0:
        print(_c(f"  ✓ Run {run_idx}: SUCCESS", GREEN))
        return "ok"
    elif rc == 2:
        print(_c(f"  ~ Run {run_idx}: MISSED — arm moved correctly but ball not lifted", YELLOW))
        return "missed"
    else:
        print(_c(f"  ✗ Run {run_idx}: FAILED (exit {rc}) — see {log_path.name}", RED))
        return "failed"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if os.environ.get("ROS_DISTRO") != "kilted":
        print(_c("  WARNING: ROS 2 Kilted not sourced. Run via:  bash multi_run.sh", YELLOW))
        print()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    active_nodes = []

    print()
    print("=" * 50)
    print("  GroceryRobot — Multi-Run (5 positions)")
    print(f"  {timestamp}")
    print(f"  position_tolerance    = {POSITION_TOLERANCE} m")
    print(f"  orientation_tolerance = {ORIENTATION_TOLERANCE} rad")
    print(f"  velocity_scaling      = {VELOCITY_SCALING}")
    print(f"  acceleration_scaling  = {ACCELERATION_SCALING}")
    print(f"  step_settle_time      = {STEP_SETTLE_TIME} s")
    print(f"  pick_timeout          = {PICK_TIMEOUT_SEC} s")
    print("=" * 50)
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

        print()
        print("  === Starting 5-position pick loop ===")
        print()

        results = []

        for i, (x, y, z) in enumerate(BALL_POSITIONS, start=1):
            print(f"─── Run {i}/{len(BALL_POSITIONS)}  ball=({x:.3f}, {y:.3f}, {z:.3f}) ───")

            if not move_ball(x, y, z):
                print(_c(f"  Skipping run {i} — ball move failed.", RED))
                results.append((i, x, y, z, "move_failed"))
                print()
                continue

            # Give the localizer time to publish a fresh detection at the new position
            print("  Waiting 3s for fresh apple detection...")
            time.sleep(3.0)

            cycle_status = run_pick_cycle(i, x, y, z, timestamp)
            results.append((i, x, y, z, cycle_status))
            print()

        write_csv_results(timestamp, results)

        # ── Summary ──────────────────────────────────────────────────────
        print("=" * 50)
        print(_c("  Multi-Run Summary", BOLD))
        print(f"  position_tolerance    = {POSITION_TOLERANCE} m")
        print(f"  orientation_tolerance = {ORIENTATION_TOLERANCE} rad")
        print(f"  velocity_scaling      = {VELOCITY_SCALING}")
        print(f"  acceleration_scaling  = {ACCELERATION_SCALING}")
        print(f"  step_settle_time      = {STEP_SETTLE_TIME} s")
        print()
        ok_count     = sum(1 for *_, s in results if s == "ok")
        missed_count = sum(1 for *_, s in results if s == "missed")
        for i, x, y, z, status in results:
            color = GREEN if status == "ok" else (YELLOW if status == "missed" else RED)
            label = {"ok": "SUCCESS", "missed": "MISSED", "failed": "FAILED", "move_failed": "MOVE FAILED"}.get(status, status)
            print(f"  Run {i}  ({x:.3f}, {y:.3f}, {z:.3f})  {_c(label, color)}")
        print()
        print(f"  {_c(str(ok_count), GREEN if ok_count == len(results) else YELLOW)}/{len(results)} picked"
              + (f"  ({missed_count} missed)" if missed_count else ""))
        print("=" * 50)
        print()

    except KeyboardInterrupt:
        pass
    finally:
        cleanup(active_nodes)


if __name__ == "__main__":
    main()
