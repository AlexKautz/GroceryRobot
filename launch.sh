#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# launch.sh — Teardown → rebuild → source → launch manager.
# Run this instead of python3 launch.py directly.
# ─────────────────────────────────────────────────────────────────────────────

set -e

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$REPO/code/ros-gazebo-v1/ros2_ws"

# 1. Source base ROS first — setup.sh checks $ROS_DISTRO
source /opt/ros/kilted/setup.bash

# 2. Stop any running simulation
bash "$REPO/teardown.sh"

# 3. Rebuild the workspace (colcon build + dependency checks)
bash "$REPO/setup.sh"

# 4. Source the freshly built workspace
source "$WS/install/setup.bash"

# 5. Launch the node manager
exec python3 "$REPO/launch.py" "$@"
