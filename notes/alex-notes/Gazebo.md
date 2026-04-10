# 🛠️ Work Notes — Gazebo Setup

## Getting Started
- Guide: https://gazebosim.org/docs/all/getstarted/
- Basic test command: `gz sim shapes.sdf`
  - Basic but functional!
  - `-v 4` flag enables debug output
  - `-s` runs headless (not particularly useful here)
- **SDF** is used to specify simulation contents — this is highly relevant!
  - Object library: https://app.gazebosim.org/fuel

---

## Building & Moving the Robot

- Tutorial: https://gazebosim.org/docs/ionic/building_robot/
- Test file: `building_robot.sdf`
- Run with: `gz sim building_robot.sdf`
- ⚠️ Encountered error when running in **VSCode terminal**:

```
gz sim gui: symbol lookup error: /snap/core20/current/lib/x86_64-linux-gnu/libpthread.so.0: undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE
```

> **Fix:** Switch to the **native terminal** instead of the VSCode integrated terminal.

- Tutorial reference for movement: https://gazebosim.org/docs/ionic/moving_robot/

---

## Robot Arm

- The tutorials are too deep to work through from scratch in one week — jumping ahead with AI assistance.
- Robot arm selected: **UR3e** by Universal Robots
  - https://www.universal-robots.com/products/ur3e/
  - *(Originally planned a different arm, but it wasn't compatible with our version of Gazebo)*
- **Next question:** How do I create a simple simulation with the UR3e arm?

---

## ⚠️ AI-Generated Section — Next Steps to Spawn the UR3e in Gazebo Ionic

> The following steps were suggested by AI to help get the UR3e arm running in a basic Gazebo Ionic + ROS 2 Kilted simulation. Treat as a starting point — verify each step as you go.

### Phase 1: Environment Check

- [x] Confirm ROS 2 Kilted is sourced in your native terminal (`printenv ROS_DISTRO` should return `kilted`)
- [x] Confirm Gazebo Ionic is installed and accessible (`gz sim --version`)
- [x] Confirm `gz_ros2_control` and `ros_gz_bridge` packages are available for Kilted (`ros2 pkg list | grep gz`)
### ROS 2 Workspace — `ros2_ws`

A ROS 2 workspace is a directory that `colcon` uses to build, install, and organize ROS 2 packages. The workspace lives at `~/Code/ROS/GroceryRobot/code/alex-code/ros2_ws` and has four key folders:

- `src/` — where you clone or place package source code
- `build/` — intermediate build artifacts (auto-generated, don't touch)
- `install/` — the final built packages that ROS 2 actually uses
- `log/` — build logs

Any time you add a new package, clone it into `src/`, then run `colcon build` from the workspace root. Always re-source after building:

```bash
source install/setup.bash
```

This "refreshes" ROS 2's awareness of the workspace. Add it to `~/.bashrc` to avoid doing it manually in every terminal. 
### Phase 2: Get the UR3e Description
- [x] Clone the `ur_description` package into your workspace `src/` folder:
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/alex-code/ros2_ws/src`
```bash
  git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Description
```

- [x] Check out the `rolling` branch (confirmed compatible branch for our ROS distro):
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/alex-code/ros2_ws/src/Universal_Robots_ROS2_Description`
```bash
  git checkout rolling
```

- [x] Build the package:
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/alex-code/ros2_ws`
```bash
  colcon build --packages-select ur_description
```

- [x] Source the workspace:
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/alex-code/ros2_ws`
```bash
  source install/setup.bash
```

- [x] Test that the URDF generates correctly:
  - 📁 **Run from:** anywhere (as long as workspace is sourced)
```bash
  ros2 launch ur_description view_ur.launch.py ur_type:=ur3e
```
  - ✅ Success looks like: RViz opens and displays the UR3e arm model
  - ⚠️ If RViz doesn't open, check that `rviz2` is installed: `sudo apt install ros-kilted-rviz2`
### Phase 3: Spawn the Arm in Gazebo Ionic

- [ ] Create a minimal Gazebo Ionic world `.sdf` file with a ground plane and lighting
- [ ] Add a `ros_gz_bridge` config to bridge joint states and commands between ROS 2 and Gazebo
- [ ] Write (or adapt) a launch file that:
  - Starts Gazebo Ionic with your world
  - Spawns the UR3e URDF into the simulation
  - Starts `robot_state_publisher`
- [ ] Run the launch file and confirm the arm appears in the Gazebo GUI without errors

### Phase 4: Basic Joint Verification

- [ ] Verify joint states are publishing: `ros2 topic echo /joint_states`
- [ ] Send a basic joint command manually to confirm the arm moves
- [ ] Confirm no collisions or URDF errors appear in the terminal output

### Phase 5: Ready for April 15th Meeting

- [ ] Take a screenshot of the working arm in Gazebo to share with the team
- [ ] Note any compatibility issues encountered for Keven (ROS) and Pascale (CV) to be aware of
- [ ] Commit any working config files to `code/Gazebo/` in the shared repo
