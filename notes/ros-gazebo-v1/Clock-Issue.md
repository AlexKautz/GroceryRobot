# Clock Issue — Sim Broken (Investigate Next Session)

**Date discovered:** 2026-04-23
**Status:** UNRESOLVED

---

## Symptom

After clicking Play in Gazebo, the controller_manager repeatedly logs:

```
[controller_manager]: No clock received, using time argument instead!
Check your node's clock configuration (use_sim_time parameter)
and if a valid clock source is available
```

The simulation does not behave correctly (pick_and_place fails).

---

## What was tried

1. **Added `use_sim_time: true` to `config/ros2_controllers.yaml`** under `controller_manager.ros__parameters` — warning persists.
2. The `/clock` bridge IS configured in the launch file (line 62–68 of `launch/ur3e_gazebo.launch.py`) — bridges `/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock`.

---

## Suspected cause

The `gz_ros2_control` plugin creates an internal ROS node inside the Gazebo process and subscribes to `/clock`. Due to a DDS discovery timing issue (or a bug in gz_ros2_control on Gazebo Ionic), that subscription does not receive messages from the `ros_gz_bridge` publisher even after Play is clicked.

---

## Things to investigate next session

- [ ] Run `ros2 topic hz /clock` after clicking Play — verify the bridge is actually publishing
- [ ] Run `ros2 topic list` after clicking Play — check `/clock` appears
- [ ] Check if the warning was present BEFORE the April 23rd session (i.e. was it introduced by any recent change?)
- [ ] Try passing `use_sim_time` directly in the URDF plugin block in `urdf/ur3e_gz.urdf.xacro`:
  ```xml
  <plugin filename="gz_ros2_control-system" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
    <parameters>$(find ur3e_gazebo)/config/ros2_controllers.yaml</parameters>
    <use_sim_time>true</use_sim_time>
  </plugin>
  ```
- [ ] Check gz_ros2_control GitHub issues for "No clock received" on Gazebo Ionic
- [ ] Try adding an explicit `<plugin name='gz::sim::systems::Clock' filename='gz-sim-clock-system'/>` to `worlds/grocery_world.sdf`

---

## Files relevant to this issue

| File | Relevance |
|------|-----------|
| `launch/ur3e_gazebo.launch.py` | Defines the `/clock` bridge (line 62–68) |
| `config/ros2_controllers.yaml` | `use_sim_time: true` added here (may or may not help) |
| `urdf/ur3e_gz.urdf.xacro` | gz_ros2_control plugin definition — may need `<use_sim_time>` tag |
| `worlds/grocery_world.sdf` | May need a Clock system plugin |
