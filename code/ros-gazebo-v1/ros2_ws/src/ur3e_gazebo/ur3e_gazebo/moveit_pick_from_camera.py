#!/usr/bin/env python3

import time
from copy import deepcopy

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PointStamped, Pose, PoseStamped, Quaternion
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

from shape_msgs.msg import SolidPrimitive
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    BoundingVolume,
    MoveItErrorCodes,
)

# Map MoveItErrorCodes.val integers to human-readable names for logging.
_MOVEIT_ERROR_NAMES = {v: k for k, v in vars(MoveItErrorCodes).items() if isinstance(v, int)}


class MoveItPickFromCamera(Node):
    """
    Camera-guided pick node for simulated UR3e.

    Input:
        /overhead_camera/apple_location  geometry_msgs/msg/PointStamped

    Output:
        MoveIt action goal to /move_action

    Optional gripper output:
        JointTrajectory command to a gripper trajectory topic.
    """

    def __init__(self):
        super().__init__('moveit_pick_from_camera')

        # ---------------- Parameters ----------------

        self.declare_parameter('apple_topic', '/overhead_camera/apple_location')
        self.declare_parameter('move_group_action', '/move_action')
        self.declare_parameter('planning_group', 'ur_manipulator')
        self.declare_parameter('eef_link', 'tool0')

        # Motion behavior
        self.declare_parameter('plan_only', False)
        self.declare_parameter('allowed_planning_time', 5.0)
        self.declare_parameter('num_planning_attempts', 10)
        self.declare_parameter('velocity_scaling', 0.05)
        self.declare_parameter('acceleration_scaling', 0.05)

        # Goal tolerances
        self.declare_parameter('position_tolerance', 0.03)
        self.declare_parameter('orientation_tolerance', 3.14)

        # Pick offsets, in meters
        self.declare_parameter('pre_grasp_z_offset', 0.20)
        self.declare_parameter('grasp_z_offset', 0.03)
        self.declare_parameter('lift_z_offset', 0.25)

        # Optional fixed place target, in world frame
        self.declare_parameter('do_place', False)
        self.declare_parameter('place_x', -0.40)
        self.declare_parameter('place_y', 0.00)
        self.declare_parameter('place_z', 0.30)
        self.declare_parameter('pre_place_z_offset', 0.15)

        # Tool orientation.
        # This is only a starting guess. Tune this for your UR3e gripper.
        self.declare_parameter('tool_qx', 0.0)
        self.declare_parameter('tool_qy', 1.0)
        self.declare_parameter('tool_qz', 0.0)
        self.declare_parameter('tool_qw', 0.0)

        # Gripper command.
        # Change topic if your gripper has a separate controller.
        self.declare_parameter('gripper_topic', '/joint_trajectory_controller/joint_trajectory')
        self.declare_parameter('left_finger_joint', 'left_finger_joint')
        self.declare_parameter('right_finger_joint', 'right_finger_joint')
        self.declare_parameter('gripper_open', 0.05)
        self.declare_parameter('gripper_closed', -0.006)
        self.declare_parameter('gripper_move_time', 1.0)
        self.declare_parameter('step_settle_time', 4.0)

        self.apple_topic = self.get_parameter('apple_topic').value
        self.move_group_action = self.get_parameter('move_group_action').value
        self.planning_group = self.get_parameter('planning_group').value
        self.eef_link = self.get_parameter('eef_link').value

        self.plan_only = self.get_parameter('plan_only').value
        self.allowed_planning_time = self.get_parameter('allowed_planning_time').value
        self.num_planning_attempts = self.get_parameter('num_planning_attempts').value
        self.velocity_scaling = self.get_parameter('velocity_scaling').value
        self.acceleration_scaling = self.get_parameter('acceleration_scaling').value

        self.position_tolerance = self.get_parameter('position_tolerance').value
        self.orientation_tolerance = self.get_parameter('orientation_tolerance').value

        self.pre_grasp_z_offset = self.get_parameter('pre_grasp_z_offset').value
        self.grasp_z_offset = self.get_parameter('grasp_z_offset').value
        self.lift_z_offset = self.get_parameter('lift_z_offset').value

        self.do_place = self.get_parameter('do_place').value
        self.place_x = self.get_parameter('place_x').value
        self.place_y = self.get_parameter('place_y').value
        self.place_z = self.get_parameter('place_z').value
        self.pre_place_z_offset = self.get_parameter('pre_place_z_offset').value

        self.tool_orientation = Quaternion()
        self.tool_orientation.x = self.get_parameter('tool_qx').value
        self.tool_orientation.y = self.get_parameter('tool_qy').value
        self.tool_orientation.z = self.get_parameter('tool_qz').value
        self.tool_orientation.w = self.get_parameter('tool_qw').value

        self.gripper_topic = self.get_parameter('gripper_topic').value
        self.left_finger_joint = self.get_parameter('left_finger_joint').value
        self.right_finger_joint = self.get_parameter('right_finger_joint').value
        self.gripper_open = self.get_parameter('gripper_open').value
        self.gripper_closed = self.get_parameter('gripper_closed').value
        self.gripper_move_time = self.get_parameter('gripper_move_time').value
        self.step_settle_time = self.get_parameter('step_settle_time').value

        # ---------------- ROS interfaces ----------------

        self._move_group_client = ActionClient(
            self,
            MoveGroup,
            self.move_group_action,
        )

        self._gripper_pub = self.create_publisher(
            JointTrajectory,
            self.gripper_topic,
            10,
        )

        self._apple_sub = self.create_subscription(
            PointStamped,
            self.apple_topic,
            self._apple_callback,
            10,
        )

        self._busy = False
        self._sequence = []
        self._active_step_name = None
        self._step_start_time: float = 0.0
        self._retry_after: float = 0.0   # wall-clock time before next pick is allowed

        self.get_logger().info('=' * 60)
        self.get_logger().info('moveit_pick_from_camera started')
        self.get_logger().info('=' * 60)
        self.get_logger().info(f'  apple_topic:          {self.apple_topic}')
        self.get_logger().info(f'  move_group_action:    {self.move_group_action}')
        self.get_logger().info(f'  planning_group:       {self.planning_group}')
        self.get_logger().info(f'  eef_link:             {self.eef_link}')
        self.get_logger().info(f'  plan_only:            {self.plan_only}')
        self.get_logger().info(f'  allowed_planning_time:{self.allowed_planning_time}s')
        self.get_logger().info(f'  num_planning_attempts:{self.num_planning_attempts}')
        self.get_logger().info(f'  velocity_scaling:     {self.velocity_scaling}')
        self.get_logger().info(f'  position_tolerance:   {self.position_tolerance}m')
        self.get_logger().info(f'  pre_grasp_z_offset:   {self.pre_grasp_z_offset}m')
        self.get_logger().info(f'  grasp_z_offset:       {self.grasp_z_offset}m')
        self.get_logger().info(f'  lift_z_offset:        {self.lift_z_offset}m')
        self.get_logger().info(f'  gripper_topic:        {self.gripper_topic}')
        self.get_logger().info(f'  left_finger_joint:    {self.left_finger_joint}')
        self.get_logger().info(f'  right_finger_joint:   {self.right_finger_joint}')
        self.get_logger().info(f'  gripper_open:         {self.gripper_open}m')
        self.get_logger().info(f'  gripper_closed:       {self.gripper_closed}m')
        self.get_logger().info(f'  gripper_move_time:    {self.gripper_move_time}s')
        self.get_logger().info(f'  step_settle_time:     {self.step_settle_time}s')
        self.get_logger().info(f'  tool_orientation:     qx={self.tool_orientation.x} qy={self.tool_orientation.y} qz={self.tool_orientation.z} qw={self.tool_orientation.w}')
        self.get_logger().info('=' * 60)
        self.get_logger().info('Waiting for apple detection...')

    # ------------------------------------------------------------------ #
    # Apple callback
    # ------------------------------------------------------------------ #

    def _apple_callback(self, msg: PointStamped):
        """
        Receives detected apple location and starts one pick sequence.
        Ignores new detections while a sequence is already running.
        """

        if self._busy:
            self.get_logger().debug('Apple detection received but already busy — ignoring.')
            return

        now = time.monotonic()
        if now < self._retry_after:
            self.get_logger().info(
                f'Apple detection received but in cooldown — '
                f'{self._retry_after - now:.1f}s remaining.',
                throttle_duration_sec=2.0,
            )
            return

        self._busy = True

        self.get_logger().info('-' * 60)
        self.get_logger().info('APPLE DETECTED — starting pick sequence')
        self.get_logger().info(
            f'  frame_id: [{msg.header.frame_id}]  '
            f'x={msg.point.x:.4f}  y={msg.point.y:.4f}  z={msg.point.z:.4f}'
        )

        self.get_logger().info('Building pick sequence from detected point...')
        self._build_sequence_from_point(msg)
        self.get_logger().info(f'Sequence has {len(self._sequence)} steps: {[s for s, _ in self._sequence]}')

        self.get_logger().info(f'Opening gripper to {self.gripper_open}m before approach...')
        self._send_gripper(self.gripper_open)
        self.get_logger().info(f'Sleeping {self.gripper_move_time}s for gripper to open...')
        time.sleep(self.gripper_move_time)
        self.get_logger().info('Gripper open wait done.')

        self._send_next_pose()

    # ------------------------------------------------------------------ #
    # Sequence construction
    # ------------------------------------------------------------------ #

    def _build_sequence_from_point(self, apple_msg: PointStamped):
        """
        Creates MoveIt pose goals from detected apple point.
        """

        frame_id = apple_msg.header.frame_id
        if frame_id == '':
            self.get_logger().warn('apple_location has empty frame_id — defaulting to "world"')
            frame_id = 'world'

        object_x = apple_msg.point.x
        object_y = apple_msg.point.y
        object_z = apple_msg.point.z

        pre_grasp = self._make_pose(
            frame_id,
            object_x,
            object_y,
            object_z + self.pre_grasp_z_offset,
        )

        grasp = self._make_pose(
            frame_id,
            object_x,
            object_y,
            object_z + self.grasp_z_offset,
        )

        lift = self._make_pose(
            frame_id,
            object_x,
            object_y,
            object_z + self.lift_z_offset,
        )

        self.get_logger().info(
            f'  pre_grasp: ({object_x:.3f}, {object_y:.3f}, {object_z + self.pre_grasp_z_offset:.3f}) frame={frame_id}'
        )
        self.get_logger().info(
            f'  grasp:     ({object_x:.3f}, {object_y:.3f}, {object_z + self.grasp_z_offset:.3f}) frame={frame_id}'
        )
        self.get_logger().info(
            f'  lift:      ({object_x:.3f}, {object_y:.3f}, {object_z + self.lift_z_offset:.3f}) frame={frame_id}'
        )

        self._sequence = [
            ('pre_grasp', pre_grasp),
            ('grasp', grasp),
            ('lift', lift),
        ]

        if self.do_place:
            pre_place = self._make_pose(
                'world',
                self.place_x,
                self.place_y,
                self.place_z + self.pre_place_z_offset,
            )

            place = self._make_pose(
                'world',
                self.place_x,
                self.place_y,
                self.place_z,
            )

            retreat = self._make_pose(
                'world',
                self.place_x,
                self.place_y,
                self.place_z + self.pre_place_z_offset,
            )

            self.get_logger().info(
                f'  pre_place: ({self.place_x:.3f}, {self.place_y:.3f}, {self.place_z + self.pre_place_z_offset:.3f}) frame=world'
            )
            self.get_logger().info(
                f'  place:     ({self.place_x:.3f}, {self.place_y:.3f}, {self.place_z:.3f}) frame=world'
            )
            self.get_logger().info(
                f'  retreat:   ({self.place_x:.3f}, {self.place_y:.3f}, {self.place_z + self.pre_place_z_offset:.3f}) frame=world'
            )

            self._sequence.extend([
                ('pre_place', pre_place),
                ('place', place),
                ('retreat', retreat),
            ])

    def _make_pose(self, frame_id: str, x: float, y: float, z: float) -> PoseStamped:
        pose = PoseStamped()
        pose.header.frame_id = frame_id
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = z
        pose.pose.orientation = deepcopy(self.tool_orientation)
        return pose

    # ------------------------------------------------------------------ #
    # MoveIt action sequence
    # ------------------------------------------------------------------ #

    def _send_next_pose(self):
        if len(self._sequence) == 0:
            self.get_logger().info('=' * 60)
            self.get_logger().info('Pick sequence COMPLETE — ready for next detection.')
            self.get_logger().info('=' * 60)
            self._busy = False
            return

        step_name, pose = self._sequence.pop(0)
        self._active_step_name = step_name
        self._step_start_time = time.monotonic()

        self.get_logger().info(
            f'[{step_name}] Sending MoveIt goal — '
            f'target: ({pose.pose.position.x:.3f}, {pose.pose.position.y:.3f}, {pose.pose.position.z:.3f}) '
            f'frame={pose.header.frame_id}  '
            f'steps_remaining_after_this={len(self._sequence)}'
        )

        goal_msg = self._make_move_group_goal(pose)

        self.get_logger().info(f'[{step_name}] Waiting for MoveGroup action server at {self.move_group_action}...')
        if not self._move_group_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(
                f'[{step_name}] TIMEOUT: MoveGroup action server not available at {self.move_group_action} '
                f'— is "ros2 launch ur3e_moveit_config move_group.launch.py" running?'
            )
            self._retry_after = time.monotonic() + 5.0
            self._busy = False
            return

        self.get_logger().info(f'[{step_name}] MoveGroup server found. Sending goal...')
        send_future = self._move_group_client.send_goal_async(goal_msg)
        send_future.add_done_callback(self._goal_response_callback)
        self.get_logger().info(f'[{step_name}] Goal sent — waiting for acceptance...')

    def _goal_response_callback(self, future):
        goal_handle = future.result()
        step = self._active_step_name
        elapsed = time.monotonic() - self._step_start_time

        if not goal_handle.accepted:
            self.get_logger().error(
                f'[{step}] Goal REJECTED by MoveGroup after {elapsed:.2f}s. '
                f'Check that planning_group="{self.planning_group}" is correct '
                f'and that MoveIt has a valid robot state.'
            )
            self._retry_after = time.monotonic() + 5.0
            self._busy = False
            return

        self.get_logger().info(
            f'[{step}] Goal ACCEPTED by MoveGroup after {elapsed:.2f}s — now planning+executing...'
        )

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._move_result_callback)

    def _move_result_callback(self, future):
        result = future.result().result
        error_code = result.error_code.val
        step = self._active_step_name
        elapsed = time.monotonic() - self._step_start_time
        error_name = _MOVEIT_ERROR_NAMES.get(error_code, f'UNKNOWN({error_code})')

        if error_code != MoveItErrorCodes.SUCCESS:
            self.get_logger().error(
                f'[{step}] MoveIt FAILED after {elapsed:.2f}s — '
                f'error_code={error_code} ({error_name})'
            )
            self.get_logger().error(
                f'[{step}] Aborting sequence. Retrying in 5s.'
            )
            self._retry_after = time.monotonic() + 5.0
            self._busy = False
            return

        self.get_logger().info(
            f'[{step}] MoveIt SUCCESS after {elapsed:.2f}s (error_code={error_code})'
        )

        # Gripper actions at important points
        if self._active_step_name == 'grasp':
            self.get_logger().info(f'[{step}] At grasp position — closing gripper to {self.gripper_closed}m...')
            self._send_gripper(self.gripper_closed)
            self.get_logger().info(f'[{step}] Sleeping {self.gripper_move_time}s for gripper to close...')
            time.sleep(self.gripper_move_time)
            self.get_logger().info(f'[{step}] Gripper close wait done.')

        elif self._active_step_name == 'place':
            self.get_logger().info(f'[{step}] At place position — opening gripper to {self.gripper_open}m...')
            self._send_gripper(self.gripper_open)
            self.get_logger().info(f'[{step}] Sleeping {self.gripper_move_time}s for gripper to open...')
            time.sleep(self.gripper_move_time)
            self.get_logger().info(f'[{step}] Gripper open wait done.')

        self.get_logger().info(f'[{step}] Settling for {self.step_settle_time}s before next move...')
        time.sleep(self.step_settle_time)
        self.get_logger().info(f'[{step}] Settle done.')

        self._send_next_pose()

    # ------------------------------------------------------------------ #
    # MoveIt goal construction
    # ------------------------------------------------------------------ #

    def _make_move_group_goal(self, target_pose: PoseStamped) -> MoveGroup.Goal:
        """
        Builds a MoveGroup action goal using position and orientation constraints.
        """

        goal = MoveGroup.Goal()

        goal.request.group_name = self.planning_group
        goal.request.num_planning_attempts = int(self.num_planning_attempts)
        goal.request.allowed_planning_time = float(self.allowed_planning_time)
        goal.request.max_velocity_scaling_factor = float(self.velocity_scaling)
        goal.request.max_acceleration_scaling_factor = float(self.acceleration_scaling)

        constraints = Constraints()
        constraints.name = 'camera_guided_pose_goal'

        # Position constraint around the target point
        position_constraint = PositionConstraint()
        position_constraint.header.frame_id = target_pose.header.frame_id
        position_constraint.link_name = self.eef_link
        position_constraint.weight = 1.0

        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [float(self.position_tolerance)]

        sphere_pose = Pose()
        sphere_pose.position = target_pose.pose.position
        sphere_pose.orientation.w = 1.0

        region = BoundingVolume()
        region.primitives.append(sphere)
        region.primitive_poses.append(sphere_pose)

        position_constraint.constraint_region = region
        constraints.position_constraints.append(position_constraint)

        # Orientation constraint for the end-effector
        orientation_constraint = OrientationConstraint()
        orientation_constraint.header.frame_id = target_pose.header.frame_id
        orientation_constraint.link_name = self.eef_link
        orientation_constraint.orientation = target_pose.pose.orientation
        orientation_constraint.absolute_x_axis_tolerance = float(self.orientation_tolerance)
        orientation_constraint.absolute_y_axis_tolerance = float(self.orientation_tolerance)
        orientation_constraint.absolute_z_axis_tolerance = float(self.orientation_tolerance)
        orientation_constraint.weight = 1.0

        constraints.orientation_constraints.append(orientation_constraint)

        goal.request.goal_constraints.append(constraints)

        # Planning options
        goal.planning_options.plan_only = bool(self.plan_only)
        goal.planning_options.replan = True
        goal.planning_options.replan_attempts = 3
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True

        self.get_logger().debug(
            f'  goal details: group={self.planning_group}  eef={self.eef_link}  '
            f'frame={target_pose.header.frame_id}  '
            f'pos_tol={self.position_tolerance}m  ori_tol={self.orientation_tolerance}rad  '
            f'plan_time={self.allowed_planning_time}s  attempts={self.num_planning_attempts}  '
            f'plan_only={self.plan_only}  vel_scale={self.velocity_scaling}'
        )

        return goal

    # ------------------------------------------------------------------ #
    # Gripper command
    # ------------------------------------------------------------------ #

    def _send_gripper(self, finger_position: float):
        """
        Sends finger command. This is separate from MoveIt.
        If this does not move the gripper, use a dedicated gripper controller topic.
        """

        point = JointTrajectoryPoint()
        point.positions = [float(finger_position), float(finger_position)]
        point.time_from_start = Duration(
            sec=int(self.gripper_move_time),
            nanosec=int((self.gripper_move_time % 1.0) * 1e9),
        )

        msg = JointTrajectory()
        msg.joint_names = [
            self.left_finger_joint,
            self.right_finger_joint,
        ]
        msg.points = [point]

        self._gripper_pub.publish(msg)
        self.get_logger().info(
            f'  Gripper command published: joints={msg.joint_names}  '
            f'position={finger_position}m  duration={self.gripper_move_time}s  '
            f'topic={self.gripper_topic}'
        )


def main(args=None):
    rclpy.init(args=args)
    node = MoveItPickFromCamera()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
