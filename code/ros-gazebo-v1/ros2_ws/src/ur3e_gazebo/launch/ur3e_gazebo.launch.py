from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    # Find our package
    ur3e_gazebo_pkg = FindPackageShare('ur3e_gazebo')

    # Generate the URDF from our wrapper xacro (which lives in ur3e_gazebo, not the upstream package).
    # ParameterValue(..., value_type=str) prevents ROS 2 from trying to parse the URDF XML as YAML.
    robot_description = ParameterValue(
        Command([
            'ros2 run xacro xacro ',
            PathJoinSubstitution([ur3e_gazebo_pkg, 'urdf', 'ur3e_gz.urdf.xacro']),
        ]),
        value_type=str,
    )

    headless = LaunchConfiguration('headless')
    world = PathJoinSubstitution([FindPackageShare('ur3e_gazebo'), 'worlds', 'grocery_world.sdf'])
    gz_launch = PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])

    # Normal mode: GUI window, starts running immediately
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([gz_launch]),
        launch_arguments={'gz_args': [world, ' -r']}.items(),
        condition=UnlessCondition(headless),
    )

    # Headless mode: no GUI window, offscreen camera rendering, starts running immediately.
    # -s suppresses the GUI window (server-only).
    # --headless-rendering uses EGL so camera sensors still produce images without a display.
    # -r starts the simulation unpaused (skips the manual unpause step).
    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([gz_launch]),
        launch_arguments={'gz_args': [world, ' -s --headless-rendering -r']}.items(),
        condition=IfCondition(headless),
    )

    # Bridge 1: /clock only — critical for controller_manager sim time
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
    )

    # Bridge 2: all camera topics — arm and overhead RGB + depth streams
    camera_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # Arm RGB camera
            '/arm_camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/arm_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            # Arm depth camera
            '/arm_depth_camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/arm_depth_camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/arm_depth_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/arm_depth_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            # Overhead RGB camera
            '/overhead_camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/overhead_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            # Overhead depth camera
            '/overhead_depth_camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/overhead_depth_camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/overhead_depth_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/overhead_depth_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
    )

    # Publish the robot state
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
    )

    # Spawn the UR3e into Gazebo
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'ur3e',
            '-topic', 'robot_description',
        ],
    )

    # Spawn joint_state_broadcaster after the robot is in Gazebo
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
    )

    # Spawn joint_trajectory_controller after joint_state_broadcaster is active
    joint_trajectory_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_trajectory_controller', '--controller-manager', '/controller_manager'],
    )

    # Send the home pose command after joint_trajectory_controller is active.
    # Gripper fingers are now part of joint_trajectory_controller — no separate
    # gripper spawner needed.
    # TO SWITCH TO ROBOTIQ 2F-85: restore a gripper_controller_spawner node here
    # and chain it between joint_trajectory_controller and home_pose.
    home_pose = Node(
        package='ur3e_gazebo',
        executable='home_pose',
    )

    # Chain: spawn_robot -> joint_state_broadcaster -> joint_trajectory_controller -> home_pose
    load_joint_state_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot,
            on_exit=[joint_state_broadcaster_spawner],
        )
    )

    load_joint_trajectory_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[joint_trajectory_controller_spawner],
        )
    )

    load_home_pose = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_trajectory_controller_spawner,
            on_exit=[home_pose],
        )
    )

    # Publish fixed transform for the overhead camera (standalone SDF model,
    # not part of the URDF, so robot_state_publisher won't emit it).
    # Translation matches grocery_world.sdf: x=0.35 y=0 z=0.5.
    # Rotation: roll=π yaw=π/2 aligns the optical frame (Z=depth pointing down)
    # so that depth maps to world -Z.  This gives:
    #   world = (0.35 + image_row_offset, image_col_offset, 0.5 - depth)
    # which matches the docstring: "image X → world Y, image Y → world X".
    overhead_camera_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=[
            '--x', '0.35', '--y', '0.0', '--z', '0.5',
            '--roll', '3.14159', '--pitch', '0.0', '--yaw', '1.5708',
            '--frame-id', 'world',
            '--child-frame-id', 'overhead_camera_link',
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'headless', default_value='false',
            description='Run Gazebo headless: no GUI window, offscreen camera rendering'
        ),
        gazebo,
        gazebo_headless,
        clock_bridge,
        camera_bridge,
        robot_state_publisher,
        spawn_robot,
        load_joint_state_broadcaster,
        load_joint_trajectory_controller,
        load_home_pose,
        overhead_camera_tf,
    ])