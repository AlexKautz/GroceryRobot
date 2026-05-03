import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped, PoseStamped
from moveit.planning import MoveItPy

from moveit_configs_utils import MoveItConfigsBuilder

class ApplePicker(Node):

    def __init__(self):
        super().__init__('apple_picker')

        # Load config the same way the launch file does
        moveit_config = (
            MoveItConfigsBuilder("ur3e", package_name="ur3e_moveit_config")
            .planning_pipelines(
                pipelines=["ompl"],
                default_planning_pipeline="ompl"
            )
            .to_moveit_configs()
        )

        self.moveit = MoveItPy(
            node_name='apple_picker_moveit',
            config_dict=moveit_config.to_dict()
        )
        self.arm = self.moveit.get_planning_component('ur_manipulator')

        self._apple_location = None
        self.create_subscription(
            PointStamped,
            '/overhead_camera/apple_location',
            self._apple_callback,
            10
        )
        
    def _apple_callback(self, msg: PointStamped):
        self._apple_location = msg

    def _build_pose(self, x, y, z) -> PoseStamped:
        """
        Build a PoseStamped with the end effector pointing straight down.
        The UR3e tool0 Z-axis points away from the flange — so to point
        the gripper downward, we rotate 180 deg around X (pi rotation).
        Quaternion for 180 deg around X: (x=1, y=0, z=0, w=0)
        """
        ps = PoseStamped()
        ps.header.frame_id = 'world'
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.pose.position.x = x
        ps.pose.position.y = y
        ps.pose.position.z = z
        # tool0 pointing straight down
        ps.pose.orientation.x = 1.0
        ps.pose.orientation.y = 0.0
        ps.pose.orientation.z = 0.0
        ps.pose.orientation.w = 0.0
        return ps

    def _move_to(self, pose: PoseStamped) -> bool:
        self.arm.set_start_state_to_current_state()
        self.arm.set_goal_state(
            pose_stamped_msg=pose,
            pose_link='tool0'
        )
        plan = self.arm.plan()
        if not plan:
            self.get_logger().error(f'Planning failed for pose: '
                f'({pose.pose.position.x:.3f}, '
                f'{pose.pose.position.y:.3f}, '
                f'{pose.pose.position.z:.3f})')
            return False
        self.moveit.execute(plan.trajectory, controllers=[])
        return True

    def pick_apple(self):
        if self._apple_location is None:
            self.get_logger().warn('No apple location received yet')
            return

        ax = self._apple_location.point.x
        ay = self._apple_location.point.y
        az = self._apple_location.point.z

        # tool0 must be FINGER_LENGTH above apple center for fingers to reach it
        # add APPROACH_OFFSET for a safe pre-grasp hover
        grasp_z    = az + self.FINGER_LENGTH
        approach_z = grasp_z + self.APPROACH_OFFSET

        self.get_logger().info(f'Apple at ({ax:.3f}, {ay:.3f}, {az:.3f})')
        self.get_logger().info(f'tool0 grasp Z = {grasp_z:.3f}  approach Z = {approach_z:.3f}')

        # 1. Move to approach pose (above apple)
        self.get_logger().info('Step 1: moving to pre-grasp...')
        if not self._move_to(self._build_pose(ax, ay, approach_z)):
            return

        # 2. Open gripper before descending
        self.get_logger().info('Step 2: opening gripper...')
        self._set_gripper(open=True)

        # 3. Descend to grasp pose
        self.get_logger().info('Step 3: descending to grasp...')
        if not self._move_to(self._build_pose(ax, ay, grasp_z)):
            return

        # 4. Close gripper
        self.get_logger().info('Step 4: closing gripper...')
        self._set_gripper(open=False)

        # 5. Retreat upward with apple
        self.get_logger().info('Step 5: retreating...')
        self._move_to(self._build_pose(ax, ay, approach_z + 0.1))

    def _set_gripper(self, open: bool):
        """
        Your gripper uses two prismatic joints:
          left_finger_joint  slides +X to open
          right_finger_joint slides -X to open
        From the URDF: limit lower=-0.03, upper=0.051
          0.0  = closed
          0.05 = fully open
        These are controlled via the gripper_controller defined
        in ros2_controllers.yaml — publish to its command topic.
        """
        from std_msgs.msg import Float64MultiArray
        msg = Float64MultiArray()
        # [left_finger_joint, right_finger_joint]
        msg.data = [0.05, 0.05] if open else [0.0, 0.0]

        # topic name depends on your ros2_controllers.yaml
        # common patterns: /gripper_controller/commands
        #                  /hand_controller/commands
        if not hasattr(self, '_gripper_pub'):
            from std_msgs.msg import Float64MultiArray
            self._gripper_pub = self.create_publisher(
                Float64MultiArray,
                '/gripper_controller/commands',
                10
            )
        self._gripper_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = ApplePicker()
    
    # Give the node a moment to receive the apple location
    import time
    time.sleep(2.0)
    
    node.pick_apple()
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()