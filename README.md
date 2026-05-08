# GroceryRobot

This project explores the task of putting away groceries with a robotic arm, addressing the computer vision and motion planning components and their translation into a simulated environment. We then narrow our focus to the subtask of picking up objects, analyzing the effect of lighting on the YOLO detection algorithm and the effect of increasing movement tolerance on the success of the pickup task.

This repository contains the code to run the robot simulation, along with supporting documents.

---

# Running the code

This project is intended to run on a Ubunto desktop running ROS 2 Kilted and Gazebo Ionic.

We also recommend [installing UV](https://docs.astral.sh/uv/getting-started/installation/) to manage the Python environments.

## First-time setup

```bash
./setup.sh
```

Run once on a new machine. Builds the ROS 2 workspace and installs Python dependencies.
Gives warnings if something is not installed (such as the correct version of Gazebo)

---

## Launch scripts

All scripts must be run from a **native terminal** (not the VS Code integrated terminal).

### `./launch.sh` — Interactive launch

The standard way to run the simulation. Prompts which ROS nodes to start and whether to rebuild the workspace (aka run setup.sh again), then opens a live dashboard.

### `./full_single_run.sh` — Automated launch, no pick node

Runs a full process of the robotic arm identifying and then picking up the apple automatically.

### `./multi_run.sh` — 5-position automated test

Runs a full process of the robotic arm identifying and picking up the apple automatically. The Apple then spawns in five different locations and the arm picks it up. Results are logged to `multi_run_results.csv` for future analysis.

### `./sweep_run.sh` — Tolerance parameter sweep

Runs `multi_run` under a large combination of different values of position and orientation tolerance. 
Runs headless, without spawning the Gazebo UI for improved speed.

### `./teardown.sh` — Stop everything

Kills all running simulation processes. Safe to run even if nothing is running.

---

## Logs

All node output is written to `logs/` with a timestamp in the filename.

# Report

The report can be read at [GroceryRobot.pdf](documents/latex/final_report/GroceryRobot.pdf)

# Videos
* Demo of the robot running `multi_run`: [Vimeo](https://vimeo.com/1190248547)
* Presentation about our project: [Vimeo](https://vimeo.com/1190332631)

# AI Use

As part of this project we collaborated with [Claude Code](https://claude.com/product/claude-code) and [ChatGPT](https://chatgpt.com/)

The process of working with these models consisted of working together to design a detailed plan, and then step-by-step implementing it. An example planning document is [Alex-Work-Log.md](notes/ros-gazebo-v1/Alex-Work-Log.md), which covered some of the initial work to design the environment.

We understood during this entire process that the use of AI is a balance. Our work is our own.
