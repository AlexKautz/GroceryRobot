# GroceryRobot — Setup and Info

---

## Part 1: Setting Up on a Fresh Ubuntu System

Getting from a fresh machine to a running simulation.

### Prerequisites

Install ROS 2 Kilted (the distro this workspace targets):

```bash
# Follow the official guide at https://docs.ros.org/en/kilted/Installation.html
# Then verify:
source /opt/ros/kilted/setup.bash
ros2 --version
```

Install Gazebo and all required ROS 2 bridge and control packages:

```bash
sudo apt install -y \
  gz-harmonic \
  ros-kilted-ros-gz \
  ros-kilted-gz-ros2-control \
  ros-kilted-ros2-controllers \
  ros-kilted-joint-trajectory-controller \
  ros-kilted-joint-state-broadcaster \
  ros-kilted-controller-manager \
  ros-kilted-joint-state-publisher-gui
```

---

### Clone the Repository

```bash
git clone https://github.com/AlexKautz/GroceryRobot.git
cd GroceryRobot
```

---

### Clone the Third-Party UR Description Package

The `Universal_Robots_ROS2_Description` package is intentionally excluded from the repo
(it has its own Git history). Clone it manually into the right place:

```bash
cd code/ros-gazebo-v1/ros2_ws/src
git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Description.git
cd Universal_Robots_ROS2_Description
git checkout rolling
```

> NOTE: Our Gazebo control additions live in `ur3e_gazebo`, NOT in this upstream package.
> Never edit files inside `Universal_Robots_ROS2_Description` directly — changes there won't
> be tracked and will be lost when re-cloned.

---

### Install ROS Dependencies

From the workspace root:

```bash
cd code/ros-gazebo-v1/ros2_ws
source /opt/ros/kilted/setup.bash
rosdep install --from-paths src --ignore-src -r -y
```

---

### Build

```bash
colcon build --symlink-install
```

Source the workspace after building:

```bash
source install/setup.bash
```

Add these to `~/.bashrc` to avoid sourcing manually every session:

```bash
echo "source /opt/ros/kilted/setup.bash" >> ~/.bashrc
echo "source ~/path/to/GroceryRobot/code/ros-gazebo-v1/ros2_ws/install/setup.bash" >> ~/.bashrc
```

---

### Run the Simulation

> Run this in a **native terminal**, not the VSCode integrated terminal — Gazebo's GUI has
> a known symbol lookup error in the VSCode terminal.

```bash
ros2 launch ur3e_gazebo ur3e_gazebo.launch.py
```

This will:
1. Launch Gazebo with the grocery store world
2. Start a clock bridge so ROS gets sim time from Gazebo
3. Spawn the UR3e robot
4. Start the `joint_state_broadcaster` controller
5. Start the `joint_trajectory_controller` controller

> ⚠️ **You must click Play in Gazebo before the controllers activate.**
> Gazebo opens in a paused state. While paused, the `/clock` topic does not tick — and the
> `controller_manager` needs `/clock` to initialize. The full startup chain only completes
> once you click the Play button:
>
> 1. Gazebo opens (paused) → robot spawns at its starting position
> 2. Controllers wait — they need `/clock` to run
> 3. **You click Play** → `/clock` starts ticking
> 4. `controller_manager` initializes → controllers activate in sequence
> 5. Any startup motion commands (e.g., move to home pose) fire here
>
> This means the robot will sit still in its spawn pose until you hit Play. That is expected.

### Verify controllers are running

In a second terminal (with the workspace sourced):

```bash
ros2 control list_controllers
```

Expected output:
```
joint_state_broadcaster[joint_state_broadcaster/JointStateBroadcaster] active
joint_trajectory_controller[joint_trajectory_controller/JointTrajectoryController] active
```

---

## Part 2: Key Files Reference

All of our code lives in `code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/`.
The `Universal_Robots_ROS2_Description/` package next to it is third-party — we never edit it.

---

### `launch/ur3e_gazebo.launch.py`

