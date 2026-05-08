# GroceryRobot

A simulated grocery-picking robot built on **ROS 2 Kilted** and **Gazebo Ionic**.
A UR3e arm picks an item off a table and places it onto a shelf, fully autonomously.

---

## Quick Start

> Run in a **native terminal** — Gazebo's GUI has a known error in the VS Code integrated terminal.

**First time on a new machine:**
```bash
source /opt/ros/kilted/setup.bash
bash setup.sh
```

**Every time after that:**
```bash
bash launch.sh
```

`launch.sh` tears down any running simulation, optionally rebuilds the workspace, then opens an interactive launch manager where you can select which nodes to start. Nodes can be set to **auto** (start immediately) or **manual** (start from the dashboard when ready). Your selections are remembered for next time.

Click **Play** in Gazebo after it opens. The arm will move to its home pose facing the table.

**To stop everything:**
```bash
bash teardown.sh
```

**For full setup, see [[Setup and Info]]**

---

## Automated tolerance sweep (overnight)

`sweep_run.sh` runs all 25 combinations of `POSITION_TOLERANCE × ORIENTATION_TOLERANCE` automatically in a single Gazebo session — 5 ball positions each, 125 pick cycles total. Results are appended to `multi_run_results.csv`.

```bash
bash sweep_run.sh
```

Edit the knobs at the top of `sweep_run.py` before running:

| Variable | What it controls |
|---|---|
| `POSITION_TOLERANCES` | List of MoveIt position tolerances to test (metres) |
| `ORIENTATION_TOLERANCES` | List of MoveIt orientation tolerances to test (radians) |
| `FAST_MODE` | `True` = headless Gazebo (no window) + shorter settle times — roughly 2× faster |

**Keep the computer awake on Ubuntu**

Wrap the command with `gnome-session-inhibit` so suspend is blocked for exactly as long as the sweep runs, then automatically re-enabled when it finishes:

```bash
gnome-session-inhibit --inhibit suspend:idle --reason "overnight sweep" bash sweep_run.sh
```

Alternatively, disable suspend manually before you start and re-enable it after:

```bash
# Before — disable automatic suspend and screen blank
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.desktop.session idle-delay 0

bash sweep_run.sh

# After — restore defaults
gsettings reset org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type
gsettings reset org.gnome.desktop.session idle-delay
```

> Make sure the machine is plugged in. Ubuntu's suspend settings are separate for battery vs. AC power — the commands above only affect AC.

---

## What the simulation does

1. A UR3e arm spawns in a world containing a table, a red apple, and a shelf
2. Arm cameras (wrist-mounted + overhead) stream RGB and depth images into ROS 2
3. On launch, the arm moves to a home pose facing the table
4. Running `pick_and_place` sequences the arm through a full pick-and-place:
   opens the gripper → approaches the apple → grasps it → lifts → rotates to the shelf → places → returns home

---

## Repository layout

```
GroceryRobot/
├── launch.sh                       # Entry point — run this to start everything
├── launch.py                       # Interactive node manager (called by launch.sh)
├── setup.sh                        # First-time setup on a new machine
├── teardown.sh                     # Stop all running simulation processes
├── code/
│   └── ros-gazebo-v1/
│       └── ros2_ws/src/
│           └── ur3e_gazebo/        # Our ROS 2 package (all custom code lives here)
├── notes/
│   └── ros-gazebo-v1/
│       ├── Setup and Info.md       # Full setup guide and key-files reference
│       ├── Gripper Testing Guide.md
│       └── Pick and Place Tuning Guide.md
└── documents/                      # Formal write-ups (LaTeX + PDFs)
```

---

## Team
*Note: These roles are just general categories. Everybody works on everything.*

| Person | Area |
|--------|------|
| Alex | Gazebo simulation |
| Kevin | ROS integration / manipulation |
| Pascale | CV / object detection |

---

## Contributing

1. Create a branch at https://github.com/AlexKautz/GroceryRobot/branches
2. Make changes and commit
3. Open a pull request at https://github.com/AlexKautz/GroceryRobot/pulls
4. Squash merge when approved

Notes are stored as Markdown. [Obsidian](https://obsidian.md/) works well — open the repo root folder to get started.

## Overleaf
The equivalent Overleaf project can be found at https://www.overleaf.com/project/69efb0f4a3da6a34ba808193.
