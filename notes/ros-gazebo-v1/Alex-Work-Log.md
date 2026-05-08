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
- [x] Note any compatibility issues encountered for Kevin (ROS) and Pascale (CV) to be aware of
- [x] Commit any working config files to `code/Gazebo/` in the shared repo

# 🛠️ Work Notes — Camera and Shelf

### Goals for this phase:
* Updating the world
	* On one side of the robotic arm is a table
		* On top of the table is an apple
		* In the future we will have a box containing the Apple (and other groceries), but that will be future work.
	* On the other side of the robotic arm is a shelf
		* The shelf is representing a refrigerator
	* The robotic arm should start facing the apple.
* Creating the image module template
	* Attach a camera and a 3D camera to the robotic arm
	* Create a camera and a 3D camera floating above the table looking down
	* In ROS Create two modules.
		* One will use the camera and 3D camera on the arm and return expected location information.
		* The other will use the camera and 3D camera floating above and again return expected location information.
		* For both the expected location information is the location of the grocery item in this case an apple.
		* Actually programming this module is the job of a teammate. So I want you to put in lots of comments and hints on how to do this, and assume the person working on this project has not actually worked with the robotic operating system or gazebo before. But don't actually implement the computer vision algorithms.
* Moving the Arm
	* Attach a gripper to the arm.
	* Have the arm reach down and grab the apple. Make sure it's doing this using a hard-coded, pre-set location of the apple, since making it dynamic will be the job of other group members.
* Notes
	* During this entire process, make sure to update the three notes in the ros-gazebo-folder. Create another note which is a guide for programming this specific robot, both from Ross and specifically for the computer vision part of it. This will include a section on programming gazebo for my own work.

---

> ⚠️ AI-Generated Section — Steps below were generated by Claude Code based on the goals above.

---

### Phase 6: World Setup — Table, Apple, and Shelf

**Goal:** Replace the empty world with a meaningful scene — a table with an apple on one side of the arm, and a shelf (representing a fridge) on the other. The arm should start oriented toward the table.

**The only file you'll edit in this phase:** `worlds/grocery_world.sdf`

> 💡 **How Gazebo worlds work:** Everything in the simulation is a `<model>`. Each model has one or more `<link>`s (rigid bodies), and each link has a `<visual>` (what it looks like) and a `<collision>` (what it physically is). `<static>true</static>` means the object has infinite mass and won't move when touched — use this for furniture. The apple should NOT be static so physics applies to it.

> 💡 **Coordinates:** The UR3e base is fixed at the world origin `(0, 0, 0)`. Its default zero-pose points the arm straight up. Positive X is "forward" in front of the arm. So: put the table at ~`(0.7, 0, 0)` and the shelf at ~`(-0.7, 0, 0)`.

---

#### 6.1 Add a Table on One Side of the Arm

- [x] Open `worlds/grocery_world.sdf`
- [x] Inside the `<world>` tag (after the existing lighting and ground plane), add a table model:
  - [x] The table should be `<static>true</static>` — it never moves
  - [x] Position it at approximately `(0.7, 0, 0)` — roughly 70 cm in front of the arm
  - [x] A simple table is just a flat box (the top) at height ~0.75 m, plus four leg boxes
  - [x] Give the table a brown color using `<ambient>` and `<diffuse>` RGBA values

  > 💡 **Hint — Table height:** A standard table is 0.75 m tall. The arm base is at ground level (z=0). The arm's working range is roughly 0.3–1.0 m above its base, so a 0.75 m table puts the apple right in the middle of its reach.

  > 💡 **Hint — Simple first:** Start with just the tabletop box — skip the legs at first. Get the apple working, then go back and add legs for looks.

  > ⚠️ **Every `<link>` needs both `<visual>` AND `<collision>`** if you want the arm to interact with it. A visual-only object is invisible to physics and the arm will pass right through it.

- [x] Save the file and relaunch: `ros2 launch ur3e_gazebo ur3e_gazebo.launch.py`
- [x] Confirm the table appears in the Gazebo GUI at the right position
- [x] ✅ Check: the table is NOT floating and NOT sunken into the ground

