# Pick-and-Place Pose Tuning Guide (Phase 8.3)

The `pick_and_place.py` node has 5 arm poses that need to be verified and tuned
in the simulation before the sequence will work. Follow the steps below for each pose.

---

## World geometry reference

| Object          | World position (x, y, z)         |
|-----------------|----------------------------------|
| Apple center    | (0.35, 0.0, 0.065)               |
| Table surface   | z ≈ 0.025 (top face)             |
| Shelf bottom    | x ≈ -0.40, z ≈ 0.015            |
| Shelf middle    | x ≈ -0.40, z ≈ 0.300            |
| Arm base        | (0.0, 0.0, 0.0)                  |
| Gripper length  | ~14 cm from tool0 (palm + fingers)|

---

## Workflow for recording any pose

1. **Launch the simulation** and click Play:
   ```bash
   cd ~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws
   source install/setup.bash
   ros2 launch ur3e_gazebo ur3e_gazebo.launch.py
   ```

2. **Send the arm to an approximate starting position** using the ready-made
   command for that pose (see each pose section below).

3. **Observe the arm in Gazebo.** Adjust individual joints by tweaking the values
   and re-sending the command until the arm is in the right position.

4. **Record the final joint angles:**
   ```bash
   ros2 topic echo /joint_states --once
   ```
   Note: `/joint_states` lists joints **alphabetically**:
   ```
   elbow_joint
   left_finger_joint
   right_finger_joint
   shoulder_lift_joint
   shoulder_pan_joint
   wrist_1_joint
   wrist_2_joint
   wrist_3_joint
   ```
   Match each `position` value to its joint name and copy into `pick_and_place.py`.

---

## Poses to record

### 1. APPROACH — above the apple, gripper open

**Goal:** Tool0 directly above the apple center (x=0.35, y=0), about 10–15 cm
above the table surface. Wrist should point the gripper straight down so the
fingers are on either side of the apple in the X direction.

**Visual check in Gazebo:**
- Gripper is above the apple, not to the side
- Fingers are open and would clear the apple when lowering
- Arm is not in tension (elbows not at limits)

**Send this command to try the starting estimate:**
```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint, left_finger_joint, right_finger_joint],
  points: [{positions: [0.0, -1.40, 1.60, -1.70, 0.0, 0.0, 0.05, 0.05], time_from_start: {sec: 3}}]
}'
```

---

### 2. GRASP — gripper around the apple

**Goal:** Fingers on either side of the apple with the apple centered between
them. The finger **inner faces** should be at the apple's center height (z=0.065).
Fingers should NOT be touching the apple yet — they close in the next step.

**Visual check in Gazebo:**
- The apple is visible between the two fingers
- When fingers close (0.0), they should just contact the apple (radius=4 cm,
  so the finger inner faces need to be within ~4 cm of center)
- The gripper palm is above the apple, not the fingers pressing down on it

**Send this command to try the starting estimate:**
```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint, left_finger_joint, right_finger_joint],
  points: [{positions: [0.0, -1.10, 1.30, -1.75, 0.0, 0.0, 0.05, 0.05], time_from_start: {sec: 3}}]
}'
```

---

### 3. LIFT — apple raised off the table

**Goal:** Same XY footprint as GRASP but arm raised so the apple clears the
table surface by at least 5–10 cm. High enough to rotate the arm 180° to the
shelf without the apple clipping the table edge.

**Visual check in Gazebo:**
- Apple (still in gripper from GRASP) is clearly above the table
- No part of the arm or apple collides with the table during the LIFT motion

**Send this command to try the starting estimate** (gripper closed — apple is gripped):
```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint, left_finger_joint, right_finger_joint],
  points: [{positions: [0.0, -1.45, 1.55, -1.57, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 3}}]
}'
```

---

### 4. TRANSPORT — facing the shelf, apple held high

**Goal:** `shoulder_pan` rotated ~180° (≈ 3.14 rad) to face the shelf at x=-0.55.
The arm should be compact and high enough that the apple clears the table edge
during the rotation from LIFT to TRANSPORT.

**Visual check in Gazebo:**
- Send LIFT pose first, then TRANSPORT — watch the rotation for collisions
- Apple should arc cleanly over the table without hitting it
- Arm is pointing generally toward the shelf

**Send this command to try the starting estimate** (gripper closed — apple is gripped):
```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint, left_finger_joint, right_finger_joint],
  points: [{positions: [3.14, -1.50, 1.30, -1.57, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 4}}]
}'
```

---

### 5. PLACE — apple lowered to shelf board

