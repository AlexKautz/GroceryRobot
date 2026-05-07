#!/usr/bin/env python3
"""
sweep_run.py — Sweep all 25 POSITION_TOLERANCE × ORIENTATION_TOLERANCE combinations.
5 ball positions per combination = 125 pick cycles total in a single Gazebo session.
Run via:  bash sweep_run.sh
"""

import csv
import datetime
import os
import subprocess
import sys
import time

from launch_lib import (
    NODES, LOGS_DIR, REPO_DIR,
    _c, BOLD, GREEN, YELLOW, GRAY, RED,
    cleanup, run_teardown,
    wait_for_topic, wait_for_action, gazebo_unpause,
)
from multi_run import (
    BALL_POSITIONS,
    VELOCITY_SCALING, ACCELERATION_SCALING, STEP_SETTLE_TIME,
    PICK_SUCCESS_Z_THRESHOLD, PICK_TIMEOUT_SEC,
    CSV_FILE, _CSV_HEADER,
    move_ball,
)


# ─── Sweep configuration ──────────────────────────────────────────────────────

POSITION_TOLERANCES    = [0.01, 0.02, 0.03, 0.04, 0.05]
ORIENTATION_TOLERANCES = [0.01, 0.02, 0.03, 0.04, 0.05]

# Set True to run Gazebo headless (no GUI window) and shorten settle/detection waits.
# Trades visual feedback for speed: ~2–3 hours → ~1–1.5 hours for the full sweep.
# Requires a GPU that supports EGL (most NVIDIA/AMD/Intel setups do).
FAST_MODE = False


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _node(name):
    return next(n for n in NODES if n.name == name)