---

#### 6.2 Add an Apple on the Table

- [x] In the same `grocery_world.sdf`, add an apple model:
  - [x] Use a `<sphere>` geometry with radius ~`0.04` (4 cm — realistic apple size)
  - [x] Set `<static>false</static>` — the apple should respond to physics (it can be grabbed)
  - [x] Position it at `(0.7, 0, 0.79)` — table height (0.75) + tabletop thickness (0.025) + apple radius (0.04) ≈ 0.815... adjust until it sits neatly on the surface
  - [x] Give it a red color: ambient/diffuse `(0.8, 0.1, 0.1, 1.0)`
  - [x] Add an `<inertial>` block — physics objects must have mass and inertia or Gazebo will warn/explode
    - Mass: `0.15` kg (a real apple is ~150 g)
    - Inertia for a sphere: `ixx = iyy = izz = (2/5) * mass * radius²` = `0.000096`

  > ⚠️ **Missing inertia = bad physics.** If you skip the `<inertial>` block on a non-static object, Gazebo will either crash, warn heavily, or make the object behave like it has zero mass and go flying. Always add it.

  > 💡 **Hint — Getting height right:** If the apple sinks into the table, increase its Z position. If it floats above the table, decrease it. The exact number depends on your tabletop thickness. Just eyeball it in the GUI.

  > ⚠️ **Don't make the apple static.** It needs to be a physics object so the gripper can interact with it. If it's static, the gripper will just clip through it.

- [x] Relaunch and confirm the apple appears sitting on the table
- [x] ✅ Check: the apple stays on the table and doesn't fall through or fly away when the simulation starts

---

#### 6.3 Add a Shelf on the Other Side

- [x] In `grocery_world.sdf`, add a shelf model:
  - [x] `<static>true</static>` — the shelf never moves
  - [x] Position at approximately `(-0.7, 0, 0)` — 70 cm behind the arm (opposite the table)
  - [x] Build it from multiple box links:
    - [x] A back panel (tall vertical box, ~0.8 m wide × 1.2 m tall × 0.03 m deep)
    - [x] Three horizontal shelf boards at different heights (e.g., z = 0.3, 0.6, 0.9 m)
    - [x] Each shelf board: ~0.8 m wide × 0.35 m deep × 0.03 m thick
  - [x] Give it a light grey or white color to suggest a fridge interior

  > 💡 **Hint — Keep it simple.** A shelf is just a few boxes. Don't overthink it. The team just needs something to place groceries on — it doesn't need to look photo-realistic.

  > 💡 **Hint — Rotation.** The shelf should face the arm. Since the arm's "front" is +X and the shelf is at -X, the shelf faces +X naturally. No rotation needed.

  > ⚠️ **Multi-link models in SDF:** Each separate board in the shelf is a `<link>`. All links go inside the same `<model>` tag. You do NOT need joints between them — since the whole model is static, they just exist as separate rigid shapes.

- [x] Relaunch and confirm the shelf appears on the opposite side of the arm from the table
- [x] ✅ Check: the shelf is upright, at a reachable distance, and facing the arm

---

#### 6.4 Set the Arm's Starting Orientation

By default the arm starts with all joints at 0 — this puts it pointing straight up, which isn't useful. We want it to start "looking at" the table (facing +X, arm slightly lowered).

