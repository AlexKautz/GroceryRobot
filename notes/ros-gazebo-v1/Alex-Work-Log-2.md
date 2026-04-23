**Alex Kautz**
4/23/26

# Work Sesion Apr 23rd
The goal of this work sesion is to do the folowing 2 things:
1. Add a realistic Apple model to the scene in place of the sphere. (We can find one online).
2. Test the Pickup and Place hardcoded automation and fix it if needed.


## Claud Work Tasks (Claud Code via VSCode)

---

### Task 1: Replace the Sphere with a Realistic 3D Orange Model ✅ COMPLETE

**Decision:** No "apple" model was found on Gazebo Fuel. We switched to an orange (`Gambit/Orange` on Fuel), which is identical in shape and physics. All references to "apple" were renamed to "orange" across the entire codebase (SDF, pick_and_place.py, arm_camera_localizer.py, overhead_camera_localizer.py, urdf comments).

**Files changed:**
- `worlds/grocery_world.sdf` — orange model replaces sphere; visual uses mesh with pose correction
- `setup.py` — registers `models/orange/meshes/` so colcon installs the mesh files
- `models/orange/meshes/textured.dae` + `texture_map.png` — new mesh files (copied from Fuel download)
- `launch/ur3e_gazebo.launch.py` — resolves `package://` URIs to `file://` at launch time (see gotcha below)
- `urdf/ur3e_gz.urdf.xacro`, `pick_and_place.py`, `arm_camera_localizer.py`, `overhead_camera_localizer.py` — all "apple" renamed to "orange"

---

#### Step 1 — Find and Download a Mesh ✅

- [x] Searched Gazebo Fuel — "apple" returned no results
- [x] Used **`Gambit/Orange`** instead — same shape, realistic textured mesh
  - Downloaded zip contained: `model.config`, `model.sdf`, `textured.dae`, `textured.mtl`, `textured.obj`, `texture_map.png`, `thumbnails/`
  - Key files needed: `textured.dae` (mesh) + `texture_map.png` (texture the .dae references internally)

---

#### Step 2 — Add the Model to the Package ✅

- [x] Created `models/orange/meshes/` inside `ur3e_gazebo`
- [x] Copied `textured.dae` and `texture_map.png` into it (both must be in the same folder — the .dae references the texture by relative filename)

---

#### Step 3 — Register in `setup.py` ✅

- [x] Added to `data_files`:
  ```python
  ('share/' + package_name + '/models/orange/meshes', glob('models/orange/meshes/*')),
  ```
- [x] Rebuilt with `colcon build --packages-select ur3e_gazebo`

---

#### Step 4 — Replace the Sphere Visual in `grocery_world.sdf` ✅

- [x] Renamed model from `"apple"` → `"orange"`, link from `"apple_link"` → `"orange_link"`
- [x] Replaced `<visual>` sphere geometry with mesh:
  ```xml
  <visual name="visual">
    <pose>0.007 -0.035 -0.018 -1.5708 0 0</pose>
    <geometry>
      <mesh>
        <uri>package://ur3e_gazebo/models/orange/meshes/textured.dae</uri>
        <scale>1 1 1</scale>
      </mesh>
    </geometry>
  </visual>
  ```
- [x] Kept `<collision>` (sphere radius 0.04) and `<inertial>` blocks unchanged

