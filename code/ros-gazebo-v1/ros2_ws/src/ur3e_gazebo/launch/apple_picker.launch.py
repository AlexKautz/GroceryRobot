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

    apple_picker_node = Node(
        package="ur3e_gazebo",
        executable="apple_picker",
        output="screen",
        parameters=[moveit_config.to_dict()],
    )

    return LaunchDescription([apple_picker_node])