#!/bin/bash
# =============================================================================
# GroceryRobot — Simulation Teardown Script
#
# Cleanly stops all running simulation processes.
# Safe to run even if the simulation is not running.
#
# Usage:
#   bash teardown.sh
# =============================================================================

echo ""
echo "============================================="
echo "  GroceryRobot Simulation Teardown"
echo "============================================="
echo ""

_kill9() {
    local pattern="$1"
    local label="$2"
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo "Stopping $label..."
        pkill -9 -f "$pattern" || true
        return 0
    fi
    return 1
}

any_killed=false

_kill9 "ros2"                   "ros2 processes"        && any_killed=true
_kill9 "gz sim"                 "Gazebo (gz sim)"       && any_killed=true
_kill9 "gzserver"               "Gazebo server"         && any_killed=true
_kill9 "gzclient"               "Gazebo client"         && any_killed=true
_kill9 "gz-sim"                 "gz-sim"                && any_killed=true
_kill9 "spawner"                "controller spawner"    && any_killed=true
_kill9 "parameter_bridge"       "ROS-Gz bridge"         && any_killed=true
_kill9 "robot_state_publisher"  "robot state publisher" && any_killed=true
_kill9 "joint_control_panel"    "joint control panel"   && any_killed=true
_kill9 "rqt_image_view"         "image viewer"          && any_killed=true
_kill9 "move_group"             "MoveIt move_group"     && any_killed=true
_kill9 "moveit_pick_from_camera" "pick node"            && any_killed=true
_kill9 "overhead_camera_localizer" "camera localizer"   && any_killed=true
_kill9 "static_transform_publisher" "static TF publishers" && any_killed=true

sleep 1

if [ "$any_killed" = false ]; then
    echo "Nothing was running."
fi

echo ""
echo "Done."
echo ""
