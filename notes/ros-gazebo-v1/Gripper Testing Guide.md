# Gripper Testing Guide

## 1. Launch the simulation

```bash
cd ~/Code/ROS/GroceryRobot/code/ros-gazebo-v1/ros2_ws
source install/setup.bash
ros2 launch ur3e_gazebo ur3e_gazebo.launch.py
```

Click **Play** in Gazebo. Wait for the arm to move to home pose (~5 seconds after play).

---

## 2. Verify controllers are active

```bash
ros2 control list_controllers
```

Expected output:
```
joint_state_broadcaster[joint_state_broadcaster/JointStateBroadcaster] active
joint_trajectory_controller[joint_trajectory_controller/JointTrajectoryController] active
```

---

## 3. Check joint positions

```bash
ros2 topic echo /joint_states --once
```

Expected: `left_finger_joint` and `right_finger_joint` both near `0.0` (closed).

---

## 4. Open the gripper

```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [left_finger_joint, right_finger_joint],
  points: [{positions: [0.05, 0.05], time_from_start: {sec: 2}}]
}'
```

Expected: both fingers slide outward over ~2 seconds.

---

## 5. Close the gripper

```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [left_finger_joint, right_finger_joint],
  points: [{positions: [0.0, 0.0], time_from_start: {sec: 2}}]
}'
```

Expected: both fingers slide back to closed position.

---

## 6. Move the arm + gripper together

Send all 8 joints in one message:

```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint, left_finger_joint, right_finger_joint],
  points: [{positions: [0.0, -1.57, 1.57, -1.57, 0.0, 0.0, 0.05, 0.05], time_from_start: {sec: 3}}]
}'
```

This moves the arm to home pose with the gripper open.

---

## 7. What to look for in logs

**Good signs:**
- `Successfully switched controllers!`
- `Home pose command sent`
- No repeated `out of limits` errors after startup

**Known noise (safe to ignore):**
- A few `out of limits` messages for `right_finger_joint` during the first second of controller activation — these should stop once the joint settles.
- `libEGL warning: egl: failed to create dri2 screen` — graphics driver warning, unrelated to control.

**Bad signs:**
- `out of limits` errors repeating every second indefinitely
- `Failed to activate controller`
- Gripper stops responding to commands after 1–2 cycles (if this happens, restart the simulation)
