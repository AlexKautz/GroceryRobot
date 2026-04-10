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

- [ ] Confirm ROS 2 Kilted is sourced in your native terminal (`printenv ROS_DISTRO` should return `kilted`)
- [ ] Confirm Gazebo Ionic is installed and accessible (`gz sim --version`)
- [ ] Confirm `gz_ros2_control` and `ros_gz_bridge` packages are available for Kilted (`ros2 pkg list | grep gz`)

### Phase 2: Get the UR3e Description

- [ ] Install or clone the `ur_description` package from the Universal Robots ROS 2 repo:
  `https://github.com/UniversalRobots/Universal_Robots_ROS2_Description`
- [ ] Check out the branch compatible with your ROS distro (look for a `kilted` or `rolling` branch)
- [ ] Build the package in your workspace: `colcon build --packages-select ur_description`
- [ ] Source your workspace: `source install/setup.bash`
- [ ] Test that the URDF generates correctly: `ros2 launch ur_description view_ur.launch.py ur_type:=ur3e`

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