> 📝 **Pose correction explained:** The mesh uses Y_UP axis (not Gazebo's Z_UP). The RPY `-1.5708 0 0` rotates it upright. The XYZ `0.007 -0.035 -0.018` corrects for the mesh's geometric center not being at the .dae file's origin — computed by finding the bounding box center of the vertex data and negating it after rotation.

> 📝 **Scale:** This mesh is already in meters (`scale 1 1 1`). The common `0.001` scale tip in the original plan only applies to meshes exported in millimeters — always check the vertex data range first.

---

#### Step 5 — Rebuild ✅

- [x] `colcon build --packages-select ur3e_gazebo` after every SDF edit
- [x] **Important gotcha:** The SDF is COPIED into `install/` at build time (ament_python package). Edits to the source SDF are NOT live — you must rebuild every time. This tripped us up once.

---

#### Step 6 — Launch and Verify ✅

- [x] Orange appears in Gazebo entity tree as `"orange"`
- [x] Orange mesh renders with texture (orange color, realistic shape)
- [x] Visual and collision sphere are aligned
- [x] No mesh URI errors in terminal

> 📝 **Gotcha — `package://` URIs in world SDF files don't resolve in Gazebo Ionic:** Gazebo's SDF parser cannot resolve `package://` URIs in world files even when the workspace is sourced. The fix was to update `launch/ur3e_gazebo.launch.py` to read the world SDF at launch time, replace all `package://ur3e_gazebo/` prefixes with the absolute `file://` path using Python string substitution, and write the result to a temp file. Gazebo then loads the temp file. This is now handled automatically on every launch.

---

#### Step 7 — Commit

- [X] Stage and commit:
  ```bash
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/models/
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/worlds/grocery_world.sdf
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/setup.py
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/launch/ur3e_gazebo.launch.py
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/urdf/ur3e_gz.urdf.xacro
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/ur3e_gazebo/
  git commit -m "Replace sphere apple with realistic orange mesh model, rename apple→orange everywhere"
  ```

---

### Task 2: Test the Pick-and-Place Automation and Fix It If Needed ✅ COMPLETE

**Outcome:** Sequence runs successfully end-to-end. The root problem was that the simulation runs at ~18% real-time speed on this machine, so the original wall-clock timing caused the node to advance to the next step before the arm had physically arrived. Fixed by switching the node to ROS simulation time.

**Fix applied — `pick_and_place.py`:**
- Added `use_sim_time=True` to the node so all timing uses `/clock` (simulation time, not wall clock)
- Replaced `time.monotonic()` with `self.get_clock().now()` for step advancement
- Changed `MOVE_DURATION_SEC = 2.0` and `HOLD_SEC = 0.0` (tuned for this machine; sim time, not wall clock)
- No rebuild required — Python changes take effect immediately on next `ros2 run`

**Key insight:** `MOVE_DURATION_SEC` and `HOLD_SEC` are now in **simulation seconds**, not wall-clock seconds. At 18% sim speed, 2 sim-seconds = ~11 wall-clock seconds. The node will automatically adapt to any machine's sim speed.

**The node:** `ur3e_gazebo/pick_and_place.py`
All tuning lives in that one file — no other files need to be changed.

**Key constants:**
| Constant | Location in file | What it controls |
|---|---|---|
| `MOVE_DURATION_SEC = 2.0` | top of file | Sim-seconds given to the arm to reach each pose |
| `HOLD_SEC = 0.0` | top of file | Sim-seconds to wait after arriving before the next step |
| `_GRIP = -0.006` | top of file | How tightly the gripper closes (meters, negative = inward) |
| `_HOME`, `_APPROACH`, `_GRASP`, `_LIFT`, `_TRANSPORT`, `_PLACE`, `_RETRACT` | pose dicts | Joint angles (radians) for each stage |

---

#### Step 1 — Set Up Two Terminals ✅

You need the sim running in one terminal and the pick node in another.

- [x] **Terminal 1** — start a fresh simulation:
  ```bash
  bash teardown.sh     # clear any stale processes first
  source /opt/ros/kilted/setup.bash
  source code/ros-gazebo-v1/ros2_ws/install/setup.bash
  ros2 launch ur3e_gazebo ur3e_gazebo.launch.py
  ```
- [x] Click **Play** in Gazebo
- [x] Wait until you see in the terminal:
  ```
  Configured and activated joint_trajectory_controller
  Home pose command sent — arm will reach pose in 3s.
  ```
  The arm should move to the home pose facing the table.

- [x] **Terminal 2** — source the workspace (same two source commands as above)

---

#### Step 2 — Run the Sequence ✅

- [x] In Terminal 2:
  ```bash
  ros2 run ur3e_gazebo pick_and_place
  ```
- [x] Sequence ran successfully end-to-end and printed `Sequence complete.`

---

#### Step 3 — Watch Each Stage and Record What Happens ✅

All 10 stages passed after switching to sim time.

- [x] **Stage 1 — open_gripper** ✅
- [x] **Stage 2 — approach** ✅
- [x] **Stage 3 — grasp_position** ✅
- [x] **Stage 4 — close_gripper** ✅
- [x] **Stage 5 — lift** ✅
- [x] **Stage 6 — transport** ✅
- [x] **Stage 7 — place** ✅
- [x] **Stage 8 — open_gripper** ✅
- [x] **Stage 9 — retract** ✅
- [x] **Stage 10 — home** ✅

#### Step 4 — Record Final Results ✅

- [x] ✅ Full sequence runs without arm collisions
- [x] ✅ Orange lifts off the table
- [x] ✅ Orange lands on the shelf
- [x] ✅ Arm returns home cleanly

```
Final tuned values:
MOVE_DURATION_SEC = 2.0   (sim seconds — auto-adapts to any machine speed)
HOLD_SEC          = 0.0

_APPROACH: pan=-0.385  lift=-1.232  elbow=1.352
_GRASP:    pan=-0.385  lift=-1.232  elbow=1.706
_LIFT:     pan=-0.385  lift=-2.226  elbow=1.425
_TRANSPORT: pan=-3.283  lift=-2.120  elbow=1.425
_PLACE:    pan=-3.283  lift=-1.754  elbow=1.425
_RETRACT:  pan=-3.283  lift=-2.371  elbow=1.425
_GRIP = -0.006
```

- [X] Commit:
