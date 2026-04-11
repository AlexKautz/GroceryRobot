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

---

## ⚠️ AI-Generated Section — Next Steps to Spawn the UR3e in Gazebo Ionic

> The following steps were suggested by AI to help get the UR3e arm running in a basic Gazebo Ionic + ROS 2 Kilted simulation. Treat as a starting point — verify each step as you go.

### Phase 1: Environment Check

- [x] Confirm ROS 2 Kilted is sourced in your native terminal (`printenv ROS_DISTRO` should return `kilted`)
- [x] Confirm Gazebo Ionic is installed and accessible (`gz sim --version`)
- [x] Confirm `gz_ros2_control` and `ros_gz_bridge` packages are available for Kilted (`ros2 pkg list | grep gz`)
  - ⚠️ `gz_ros2_control` was missing — fixed with:
```bash
  sudo apt install ros-kilted-gz-ros2-control
```

---

### ROS 2 Workspace — `ros2_ws`

A ROS 2 workspace is a directory that `colcon` uses to build, install, and organize ROS 2 packages. The workspace lives at `~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws` and has four key folders:

- `src/` — where you clone or place package source code
- `build/` — intermediate build artifacts (auto-generated, don't touch)
- `install/` — the final built packages that ROS 2 actually uses
- `log/` — build logs

Any time you add a new package, clone it into `src/`, then run `colcon build` from the workspace root. Always re-source after building:

```bash
source install/setup.bash
```

This "refreshes" ROS 2's awareness of the workspace. Add it to `~/.bashrc` to avoid doing it manually in every terminal.

---

### Phase 2: Get the UR3e Description

- [x] Clone the `ur_description` package into your workspace `src/` folder:
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws/src`
```bash
git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Description
```

- [x] Check out the `rolling` branch (confirmed compatible branch for our ROS distro):
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws/src/Universal_Robots_ROS2_Description`
```bash
git checkout rolling
```

- [x] Build the package:
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws`
```bash
colcon build --packages-select ur_description
```

- [x] Source the workspace:
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws`
```bash
source install/setup.bash
```

- [x] Test that the URDF generates correctly:
  - 📁 **Run from:** anywhere (as long as workspace is sourced)
```bash
ros2 launch ur_description view_ur.launch.py ur_type:=ur3e
```
  - ✅ Success looks like: RViz opens and displays the UR3e arm model
  - ⚠️ `joint_state_publisher_gui` was missing — fixed with:
```bash
  sudo apt install ros-kilted-joint-state-publisher-gui
```

---

### Phase 3: Spawn the Arm in Gazebo Ionic

- [x] Create a minimal Gazebo Ionic world `.sdf` file with a ground plane and lighting
  - ✅ **Note:** The default empty world that opens with `gz sim` already includes a ground plane (`default`) and a sun light (`sun`) — no manual setup needed. Just open Gazebo and use `File > Save World As grocery_world.sdf`.
  - ✅ World file stored at: `src/ur3e_gazebo/worlds/grocery_world.sdf`

- [x] Create a new ROS 2 package `ur3e_gazebo` to hold the launch file and world:
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws/src`
```bash
ros2 pkg create ur3e_gazebo --build-type ament_python --dependencies ros2launch ros_gz_sim robot_state_publisher
```
  - Created a `launch/` and `worlds/` folder inside the package
  - Registered both in `setup.py` using `glob`

- [x] Write the launch file `ur3e_gazebo.launch.py`:
  - ✅ Final working launch file at: `src/ur3e_gazebo/launch/ur3e_gazebo.launch.py`
  - ⚠️ **Gotchas encountered:**
    - The xacro file requires `name:=ur3e` to be passed explicitly despite having a default — ordering bug in the xacro file causes it to fail otherwise
    - Must pass `force_abs_paths:=true` so Gazebo can find the mesh `.stl` and `.dae` files — without this the arm spawns invisibly with mesh errors
    - World file must be referenced via `PathJoinSubstitution` + `FindPackageShare`, not just a bare filename

```python
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution, Command


def generate_launch_description():

    ur_description_pkg = FindPackageShare('ur_description')

    robot_description = Command([
        'ros2 run xacro xacro ',
        PathJoinSubstitution([ur_description_pkg, 'urdf', 'ur.urdf.xacro']),
        ' ur_type:=ur3e',
        ' name:=ur3e',
        ' force_abs_paths:=true',
    ])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={'gz_args': PathJoinSubstitution([
            FindPackageShare('ur3e_gazebo'), 'worlds', 'grocery_world.sdf'
        ])}.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'ur3e',
            '-topic', 'robot_description',
        ],
    )

    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        spawn_robot,
    ])
