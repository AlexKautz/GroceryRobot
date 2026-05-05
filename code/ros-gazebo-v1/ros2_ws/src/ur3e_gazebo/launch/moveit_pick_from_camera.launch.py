from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ur3e_gazebo',
            executable='moveit_pick_from_camera',
            output='screen',
            parameters=[{
                'apple_topic': '/overhead_camera/apple_location',
                'move_group_action': '/move_action',
                'planning_group': 'ur_manipulator',
                'eef_link': 'tool0',
                'pre_grasp_z_offset': 0.20,
                'grasp_z_offset': 0.03,
                'lift_z_offset': 0.25,
                'velocity_scaling': 0.05,
                'acceleration_scaling': 0.05,
                'gripper_topic': '/joint_trajectory_controller/joint_trajectory',
                'left_finger_joint': 'left_finger_joint',
                'right_finger_joint': 'right_finger_joint',
                'gripper_open': 0.05,
                'gripper_closed': -0.006,
            }],
        ),
    ])