> 💡 **`initial_value` vs. home pose — they are different things:**
>
> - **`initial_value`** (set in `urdf/ur3e_gz.urdf.xacro`, inside the `<ros2_control>` block) is a
>   hint to the **Gazebo physics engine**. It sets where the joint is physically placed when the
>   simulation first loads — before any controller has started. The arm teleports to that position
>   at spawn time.
>
> - **Home pose command** (a `JointTrajectory` message sent through the `joint_trajectory_controller`)
>   is a live motion command sent **through the ROS 2 controller**. The controller actively drives
>   each joint to the target angles — the arm visibly moves there after launch.
>
> **Why use both:** `initial_value` sets the physics starting point so there's no jitter on spawn.
> The home pose command ensures the controller is actively holding the pose. In practice, try
> `initial_value` alone first — if the arm drifts or jolts when the controller activates, add the
> trajectory command as a second layer.
>
> **Visual confirmation tip:** Since `initial_value` is currently `0.0` for all joints (arm pointing
> up) and the home pose will be the facing-table angles, you'll naturally see the arm move every
> time you start the sim — which confirms the controller chain is working correctly.
>
> ⚠️ **Controllers only activate after you click Play in Gazebo.** The sim opens paused, `/clock`
> doesn't tick while paused, and the `controller_manager` needs `/clock` to run. The arm will sit
> still at its spawn position until you hit Play — at that point the controllers activate and any
> home pose command fires. This is expected behavior.

- [x] Find a good "home" pose — decided on the following angles:
  - `shoulder_pan_joint`: `0.0` (facing +X toward table)
  - `shoulder_lift_joint`: `-1.57` (arm sweeps forward)
  - `elbow_joint`: `1.57` (elbow bent, arm reaches out)
  - `wrist_1_joint`: `-1.57` (wrist level)
  - `wrist_2_joint`: `0.0`
  - `wrist_3_joint`: `0.0`

- [x] Set home pose angles as `initial_value` in `urdf/ur3e_gz.urdf.xacro` (inside the `<ros2_control>` block for each joint)

- [x] Created `ur3e_gazebo/home_pose.py` — a one-shot ROS 2 node that publishes a single `JointTrajectory` command to the home pose angles, then exits cleanly

- [x] Wired `home_pose` into the launch file, chained after `joint_trajectory_controller` activates via `RegisterEventHandler` / `OnProcessExit`

- [x] Registered `home_pose` as a `console_scripts` entry point in `setup.py` and rebuilt

- [x] ✅ Check: arm spawns facing the table on every launch. `home_pose` node fires after Play is clicked and exits cleanly (confirmed in logs).

  > 📝 **Design decision:** Both `initial_value` and the home pose command were set to the same
  > angles. The arm spawns directly in the correct position — no visible movement after clicking
  > Play. This is intentional: `initial_value` prevents physics jitter on spawn, and the
  > `home_pose` command ensures the controller is actively holding the pose.

---

### Phase 7: Cameras and Vision Module Templates

**Goal:** Add cameras to the simulation (one set on the arm, one set overhead), bridge them to ROS topics, and create two stub Python nodes that a teammate can fill in with actual CV logic.

> 💡 **What "bridging" means:** Gazebo has its own internal topic system (gz topics). ROS 2 has its own (ROS topics). They don't talk to each other automatically. The `ros_gz_bridge` package creates a bridge process that copies messages from one system to the other. You already used it for the `/clock` — cameras need the same treatment.

> 💡 **Two types of cameras you'll add:**
> - **Regular camera** (`camera`): produces color image frames. Like a webcam.
> - **Depth / RGBD camera** (`rgbd_camera`): produces both color AND a depth map (distance to every pixel). Like a Microsoft Kinect or Intel RealSense. This is what lets you figure out where in 3D space an object is.

---

#### 7.1 Add a Camera and Depth Camera to the Robot Arm

The cameras attach near the end of the arm. **We mounted them on `wrist_3_link` (not `tool0`)** — see design decision note below.

- [x] Open `urdf/ur3e_gz.urdf.xacro`
- [x] Added a `camera_link` (small box representing the camera body) and a fixed joint attaching it to `wrist_3_link`:
  - Offset: 4 cm to the side (Y), 6 cm along the wrist axis (Z), angled ~17° down to see the gripper workspace
  - `<origin xyz="0 0.04 0.06" rpy="0 0.3 0"/>`
- [x] Added two `<gazebo reference="camera_link">` sensor blocks:
  - RGB camera (`arm_rgb_camera`, type `camera`) — 640×480, 30 fps, topic `/arm_camera/image_raw`
  - Depth camera (`arm_depth_camera`, type `rgbd_camera`) — 640×480, 30 fps, topic `/arm_depth_camera`
