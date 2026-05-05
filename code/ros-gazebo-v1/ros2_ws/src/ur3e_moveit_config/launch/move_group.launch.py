from moveit_configs_utils import MoveItConfigsBuilder
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("ur3e", package_name="ur3e_moveit_config")
        .planning_pipelines(
            pipelines=["ompl"],
            default_planning_pipeline="ompl"
        )
        .to_moveit_configs()
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": True},
            {"trajectory_execution.allowed_start_tolerance": 0.05},
        ],
        arguments=["--ros-args", "--log-level", "tf2_buffer:=ERROR"],
    )

    return LaunchDescription([move_group_node])