def run_pick_cycle(run_idx, x, y, z, timestamp, combo_label, pos_tol, ori_tol):
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / f"sweep_{timestamp}_{combo_label}_run{run_idx:02d}.log"

    cmd = (
        "ros2 run ur3e_gazebo moveit_pick_from_camera --ros-args"
        " -p use_sim_time:=true"
        f" -p position_tolerance:={pos_tol}"
        f" -p orientation_tolerance:={ori_tol}"
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
            cmd, shell=True,
            stdout=log_file, stderr=subprocess.STDOUT,
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
            return "failed"

    rc = proc.returncode
    if rc == 0:
        print(_c(f"  ✓ Run {run_idx}: SUCCESS", GREEN))
        return "ok"
    elif rc == 2:
        print(_c(f"  ~ Run {run_idx}: MISSED — arm moved but ball not lifted", YELLOW))
        return "missed"
    else:
        print(_c(f"  ✗ Run {run_idx}: FAILED (exit {rc}) — see {log_path.name}", RED))
        return "failed"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if os.environ.get("ROS_DISTRO") != "kilted":
        print(_c("  WARNING: ROS 2 Kilted not sourced. Run via:  bash sweep_run.sh", YELLOW))
        print()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    active_nodes = []

    combinations = [
        (pt, ot)
        for pt in POSITION_TOLERANCES
        for ot in ORIENTATION_TOLERANCES
    ]
    n_combos = len(combinations)
    n_positions = len(BALL_POSITIONS)
    total_cycles = n_combos * n_positions

    print()
    print("=" * 58)
    print("  GroceryRobot — Tolerance Sweep")
    print(f"  {timestamp}")
    print(f"  pos_tol:   {POSITION_TOLERANCES}")
    print(f"  ori_tol:   {ORIENTATION_TOLERANCES}")
    print(f"  {n_combos} combinations × {n_positions} positions = {total_cycles} cycles")
    print(f"  velocity_scaling      = {VELOCITY_SCALING}")
    print(f"  acceleration_scaling  = {ACCELERATION_SCALING}")
    print(f"  step_settle_time      = {STEP_SETTLE_TIME} s")
    print(f"  pick_timeout          = {PICK_TIMEOUT_SEC} s")
    print("=" * 58)
    print()

    # Settle/detection times: shorter in fast mode since headless has less overhead
    # and -r starts unpaused so the physics engine is already running at clock time.
    controller_settle_secs = 3.0 if FAST_MODE else 5.0
    detection_wait_secs    = 1.5 if FAST_MODE else 3.0

    run_teardown()

    write_header = not CSV_FILE.exists() or CSV_FILE.stat().st_size == 0
    csv_f = CSV_FILE.open("a", newline="")
    writer = csv.writer(csv_f)
    if write_header:
        writer.writerow(_CSV_HEADER)

    try:
        sim = _node("Simulation")
        sim.selected = True
        if FAST_MODE:
            sim.command = sim.command + " headless:=true"
        print("  Starting Simulation..." + (" (headless)" if FAST_MODE else ""))
        sim.start(timestamp)
        active_nodes.append(sim)

        wait_for_topic("/clock", "Gazebo clock", timeout_sec=90)
        print(f"  Letting controllers settle ({controller_settle_secs:.0f}s)...")
        time.sleep(controller_settle_secs)

        gazebo_unpause()  # no-op in fast mode (-r already unpaused), safe to call anyway

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
        print(f"  === Starting sweep: {n_combos} combinations, {total_cycles} total cycles ===")
        print()

        all_summary = []

        for combo_num, (pos_tol, ori_tol) in enumerate(combinations, start=1):
            combo_label = f"pt{str(pos_tol).replace('.', '')}ot{str(ori_tol).replace('.', '')}"
            print(f"{'─' * 58}")
            print(f"  Combo {combo_num}/{n_combos}  pos_tol={pos_tol}  ori_tol={ori_tol}")
            print(f"{'─' * 58}")

            combo_results = []

            for i, (x, y, z) in enumerate(BALL_POSITIONS, start=1):
                print(f"─── Run {i}/{n_positions}  ball=({x:.3f}, {y:.3f}, {z:.3f}) ───")

                if not move_ball(x, y, z):
                    print(_c(f"  Skipping run {i} — ball move failed.", RED))
                    combo_results.append((i, x, y, z, "move_failed"))
                    print()
                    continue

                print(f"  Waiting {detection_wait_secs:.1f}s for fresh apple detection...")
                time.sleep(detection_wait_secs)

                status = run_pick_cycle(i, x, y, z, timestamp, combo_label, pos_tol, ori_tol)
                combo_results.append((i, x, y, z, status))
                print()

            # Write and flush this combo's rows immediately so data is safe overnight
            for i, x, y, z, status in combo_results:
                label = {
                    "ok": "SUCCESS", "missed": "MISSED",
                    "failed": "FAILED", "move_failed": "MOVE_FAILED",
                }.get(status, status.upper())
                writer.writerow([
                    timestamp, i, x, y, z,
                    pos_tol, ori_tol,
                    VELOCITY_SCALING, ACCELERATION_SCALING, STEP_SETTLE_TIME,
                    label,
                ])
            csv_f.flush()

            ok_count     = sum(1 for *_, s in combo_results if s == "ok")
            missed_count = sum(1 for *_, s in combo_results if s == "missed")
            color = GREEN if ok_count == n_positions else (YELLOW if ok_count > 0 else RED)
            print(f"  Combo {combo_num} result: {_c(f'{ok_count}/{n_positions}', color)} picked"
                  + (f"  ({missed_count} missed)" if missed_count else ""))
            print(f"  Results flushed to {CSV_FILE.name}")
            print()

            all_summary.append((combo_num, pos_tol, ori_tol, combo_results))

        # ── Final summary ─────────────────────────────────────────────────────
        print("=" * 58)
        print(_c("  Sweep Summary", BOLD))
        print()
        grand_ok = 0
        for combo_num, pos_tol, ori_tol, combo_results in all_summary:
            ok = sum(1 for *_, s in combo_results if s == "ok")
            missed = sum(1 for *_, s in combo_results if s == "missed")
            grand_ok += ok
            color = GREEN if ok == n_positions else (YELLOW if ok > 0 else RED)
            print(f"  pt={pos_tol:.2f} ot={ori_tol:.2f}  {_c(f'{ok}/{n_positions}', color)}"
                  + (f"  ({missed} missed)" if missed else ""))
        print()
        grand_color = GREEN if grand_ok == total_cycles else YELLOW
        print(f"  Grand total: {_c(str(grand_ok), grand_color)}/{total_cycles} picked")
        print("=" * 58)
        print()

    except KeyboardInterrupt:
        pass
    finally:
        csv_f.close()
        cleanup(active_nodes)


if __name__ == "__main__":
    main()