**Goal:** Gripper lowered so the apple (radius 4 cm) sits on the middle shelf
board at world z ≈ 0.30. Apple center should be at z ≈ 0.34 (board + radius).
X position should be within the shelf depth (roughly x = -0.40).

**Visual check in Gazebo:**
- Apple (held by gripper) is directly above or on the shelf board
- When gripper opens, the apple would land on the board and stay there
- The arm doesn't clip the shelf back panel

**Send this command to try the starting estimate** (gripper closed — apple is gripped):
```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint, left_finger_joint, right_finger_joint],
  points: [{positions: [3.14, -1.10, 1.20, -1.57, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 3}}]
}'
```

---

## After tuning all 5 poses

1. Update the constants in `pick_and_place.py`
2. Rebuild:
   ```bash
   cd ~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws
   colcon build --symlink-install --packages-select ur3e_gazebo
   ```
   (With `--symlink-install`, edits to `.py` files take effect immediately —
   no rebuild needed unless you edit `setup.py`.)
3. Run the full sequence (Phase 8.4 / 8.5):
   ```bash
   ros2 run ur3e_gazebo pick_and_place
   ```

# Recorded Locations
## 1 Starting pose:
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  +0.000,
    'shoulder_lift_joint':  -1.570,
    'elbow_joint':  +1.570,
    'wrist_1_joint':  -1.570,
    'wrist_2_joint':  +0.000,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   0.0000,  (0=closed, 0.05=open)
    # right_finger_joint:  0.0000,
```
## 2 Positioning almost over apple and Opening the claw
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  -0.385,
    'shoulder_lift_joint':  -1.232,
    'elbow_joint':  +1.352,
    'wrist_1_joint':  -1.570,
    'wrist_2_joint':  -1.571,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   0.0500,  (0=closed, 0.05=open)
    # right_finger_joint:  0.0500,
```
## 3 Positioning over apple
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  -0.385,
    'shoulder_lift_joint':  -1.232,
    'elbow_joint':  +1.706,
    'wrist_1_joint':  -1.953,
    'wrist_2_joint':  -1.571,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   0.0500,  (0=closed, 0.05=open)
    # right_finger_joint:  0.0500,
```
## 4 Closing the claw
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  -0.385,
    'shoulder_lift_joint':  -1.232,
    'elbow_joint':  +1.706,
    'wrist_1_joint':  -1.953,
    'wrist_2_joint':  -1.571,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   -0.0060,  (0=closed, 0.05=open)
    # right_finger_joint:  -0.0060,
```
## Lifting the ball
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  -0.385,
    'shoulder_lift_joint':  -2.226,
    'elbow_joint':  +1.425,
    'wrist_1_joint':  -1.953,
    'wrist_2_joint':  -1.571,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   -0.0060,  (0=closed, 0.05=open)
    # right_finger_joint:  -0.0060,
```
## 5 Positioning almost over shelf
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  -3.283,
    'shoulder_lift_joint':  -2.120,
    'elbow_joint':  +1.425,
    'wrist_1_joint':  -1.953,
    'wrist_2_joint':  -1.571,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   -0.0060,  (0=closed, 0.05=open)
    # right_finger_joint:  -0.0060,
```
## 6 Placing on shelf
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  -3.283,
    'shoulder_lift_joint':  -1.754,
    'elbow_joint':  +1.425,
    'wrist_1_joint':  -1.953,
    'wrist_2_joint':  -1.571,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   -0.0060,  (0=closed, 0.05=open)
    # right_finger_joint:  -0.0060,
```
## 7 Opening claw
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  -3.283,
    'shoulder_lift_joint':  -1.754,
    'elbow_joint':  +1.425,
    'wrist_1_joint':  -1.953,
    'wrist_2_joint':  -1.571,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   0.0500,  (0=closed, 0.05=open)
    # right_finger_joint:  0.0500,
```
## 8 Moving arm
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  -3.283,
    'shoulder_lift_joint':  -2.371,
    'elbow_joint':  +1.425,
    'wrist_1_joint':  -1.953,
    'wrist_2_joint':  -1.571,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   0.0500,  (0=closed, 0.05=open)
    # right_finger_joint:  0.0500,
```
## 9 Return to starting pose
```
# Paste into pick_and_place.py:
    'shoulder_pan_joint':  +0.000,
    'shoulder_lift_joint':  -1.570,
    'elbow_joint':  +1.570,
    'wrist_1_joint':  -1.570,
    'wrist_2_joint':  +0.000,
    'wrist_3_joint':  +0.000,
    # left_finger_joint:   0.0000,  (0=closed, 0.05=open)
    # right_finger_joint:  0.0000,
```