**What it does:** The entry point for the entire simulation. Running `ros2 launch ur3e_gazebo ur3e_gazebo.launch.py` executes this file, which starts every node in the right order.

**Overall description:** A ROS 2 launch file is a Python script that describes what programs to run and in what order. This one starts Gazebo, bridges the clock, publishes the robot description, spawns the robot into Gazebo, and then chains the two controllers using event handlers so each step waits for the previous one to finish.

**Key lines to know:**

- **Lines 18–24** — Generates the robot URDF by running `xacro` on our wrapper file. `ParameterValue(..., value_type=str)` prevents ROS 2 from misinterpreting the XML as YAML, which would crash the launch.
- **Lines 27–38** — Starts Gazebo using `ros_gz_sim`'s built-in launch file, passing it the path to our world file.
- **Lines 41–46** — The clock bridge node. This bridges Gazebo's internal `/clock` to a ROS `/clock` topic, which is what lets the `controller_manager` use simulated time instead of wall time. Without this the controller spawners time out.
- **Lines 49–55** — `robot_state_publisher` reads the URDF and continuously publishes the transform tree (`/tf`) so other tools (RViz, etc.) know where each joint is.
- **Lines 58–68** — `spawn_robot` tells Gazebo to pull the robot description off the `/robot_description` ROS topic and insert the robot into the simulation.
- **Lines 71–84** — The two controller spawner nodes. They call the `controller_manager` service to load and activate `joint_state_broadcaster` and `joint_trajectory_controller`.
- **Lines 87–97** — `RegisterEventHandler` with `OnProcessExit` chains the startup sequence: spawn_robot finishes → start broadcaster → broadcaster finishes → start trajectory controller. This ordering matters; if controllers spawn before the robot is in Gazebo, the controller_manager has nothing to connect to.

---

### `urdf/ur3e_gz.urdf.xacro`

**What it does:** Describes the robot to ROS and Gazebo — its joints, links, physics, and what hardware plugin to use for simulation.