- [x] Added the `gz-sim-sensors-system` plugin to `worlds/grocery_world.sdf` — **required for any camera to work in Gazebo**:
  ```xml
  <plugin name='gz::sim::systems::Sensors' filename='gz-sim-sensors-system'>
    <render_engine>ogre2</render_engine>
  </plugin>
  ```
- [x] Rebuilt and relaunched. Confirmed via `gz topic -l | grep camera`:
  - `/arm_camera/image_raw`
  - `/arm_camera/camera_info`
  - `/arm_depth_camera/image`
  - `/arm_depth_camera/depth_image`
  - `/arm_depth_camera/points`
  - `/arm_depth_camera/camera_info`

  > 📝 **Design decision — wrist_3_link instead of tool0:**
  > Mounting on `tool0` risks a conflict when the gripper is added in Phase 8 — `tool0` is the
  > conventional gripper attachment point. Using `wrist_3_link` as the parent keeps `tool0` free.
  > The camera_link is offset so the view still covers the gripper workspace.

  > ⚠️ **URDF `<material>` must have a `name` attribute.** A bare `<material><color rgba="..."/></material>` block (without `name="..."`) causes a parse error: "Visual material must contain a name attribute." Always write `<material name="something">`.

  > ⚠️ **`gz_frame_id` is not a valid SDF element** in Gazebo Ionic. Adding `<gz_frame_id>` inside a sensor block causes warnings. Omit it.

  > ⚠️ **Run in a native terminal.** Camera rendering uses the GPU — GPU issues surface more often in the VSCode integrated terminal.

---

#### 7.2 Add Overhead Cameras Above the Table (Fixed in World)

These cameras are fixed in the world — they don't move. They go in `worlds/grocery_world.sdf`.

- [x] Open `worlds/grocery_world.sdf`
- [x] Added a new `static` model named `overhead_camera`:
  - Pose: `0.35 0 1.2 0 1.5708 0` — centered over the table work area, 1.2 m up, pitched 90° to face straight down
  - Small box visual (0.05 × 0.05 × 0.03 m) representing the camera body
  - RGB camera sensor (`overhead_rgb_camera`, type `camera`) — 640×480, 30 fps, topic `/overhead_camera/image_raw`
  - Depth camera sensor (`overhead_depth_camera`, type `rgbd_camera`) — 640×480, 30 fps, topic `/overhead_depth_camera`
- [x] Relaunched and confirmed via `gz topic -l | grep camera`:
  - `/overhead_camera/image_raw`
  - `/overhead_camera/camera_info`
  - `/overhead_depth_camera/image`
  - `/overhead_depth_camera/depth_image`
  - `/overhead_depth_camera/points`
  - `/overhead_depth_camera/camera_info`

  > 💡 **Visualizing the camera direction:** In Gazebo, enable **View → Camera Frustums** in the GUI to see which way your cameras are pointing. If the frustum points the wrong direction, adjust the pitch angle in the pose.

  > 💡 **Why `rpy="0 1.5708 0"` (pitch 90°)?** In Gazebo, a camera's default "forward" direction is +X. Rotating 90° around Y points the sensor straight down (-Z). Without this rotation, the camera would be looking sideways instead of at the table.

---

#### 7.3 Bridge Camera Topics from Gazebo to ROS

Right now the camera topics exist in Gazebo but ROS 2 can't see them. Bridge them in the launch file.

