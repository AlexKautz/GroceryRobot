# Pick-and-Place Reference

## Running the sequence

Launch the simulation and click Play, then in a second terminal:

```bash
ros2 run ur3e_gazebo pick_and_place
```

The full sequence takes ~90 seconds (9 steps × ~10 s each).

---

## World geometry

| Object | World position (x, y, z) |
|---|---|
| Apple center | (0.35, 0.0, 0.065) |
| Table surface | z ≈ 0.025 |
| Shelf middle board | x ≈ −0.40, z ≈ 0.300 |
| Arm base | (0.0, 0.0, 0.0) |

---

## Recorded joint positions

All values recorded via the `joint_control_panel` GUI during Phase 8.3.
Joint angles are in radians; finger positions are in meters (0 = closed, 0.05 = open).

### 1 — Home (start and end pose)
```
'shoulder_pan_joint':  +0.000,
'shoulder_lift_joint': -1.570,
'elbow_joint':         +1.570,
'wrist_1_joint':       -1.570,
'wrist_2_joint':       +0.000,
'wrist_3_joint':       +0.000,
# fingers: 0.0000  (closed)
```

### 2 — Approach (above apple, gripper open)
```
'shoulder_pan_joint':  -0.385,
'shoulder_lift_joint': -1.232,
'elbow_joint':         +1.352,
'wrist_1_joint':       -1.570,
'wrist_2_joint':       -1.571,
'wrist_3_joint':       +0.000,
# fingers: 0.0500  (open)
```

### 3 — Grasp position (gripper around apple, still open)
```
'shoulder_pan_joint':  -0.385,
'shoulder_lift_joint': -1.232,
'elbow_joint':         +1.706,
'wrist_1_joint':       -1.953,
'wrist_2_joint':       -1.571,
'wrist_3_joint':       +0.000,
# fingers: 0.0500  (open)
```

### 4 — Grip (same arm position, fingers closed)
```
'shoulder_pan_joint':  -0.385,
'shoulder_lift_joint': -1.232,
'elbow_joint':         +1.706,
'wrist_1_joint':       -1.953,
'wrist_2_joint':       -1.571,
'wrist_3_joint':       +0.000,
# fingers: -0.0060  (gripping)
```

### 5 — Lift (apple raised clear of table)
```
'shoulder_pan_joint':  -0.385,
'shoulder_lift_joint': -2.226,
'elbow_joint':         +1.425,
'wrist_1_joint':       -1.953,
'wrist_2_joint':       -1.571,
'wrist_3_joint':       +0.000,
# fingers: -0.0060  (gripping)
```

### 6 — Transport (rotated to face shelf)
```
'shoulder_pan_joint':  -3.283,
'shoulder_lift_joint': -2.120,
'elbow_joint':         +1.425,
'wrist_1_joint':       -1.953,
'wrist_2_joint':       -1.571,
'wrist_3_joint':       +0.000,
# fingers: -0.0060  (gripping)
```

### 7 — Place (lowered to shelf board)
```
'shoulder_pan_joint':  -3.283,
'shoulder_lift_joint': -1.754,
'elbow_joint':         +1.425,
'wrist_1_joint':       -1.953,
'wrist_2_joint':       -1.571,
'wrist_3_joint':       +0.000,
# fingers: -0.0060  (gripping)
```

### 8 — Release (same arm position, gripper open)
```
'shoulder_pan_joint':  -3.283,
'shoulder_lift_joint': -1.754,
'elbow_joint':         +1.425,
'wrist_1_joint':       -1.953,
'wrist_2_joint':       -1.571,
'wrist_3_joint':       +0.000,
# fingers: 0.0500  (open)
```

### 9 — Retract (arm raised clear of shelf)
```
'shoulder_pan_joint':  -3.283,
'shoulder_lift_joint': -2.371,
'elbow_joint':         +1.425,
'wrist_1_joint':       -1.953,
'wrist_2_joint':       -1.571,
'wrist_3_joint':       +0.000,
# fingers: 0.0500  (open)
```

---

## Timing

Configured in `ur3e_gazebo/pick_and_place.py` at the top of the file:

```python
MOVE_DURATION_SEC = 4.0   # seconds given to the arm to reach each pose
HOLD_SEC          = 2.0   # seconds to wait after arriving before the next step
```

---

## Joint control panel

To manually position the arm and record new values, use the interactive GUI:

```bash
ros2 run ur3e_gazebo joint_control_panel
```

Sliders for all 6 arm joints and the gripper, with live update mode and copy-to-clipboard output.