**Overall description:** This is our "wrapper" xacro file. Rather than editing the upstream UR3e description (which we don't own), we include it here and append our own simulation-specific blocks on top. Xacro is a macro language that gets expanded into plain URDF XML at launch time.

**Key lines to know:**

- **Line 5** — `xacro:include` pulls in the upstream UR3e robot macro from `ur_description`. This is the entire physical description of the arm (links, joints, meshes, collision geometry).
- **Lines 8–9** — A fixed `world` link that the arm attaches to. Without this, the arm would have no fixed reference frame and would fall through the ground.
- **Lines 11–22** — `xacro:ur_robot` expands the upstream macro with UR3e-specific config files. `force_abs_paths="true"` is critical — without it, Gazebo can't find the mesh `.stl`/`.dae` files and the arm spawns invisible.
- **Lines 25–77** — The `<ros2_control>` block. This is what tells `gz_ros2_control` which joints exist and what interfaces each one exposes (`position` command, `position`/`velocity`/`effort` state). Every joint in this list must match the joint names in the URDF exactly.
- **Lines 80–84** — The `<gazebo>` plugin block. This loads the `gz_ros2_control::GazeboSimROS2ControlPlugin` into Gazebo, which is the bridge between Gazebo's physics engine and the ROS 2 `controller_manager`. It also points to our `ros2_controllers.yaml` config file.

---

### `config/ros2_controllers.yaml`

**What it does:** Configures the `controller_manager` and defines the two controllers — what type they are and what joints/interfaces they operate on.

**Overall description:** This YAML file is read by both `gz_ros2_control` at startup (via the xacro plugin block) and by the controller spawner nodes at launch. It has two sections: the `controller_manager` section (which registers the controller names and types) and the `joint_trajectory_controller` section (which specifies which joints it controls and at what rate).

**Key lines to know:**

- **Line 3** — `update_rate: 100` sets the controller loop to run at 100 Hz. This must be slower than the physics step rate in `grocery_world.sdf` (1000 Hz), which it is.
- **Lines 5–6** — Registers `joint_state_broadcaster` by type. This controller reads all joint states from the hardware and publishes them to `/joint_states`. It needs no further config.
- **Lines 8–9** — Registers `joint_trajectory_controller` by type. This is the controller that actually accepts motion commands.
- **Lines 13–19** — Lists all 6 UR3e joint names that the trajectory controller manages. These must exactly match the joint names in the URDF/xacro — a mismatch here causes a silent failure at activation.
- **Lines 20–23** — `command_interfaces: [position]` means we send position targets (not velocity or torque). `state_interfaces: [position, velocity]` means the controller reads back both position and velocity to track trajectory progress.

---

### `worlds/grocery_world.sdf`

**What it does:** Defines the Gazebo simulation environment — the physics settings, the ground plane, and the lighting.

**Overall description:** An SDF (Simulation Description Format) file is Gazebo's world format. This is a minimal world with just enough to run a meaningful simulation: physics at 1000 Hz, a flat ground plane with friction, and a directional sun light. The robot is not defined here — it gets spawned into this world at runtime by the launch file.

**Key lines to know:**

- **Lines 4–6** — Physics timing: `max_step_size` of 0.001 s = 1000 Hz physics. `real_time_factor: 1` means the simulation runs at real-world speed (not accelerated or slowed).
- **Lines 8–11** — The four Gazebo system plugins that must be present for any meaningful simulation: `Physics` (runs the physics engine), `UserCommands` (allows interaction via the GUI), `SceneBroadcaster` (streams the scene to the GUI renderer), and `Contact` (enables collision detection).
- **Lines 20–68** — The ground plane model. Marked `<static>true</static>` so it has infinite mass and won't move when the robot pushes on it. The arm is mounted on top of this.
- **Lines 69–87** — The sun directional light. Without this the scene renders completely black.

---

### `setup.py`

**What it does:** Tells `colcon` (the ROS 2 build tool) what to install and where, so ROS can find our package's files after building.

**Overall description:** This is a standard Python `setuptools` file used by `ament_python` packages. The critical part is the `data_files` list — it tells colcon to copy our non-Python files (launch files, world, URDF, config) into the `install/` directory after building. If a file isn't registered here, it won't be found by `FindPackageShare` at runtime, and the launch will fail.

**Key lines to know:**

- **Line 14** — Installs all `launch/*.py` files. Without this line, `ros2 launch ur3e_gazebo ...` would say the package has no launch files.
- **Line 15** — Installs `worlds/*.sdf`. Without this, Gazebo can't find `grocery_world.sdf`.
- **Line 16** — Installs `urdf/*.xacro`. Without this, the xacro command in the launch file fails.
- **Line 17** — Installs `config/*.yaml`. Without this, the controller_manager can't read `ros2_controllers.yaml`.

> Any time you add a new file type to the package (e.g., a mesh folder, a new config),
> you must add a corresponding `glob` line here and rebuild, or ROS won't see it.

---

## Workspace Structure

```
GroceryRobot/
├── code/ros-gazebo-v1/ros2_ws/
│   └── src/
│       ├── ur3e_gazebo/                        # Our package (tracked in git)
│       │   ├── launch/
│       │   │   └── ur3e_gazebo.launch.py       # Entry point — starts everything
│       │   ├── urdf/
│       │   │   └── ur3e_gz.urdf.xacro          # Robot description + control wiring
│       │   ├── config/
│       │   │   └── ros2_controllers.yaml       # Controller definitions and joint list
│       │   ├── worlds/
│       │   │   └── grocery_world.sdf           # Gazebo world (ground, physics, lights)
│       │   ├── setup.py                        # Tells colcon what files to install
│       │   └── package.xml                     # Package metadata and dependencies
│       └── Universal_Robots_ROS2_Description/  # Third-party — clone separately, never edit
└── notes/
    └── ros-gazebo-v1/
        └── Setup and Info.md                   # This file
```
