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

# 3. Optionally rebuild the workspace
echo ""
read -r -t 10 -p "  Rebuild workspace? [s = run setup.sh, Enter = skip]: " REBUILD_CHOICE || true
echo ""
if [ "${REBUILD_CHOICE}" = "s" ]; then
    bash "$REPO/setup.sh"
else
    echo "  Skipping rebuild."
fi

# 4. Source the freshly built workspace
source "$WS/install/setup.bash"

# 5. Expose the local venv's packages to all child processes (ros2 run nodes
#    use /usr/bin/python3 directly, so activating the venv isn't enough —
#    PYTHONPATH is the reliable way to make the packages visible to them)
VENV="$REPO/venv"
if [ -d "$VENV" ]; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    export PYTHONPATH="$VENV/lib/python${PY_VER}/site-packages${PYTHONPATH:+:$PYTHONPATH}"
else
    echo "WARNING: venv not found at $VENV — run bash setup.sh first"
fi

# 6. Launch the node manager
exec python3 "$REPO/launch.py" "$@"
