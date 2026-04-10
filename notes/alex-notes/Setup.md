# GroceryRobot — Workspace Setup

Getting from a fresh machine to a running simulation.

---

## Prerequisites

Install ROS 2 Kilted (the distro this workspace targets):

```bash
# Follow the official guide at https://docs.ros.org/en/kilted/Installation.html
# Then verify:
source /opt/ros/kilted/setup.bash
ros2 --version
```

Install Gazebo and the ROS 2 control bridge:

```bash
sudo apt install -y \
  gz-harmonic \
  ros-kilted-ros-gz \
  ros-kilted-gz-ros2-control \
  ros-kilted-joint-trajectory-controller \
  ros-kilted-joint-state-broadcaster \
  ros-kilted-controller-manager
```

---

## Clone the Repository

```bash
git clone https://github.com/AlexKautz/GroceryRobot.git
cd GroceryRobot
```

---

## Clone the Third-Party UR Description Package

The `Universal_Robots_ROS2_Description` package is intentionally excluded from the repo
(it has its own Git history). Clone it manually into the right place:

```bash
cd code/alex-code/ros2_ws/src
git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Description.git
```

> NOTE: Our gazebo control additions live in `ur3e_gazebo`, NOT in this upstream package.
> Never edit files inside `Universal_Robots_ROS2_Description` directly — changes there won't
> be tracked and will be lost.

---

## Install ROS Dependencies

From the workspace root:

```bash
cd code/alex-code/ros2_ws
source /opt/ros/kilted/setup.bash
rosdep install --from-paths src --ignore-src -r -y
```

---

## Build

```bash
colcon build --symlink-install
```

Source the workspace after building:

```bash
source install/setup.bash
```

Add this to `~/.bashrc` to avoid sourcing manually every session:

```bash
echo "source /opt/ros/kilted/setup.bash" >> ~/.bashrc
echo "source ~/path/to/GroceryRobot/code/alex-code/ros2_ws/install/setup.bash" >> ~/.bashrc
```

---

## Run the Simulation

```bash
ros2 launch ur3e_gazebo ur3e_gazebo.launch.py
```

This will:
1. Launch Gazebo with the grocery store world
2. Spawn the UR3e robot
3. Start the `joint_state_broadcaster` controller
4. Start the `joint_trajectory_controller` controller

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

## Workspace Structure

```
GroceryRobot/
├── code/alex-code/ros2_ws/
│   └── src/
│       ├── ur3e_gazebo/               # Our package (tracked in git)
│       │   ├── launch/
│       │   │   └── ur3e_gazebo.launch.py
│       │   ├── config/
│       │   │   └── ros2_controllers.yaml
│       │   └── worlds/
│       │       └── grocery_world.sdf
│       └── Universal_Robots_ROS2_Description/  # Third-party, clone separately
└── notes/
    └── alex-notes/
        └── Setup.md                   # This file
```