- [x] Open `launch/ur3e_gazebo.launch.py`
- [x] **Split the bridge into two separate nodes** (clock bridge and camera bridge):
  - `clock_bridge` — bridges only `/clock` (critical infrastructure; keeps controllers alive)
  - `camera_bridge` — bridges all 12 camera topics (sensor data; isolated so a camera issue can't kill the clock)
  - Both nodes added to the `LaunchDescription` return list

  > 📝 **Design decision — two separate bridges:**
  > Keeping `/clock` in its own bridge node means a camera issue (topic type mismatch, missing plugin,
  > etc.) can't crash the clock bridge and kill your controllers. It also makes each node's purpose
  > obvious and easier to debug independently.

  > 💡 **Reading the `@` syntax:** `topic_name@ROS_type[gz_type`
  > - `@` separates the topic name from the type mapping
  > - `[` = direction Gazebo → ROS (Gz publishes, ROS subscribes)
  > - `]` = direction ROS → Gazebo
  > - `@` between types (no bracket) = bidirectional
  > We use `[` for all camera topics because data always flows out of the sim into ROS.

- [x] Camera topics bridged (all 12 confirmed working):
  ```
  /arm_camera/image_raw        → sensor_msgs/msg/Image
  /arm_camera/camera_info      → sensor_msgs/msg/CameraInfo
  /arm_depth_camera/image      → sensor_msgs/msg/Image
  /arm_depth_camera/depth_image → sensor_msgs/msg/Image
  /arm_depth_camera/points     → sensor_msgs/msg/PointCloud2
  /arm_depth_camera/camera_info → sensor_msgs/msg/CameraInfo
  /overhead_camera/image_raw   → sensor_msgs/msg/Image
  /overhead_camera/camera_info → sensor_msgs/msg/CameraInfo
  /overhead_depth_camera/image → sensor_msgs/msg/Image
  /overhead_depth_camera/depth_image → sensor_msgs/msg/Image
  /overhead_depth_camera/points → sensor_msgs/msg/PointCloud2
  /overhead_depth_camera/camera_info → sensor_msgs/msg/CameraInfo
  ```
- [x] ✅ Verified: `ros2 topic list | grep camera` shows all 12 topics

---

#### 7.4 Create the Arm Camera Localizer Node (Stub for CV Teammate)

This node subscribes to the arm's camera feeds and publishes the estimated 3D location of the apple. The CV logic is left as a scaffold for the CV teammate to fill in.

- [x] Created `ur3e_gazebo/arm_camera_localizer.py`
  - Node name: `arm_camera_localizer`
  - Subscribes to:
    - `/arm_camera/image_raw` (`sensor_msgs/msg/Image`)
    - `/arm_depth_camera/depth_image` (`sensor_msgs/msg/Image`)
    - `/arm_depth_camera/camera_info` (`sensor_msgs/msg/CameraInfo`)
  - Publishes: `/arm_camera/apple_location` (`geometry_msgs/msg/PointStamped`)
  - Diagnostic logging: mean R/G/B per frame (throttled 2s), depth min/max/mean (throttled 2s)
  - tf2 buffer + listener wired up; `_lookup_camera_to_world()` helper provided
  - Full CV pipeline outlined in docstring with hints at each TODO step
  - Dummy `(0, 0, 0)` publish with `CV NOT IMPLEMENTED` warning as placeholder

  > 📝 **Design note — wrist camera coordinate frames:**
  > The arm camera moves with the arm, so every frame the transform from
  > `camera_link` to `world` is different. tf2 handles this automatically via
  > the `_lookup_camera_to_world()` helper. The CV implementation must always
  > transform detections to world frame before publishing.

- [x] Registered in `setup.py` as `arm_camera_localizer`
- [x] ✅ Tested: node starts, logs RGB and depth diagnostics, publishes dummy location

---

#### 7.5 Overhead Camera Localizer Node (Stub for CV Teammate)

Same pattern as the arm node, but uses the fixed overhead cameras. Simpler coordinate frame math since the camera never moves.

- [x] Created `ur3e_gazebo/overhead_camera_localizer.py`
  - Node name: `overhead_camera_localizer`
  - Subscribes to:
    - `/overhead_camera/image_raw` (`sensor_msgs/msg/Image`)
    - `/overhead_depth_camera/depth_image` (`sensor_msgs/msg/Image`)
    - `/overhead_depth_camera/camera_info` (`sensor_msgs/msg/CameraInfo`)
  - Publishes: `/overhead_camera/apple_location` (`geometry_msgs/msg/PointStamped`)
  - Diagnostic logging: mean R/G/B per frame (throttled 2s), depth min/max/mean (throttled 2s)
  - tf2 buffer + listener wired up; `_lookup_camera_to_world()` uses `overhead_camera_link` frame
  - Notes in docstring: overhead view is good for X/Y; depth gives Z; transform is constant
  - Dummy `(0, 0, 0)` publish with `CV NOT IMPLEMENTED` warning as placeholder

  > 📝 **Design note — fixed camera coordinate frames:**
  > Because the overhead camera never moves, the transform from
  > `overhead_camera_link` to `world` is constant. It only needs to be looked
  > up once, unlike the arm camera which changes with every joint movement.

- [x] Registered in `setup.py` as `overhead_camera_localizer`
- [x] ✅ Tested: node starts, logs RGB and depth diagnostics, publishes dummy location

---

### Phase 8: Gripper and Hard-Coded Pick Motion

**Goal:** Attach a gripper to the arm's tool0 link, wire it up as a controller, and write a Python node that moves the arm through a complete pick-and-place sequence using hard-coded joint angles.

> 💡 **Why hard-code joint angles instead of using IK?** Inverse kinematics (IK) computes joint angles from a desired end-effector position automatically — but it requires additional packages (like MoveIt 2) and significant setup. For now, joint angles are determined manually (using the Gazebo GUI or trial and error) and hard-coded directly. This is valid for a demo.

---

#### Gripper Design Decision

**Option 1 (chosen): Custom two-finger gripper**
Built from box primitives directly in URDF. No external dependencies, fully under our control. Physics interaction with a sphere is imperfect (flat fingers on a round apple can slip), but sufficient for a demo.

**Option 2 (future upgrade): Robotiq 2F-85**
The industry-standard gripper for UR arms. More realistic physics and appearance. To switch:
1. Remove the `BEGIN CUSTOM GRIPPER` / `END CUSTOM GRIPPER` block in `urdf/ur3e_gz.urdf.xacro`
2. Clone the Robotiq ROS 2 description package and include its xacro macro attached to `tool0`
3. Replace the custom gripper joints in the `<ros2_control>` block with the Robotiq joint config
4. Update `config/ros2_controllers.yaml` to use the Robotiq controller
5. Update `pick_and_place.py` — Robotiq uses an action interface (`/robotiq_gripper_controller/gripper_cmd`) rather than a position topic

The code is structured with comments marking every place that would need to change for this swap.

---

#### 8.1 Add the Gripper to the URDF ✅

- [x] Open `urdf/ur3e_gz.urdf.xacro`
- [x] Added `gripper_base_link` (palm: 12 cm × 6 cm × 4 cm) with a fixed joint to `tool0`
- [x] Added `left_finger_link` — prismatic joint sliding along +X, limits −1 mm to 51 mm (0 = closed, 50 mm = open)
- [x] Added `right_finger_link` — prismatic joint sliding along −X, mirrored
- [x] Added `left_finger_joint` and `right_finger_joint` to the `<ros2_control>` block with position command/state interfaces
- [x] Both joints given `<dynamics damping="0.5" friction="0.0"/>` for stable controller response
- [x] All gripper code wrapped in `BEGIN CUSTOM GRIPPER` / `END CUSTOM GRIPPER` comment blocks for easy identification and future swap

  > 💡 **Fixed joint vs prismatic joint:**
  > - `fixed`: two links are rigidly connected — no movement
  > - `prismatic`: one link slides along an axis — this is how fingers open/close
  > - `revolute`: one link rotates around an axis — this is how arm joints work

  > ⚠️ **Don't forget the ros2_control block.** Just adding URDF links isn't enough — the finger joints must also be listed in the `<ros2_control>` block or the controller_manager won't know about them.

  > ⚠️ **Joint limits must have a 1 mm buffer from exact zero.** gz_ros2_control's `JointSaturationLimiter` fires a constant error stream when a joint rests exactly at a limit boundary (IEEE negative zero issue). Setting `lower="-0.001"` and `upper="0.051"` prevents this without affecting physical behavior.

---

#### 8.2 Wire the Gripper into the Controller ✅

Rather than adding a separate `JointGroupPositionController` for the gripper, the finger joints were added directly to the existing `joint_trajectory_controller`. This is more stable — `JointGroupPositionController` with `gz_ros2_control`'s default `position_proportional_gain=0.1` is too weak to reliably drive small prismatic joints, causing physics instability at joint limits.

- [x] Open `config/ros2_controllers.yaml`
- [x] Added `left_finger_joint` and `right_finger_joint` to the `joints` list under `joint_trajectory_controller`
- [x] Added `allow_partial_joints_goal: true` — allows sending a trajectory that specifies only the finger joints (leaving the arm at its current pose) or only the arm (leaving the gripper at its current pose)
- [x] Updated `home_pose.py` to include both finger joints at `0.0` (closed) in the `HOME_POSE` dict
- [x] No separate gripper spawner needed — launch chain is unchanged: spawn_robot → joint_state_broadcaster → joint_trajectory_controller → home_pose

  > 💡 **Why fold the gripper into the JTC?** The `JointTrajectoryController` is well-tested, respects joint limits cleanly, and already handles all 6 arm joints. `allow_partial_joints_goal: true` gives you the flexibility to command just the fingers or just the arm without needing separate controllers.

  > 💡 **Gripper command topic:** The gripper now shares `/joint_trajectory_controller/joint_trajectory`. Send a `JointTrajectory` message with only the finger joints named — the controller holds the arm at its current position:
  > ```bash
  > # Open gripper
  > ros2 topic pub --once /joint_trajectory_controller/joint_trajectory \
  >   trajectory_msgs/msg/JointTrajectory '{
  >     joint_names: [left_finger_joint, right_finger_joint],
  >     points: [{positions: [0.05, 0.05], time_from_start: {sec: 2}}]
  >   }'
  > # Close gripper
  > ros2 topic pub --once /joint_trajectory_controller/joint_trajectory \
  >   trajectory_msgs/msg/JointTrajectory '{
  >     joint_names: [left_finger_joint, right_finger_joint],
  >     points: [{positions: [0.0, 0.0], time_from_start: {sec: 2}}]
  >   }'
  > ```

- [x] Rebuild and relaunch
- [x] ✅ `ros2 control list_controllers` shows `joint_trajectory_controller` active (gripper included)
- [x] ✅ Gripper opens and closes reliably via topic commands

---

#### 8.3 Find the Hard-Coded Joint Angles

Before writing the pick node, you need to know the actual joint angles for each step of the motion. Do this experimentally — launch the simulation, send commands, and record what works.

- [ ] Launch the simulation
- [ ] Use the JointTrajectory command (from Phase 4) to move the arm to each pose you need:
  - [ ] **Home pose** — arm raised, out of the way, safe starting position
  - [ ] **Approach pose** — arm above the apple, ~15 cm higher than the apple's center
  - [ ] **Grasp pose** — arm down to apple level, gripper open, centered over the apple
  - [ ] **Lift pose** — arm raised back up while holding the apple (~15 cm above apple height)
  - [ ] **Transport pose** — arm rotated toward the shelf (`shoulder_pan` rotated 180° from home), raised safely
  - [ ] **Place pose** — arm lowered to the target shelf level, above the desired shelf compartment

  > 💡 **How to find angles:** Send a trajectory command, watch what happens, note the values. Run:
  > ```bash
  > ros2 topic echo /joint_states --once
  > ```
  > This prints the current joint positions — copy these numbers for your script.

  > ⚠️ **Check for collisions at every pose.** Watch the Gazebo GUI carefully. If the arm hits the table, the shelf, or itself, pick a different angle. Collisions in simulation can freeze the physics or launch the apple across the room.

  > 💡 **The apple is at a known, fixed location** — you defined it in `grocery_world.sdf`. So the grasp pose joint angles are fixed too. Calculate or adjust until the gripper is centered over the apple position you set.

- [ ] Record all 6 joint angles (in radians) for each of the 6 poses in a comment block for use in the next step

---

#### 8.4 Write the Hard-Coded Pick Node

- [ ] Create `ur3e_gazebo/hard_coded_pick.py`
- [ ] The node should:
  - [ ] On startup, wait 2 seconds for all controllers to be ready
  - [ ] Execute the pick-and-place sequence step by step:
    1. **Move to home pose** — publish to `/joint_trajectory_controller/joint_trajectory`
    2. **Wait** for the motion to complete (use `time.sleep()` with generous margin)
    3. **Open gripper** — publish `[left_finger_joint, right_finger_joint]` = `[0.05, 0.05]` to `/joint_trajectory_controller/joint_trajectory`
    4. **Move to approach pose**
    5. **Wait**
    6. **Move to grasp pose**
    7. **Wait**
    8. **Close gripper** — publish `[0.0, 0.0]` to `/joint_trajectory_controller/joint_trajectory`
    9. **Wait** (give the gripper time to close — ~2 seconds)
    10. **Move to lift pose**
    11. **Wait**
    12. **Move to transport pose**
    13. **Wait**
    14. **Move to place pose**
    15. **Wait**
    16. **Open gripper** — release the apple
    17. **Wait**
    18. **Move back to home pose**
    19. Log "Pick and place complete!" and shut down

  > 💡 **`time.sleep()` vs proper action waiting:** Using `time.sleep()` is simple and fine for a demo. A production system would use action clients to wait for the controller to confirm completion. Don't over-engineer it now — `sleep()` works.

  > ⚠️ **The apple might not actually stay in the gripper.** Grasping in Gazebo is tricky — physics contact between the fingers and a sphere is often unstable. If the apple slips, try:
  > - Making the finger collision surfaces slightly larger
  > - Reducing simulation speed (add `-v 4 --physics-engine bullet` to gz args — Bullet handles contacts better)
  > - As a last resort, use a "sticky gripper" hack: a Gazebo plugin that temporarily welds the object to the gripper on contact. Ask Claude Code about it if needed.

  > 💡 **Add lots of `rclpy.logging` calls.** Print what the node is doing at each step:
  > ```python
  > self.get_logger().info('Moving to approach pose...')
  > ```
  > This makes debugging much easier — you can see exactly where the sequence is when something goes wrong.

  > ⚠️ **The node must be running AFTER the launch file is up.** Don't bake this node into the launch file automatically — run it manually in a second terminal after the simulation is stable. Otherwise the arm will start moving before Gazebo has fully loaded, which causes unpredictable behaviour.

- [ ] Register in `setup.py` as `hard_coded_pick`
- [ ] Rebuild: `colcon build --packages-select ur3e_gazebo && source install/setup.bash`

---

#### 8.5 Test the Full Pick-and-Place Sequence

- [ ] Terminal 1 — Launch the simulation:
  ```bash
  ros2 launch ur3e_gazebo ur3e_gazebo.launch.py
  ```
- [ ] Wait for both controllers to report active: `joint_state_broadcaster` and `joint_trajectory_controller` (gripper is now part of the trajectory controller — no third controller needed)
- [ ] Terminal 2 — Run the pick node:
  ```bash
  ros2 run ur3e_gazebo hard_coded_pick
  ```
- [ ] Watch the Gazebo GUI and verify each step:
  - [ ] Arm moves to home ✅
  - [ ] Gripper opens ✅
  - [ ] Arm descends to apple ✅
  - [ ] Gripper closes around apple ✅
  - [ ] Arm lifts (apple should come with it) ✅
  - [ ] Arm rotates toward shelf ✅
  - [ ] Arm places apple on shelf ✅
  - [ ] Gripper opens, apple stays on shelf ✅
  - [ ] Arm returns home ✅

  > ⚠️ **If the apple doesn't come with the gripper** — see the note in 8.4 about physics contact. This is the hardest part of robotic grasping in simulation, even for experts. Don't panic.

  > ⚠️ **If the arm collides with the table/shelf** — slow down the trajectory by increasing `time_from_start` values and re-check your approach/place joint angles.

- [ ] ✅ Final check: take a screenshot of the apple on the shelf for the team meeting
- [ ] Commit everything: all new SDF models, the modified xacro, the new Python nodes, and the updated launch file