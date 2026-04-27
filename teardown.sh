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

any_killed=false

if pgrep -f "ros2" > /dev/null 2>&1; then
    echo "Stopping ros2 processes..."
    pkill -f "ros2" || true
    any_killed=true
fi

if pgrep -f "gz sim" > /dev/null 2>&1; then
    echo "Stopping Gazebo..."
    pkill -f "gz sim" || true
    any_killed=true
fi

if pgrep -f "gzserver\|gzclient\|gz-sim" > /dev/null 2>&1; then
    echo "Stopping Gazebo server/client..."
    pkill -f "gzserver\|gzclient\|gz-sim" || true
    any_killed=true
fi

if pgrep -f "spawner" > /dev/null 2>&1; then
    echo "Stopping controller spawner..."
    pkill -f "spawner" || true
    any_killed=true
fi

if pgrep -f "robot_state_publisher\|parameter_bridge" > /dev/null 2>&1; then
    echo "Stopping ROS bridge/state publisher..."
    pkill -f "robot_state_publisher\|parameter_bridge" || true
    any_killed=true
fi

sleep 1

if [ "$any_killed" = false ]; then
    echo "Nothing was running."
fi

echo ""
echo "Done."
echo ""