```

- [x] Run the launch file and confirm the arm appears in the Gazebo GUI without errors:
  - 📁 **Run from:** `~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws`
```bash
ros2 launch ur3e_gazebo ur3e_gazebo.launch.py
```
  - ✅ Arm appears in Gazebo

- [x] Check what topics Gazebo and ROS 2 are publishing:
```bash
gz topic -l
ros2 topic list
```
  - ✅ ROS 2 topics confirmed: `/joint_states`, `/robot_description`, `/tf`, `/tf_static`
  - ⚠️ No joint topics on the Gazebo side — `gz_ros2_control` plugin is **not yet loaded**
  - This means the arm is currently a static mesh — joints are not simulated yet
  - `ros_gz_bridge` is **not needed yet** — will be relevant later when adding a camera

---

### Phase 3.5: Set Up Claude Code in VS Code

> ⚠️ AI-Generated Section

Claude Code's VS Code extension brings AI-assisted coding directly into the editor — inline diffs, accept/reject buttons, file @-mentions, and a chat panel that already knows your project context. Think Cursor, but it's an extension so all your existing VS Code settings, themes, and plugins stay intact.

> **Requirement:** You need a Claude Pro, Max, Team, or Enterprise account, OR an Anthropic Console account with active API billing. The free Claude.ai plan does not include Claude Code access.

> **Requirement:** VS Code version 1.98.0 or later.

---

**Step 1 — Install the Claude Code CLI (required first):**
- 📁 **Run from:** anywhere
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
Then add it to PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```
Verify:
```bash
claude --version
```

**Step 2 — Install the VS Code extension:**

Open VS Code and press `Ctrl+Shift+X` to open the Extensions panel. Search for `Claude Code` and install the one published by **Anthropic** (watch out for unofficial lookalikes).

Alternatively, install from the terminal:
```bash
code --install-extension anthropic.claude-code
```

**Step 3 — Authenticate:**

Click the **Spark icon** (⚡) that appears in the VS Code sidebar after installation. It will prompt you to sign in — follow the browser login flow with your Anthropic account.

**Step 4 — Open the project:**
- Open `~/Code/ROS/GroceryRobot` as your VS Code workspace
- Click the Spark icon in the sidebar to open the Claude Code panel
- Claude Code will automatically read your project structure — no manual setup needed

**Step 5 — Sanity check:**

Try a simple prompt in the panel:
```
What packages are in this ROS 2 workspace?
```
✅ Success: Claude describes your `ur_description` and `ur3e_gazebo` packages correctly

---

> **Key features to know:**
> - **Inline diffs** — Claude proposes changes as diffs you can accept or reject line by line
> - **@-mention files** — type `@filename` in the prompt to pull a specific file into context
> - **Plan mode** — Claude shows its plan before making changes, so you can review and edit it first
> - **Terminal access** — Claude can run commands in the VS Code integrated terminal with your permission

### Phase 4: Basic Joint Verification

> ✅ `gz_ros2_control` is wired up and both controllers load successfully as of 2026-04-11.

- [x] Add `gz_ros2_control` plugin to the URDF so Gazebo simulates joint physics
  - [x] Locate the `ur_macro.xacro` file inside `ur_description` — this is where the plugin needs to be added
  - [x] Add a `<gazebo>` plugin block referencing `gz_ros2_control` to the xacro
  - [x] Create a `ros2_controllers.yaml` config file inside `ur3e_gazebo` defining the joint controllers
  - [x] Update the launch file to load the controller config and spawn the controllers on startup

#### Note: I've switched entirely to Claude Code
It is just not possible for me to learn this in time without the project failing. Luckily, this is a good chance to learn Claude Code and get into the loop of working on this. It's very interesting. You actually have to edit both files that you control and the files you get for the description of the robotic arm. It's incredibly complicated, LOL.

- [x] Rebuild and relaunch, confirm both controllers activate cleanly
  - [x] Install missing package: `sudo apt install -y ros-kilted-ros2-controllers`
  - [x] Rebuild: `colcon build --packages-select ur3e_gazebo`
  - [x] Re-source: `source install/setup.bash`
  - [x] Relaunch: `ros2 launch ur3e_gazebo ur3e_gazebo.launch.py`
  - [x] Confirmed via spawner output: `Configured and activated joint_state_broadcaster`
  - [x] Confirmed via spawner output: `Configured and activated joint_trajectory_controller`
  - ⚠️ **Gotcha:** Controller spawners were timing out due to no sim clock. Fixed by adding a `ros_gz_bridge` clock bridge node to the launch file (`/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock`). Without this, `controller_manager` has no sim time and service calls hang.

- [x] Verify joint states are publishing:
  - [x] Run `ros2 topic echo /joint_states`
  - [x] All 6 joints listed with position, velocity, and effort values
  - [x] Values updating over time — sim time ticking, effort non-zero (gravity hold)

- [x] Send a basic joint command manually to confirm the arm moves
  - [x] Publish to `/joint_trajectory_controller/joint_trajectory`
  - [x] Sent `shoulder_pan_joint` to 1.0 rad with `time_from_start: 2s` — arm moved in Gazebo GUI ✅
  - Command used:
```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint],
  points: [{
    positions: [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    time_from_start: {sec: 2, nanosec: 0}
  }]
}"
```

- [x] Confirm no collisions or URDF errors in terminal output — none observed
---

### Phase 5: Ready for April 15th Meeting

- [x] Take a screenshot of the working arm in Gazebo to share with the team
- [x] Note any compatibility issues encountered for Keven (ROS) and Pascale (CV) to be aware of
- [x] Commit any working config files to `code/Gazebo/` in the shared repo