# GroceryRobot

A simulated grocery-picking robot. A UR3e arm picks a red apple off a table and places it on a shelf, using MoveIt 2 for motion planning and YOLOv8 via an overhead camera for localization.

---

## First-time setup

```bash
bash setup.sh
```

Run once on a new machine. Builds the ROS 2 workspace and installs Python dependencies.

---

## Launch scripts

All scripts must be run from a **native terminal** (not the VS Code integrated terminal — Gazebo's GUI breaks there).

### `bash launch.sh` — Interactive launch

The standard way to run the simulation. Prompts you to select which nodes to start and whether to rebuild the workspace, then opens a live dashboard. Nodes can be set to **auto** (start immediately) or **manual** (start from the dashboard on demand).

### `bash do_the_thing.sh` — Fully automated single run

Starts everything automatically in the right order — simulation, overhead camera localizer, MoveIt, and the pick node — then waits. No interaction required. Ctrl+C stops everything cleanly.

### `bash full_single_run.sh` — Automated launch, no pick node

Same as `do_the_thing.sh` but stops before launching the pick node. Useful for watching the simulation manually or running the pick node yourself in a second terminal.

### `bash multi_run.sh` — 5-position automated test

Runs one full pick cycle at each of 5 preset apple positions in a single Gazebo session. Results are appended to `multi_run_results.csv`. Edit the knobs at the top of `multi_run.py` to change tolerances, velocity scaling, and other parameters.

### `bash sweep_run.sh` — Tolerance parameter sweep

Sweeps all combinations of `POSITION_TOLERANCE × ORIENTATION_TOLERANCE` (8 × 8 = 64 combinations by default), 5 positions each, in a single Gazebo session. Results are appended to `multi_run_results.csv`. Edit the lists at the top of `sweep_run.py` before running.

Set `FAST_MODE = True` in `sweep_run.py` for headless Gazebo (no GUI) — roughly 2× faster.

### `bash teardown.sh` — Stop everything

Kills all running simulation processes. Safe to run even if nothing is running.

---

## Logs

All node output is written to `logs/` with a timestamp in the filename.
