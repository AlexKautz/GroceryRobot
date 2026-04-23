**Alex Kautz**
4/23/26

# Work Sesion Apr 23rd
The goal of this work sesion is to do the folowing 2 things:
1. Add a realistic Apple model to the scene in place of the sphere. (We can find one online).
2. Somehow see what the cameras see, such as saving their view to a file or better yet seeing it live.


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

- [ ] Stage and commit:
  ```bash
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/models/
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/worlds/grocery_world.sdf
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/setup.py
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/launch/ur3e_gazebo.launch.py
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/urdf/ur3e_gz.urdf.xacro
  git add code/ros-gazebo-v1/ros2_ws/src/ur3e_gazebo/ur3e_gazebo/
  git commit -m "Replace sphere apple with realistic orange mesh model, rename apple→orange everywhere"
  ```
