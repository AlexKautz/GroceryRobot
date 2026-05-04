import os
import yaml
import tempfile
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped, PoseStamped
from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder


class ApplePicker(Node):

    FINGER_LENGTH = 0.14
    APPROACH_OFFSET = 0.05

    def __init__(self):
        super().__init__('apple_picker')

        # Build config and write to temp file for MoveItPy to load
        moveit_config = (
            MoveItConfigsBuilder("ur3e", package_name="ur3e_moveit_config")
            .planning_pipelines(
                pipelines=["ompl"],
                default_planning_pipeline="ompl"
            )
            .to_moveit_configs()
        )

        # Write config dict to a temp yaml file
        config_dict = moveit_config.to_dict()

        # ROS param files
        ros_params = {
            'apple_picker_moveit': {
                'ros__parameters': config_dict
            }
        }

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump(config_dict, f)
            params_file = f.name

        self.get_logger().info(f'Loading MoveIt config from: {params_file}')

        self.moveit = MoveItPy(
            node_name='apple_picker_moveit',
            launch_params_filepaths=[params_file]
        )

        os.unlink(params_file)  # clean up temp file

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
        ps = PoseStamped()
        ps.header.frame_id = 'world'
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.pose.position.x = x
        ps.pose.position.y = y
        ps.pose.position.z = z
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
            self.get_logger().error(
                f'Planning failed for pose: '
                f'({pose.pose.position.x:.3f}, '
                f'{pose.pose.position.y:.3f}, '
                f'{pose.pose.position.z:.3f})'
            )
            return False
        self.moveit.execute(plan.trajectory, controllers=[])
        return True

    def _set_gripper(self, open: bool):
        from std_msgs.msg import Float64MultiArray
        if not hasattr(self, '_gripper_pub'):
            self._gripper_pub = self.create_publisher(
                Float64MultiArray,
                '/gripper_controller/commands',
                10
            )
        msg = Float64MultiArray()
        msg.data = [0.05, 0.05] if open else [0.0, 0.0]
        self._gripper_pub.publish(msg)

    def pick_apple(self):
        if self._apple_location is None:
            self.get_logger().warn('No apple location received yet')
            return

        ax = self._apple_location.point.x
        ay = self._apple_location.point.y
        az = self._apple_location.point.z

        grasp_z    = az + self.FINGER_LENGTH
        approach_z = grasp_z + self.APPROACH_OFFSET

        self.get_logger().info(f'Apple at ({ax:.3f}, {ay:.3f}, {az:.3f})')

        self.get_logger().info('Step 1: pre-grasp...')
        if not self._move_to(self._build_pose(ax, ay, approach_z)):
            return

        self.get_logger().info('Step 2: open gripper...')
        self._set_gripper(open=True)

        self.get_logger().info('Step 3: descend...')
        if not self._move_to(self._build_pose(ax, ay, grasp_z)):
            return

        self.get_logger().info('Step 4: close gripper...')
        self._set_gripper(open=False)

        self.get_logger().info('Step 5: retreat...')
        self._move_to(self._build_pose(ax, ay, approach_z + 0.1))


def main(args=None):
    rclpy.init(args=args)
    node = ApplePicker()
    import time
    time.sleep(2.0)
    node.pick_apple()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()