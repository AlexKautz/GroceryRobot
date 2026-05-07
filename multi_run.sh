#!/bin/bash
# multi_run.sh — Set up ROS environment and run the 5-position pick test.

set -e

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$REPO/code/ros-gazebo-v1/ros2_ws"

source /opt/ros/kilted/setup.bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
source "$WS/install/setup.bash"

VENV="$REPO/venv"
if [ -d "$VENV" ]; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    export PYTHONPATH="$VENV/lib/python${PY_VER}/site-packages${PYTHONPATH:+:$PYTHONPATH}"
else
    echo "WARNING: venv not found at $VENV — run bash setup.sh first"
fi

exec python3 "$REPO/multi_run.py" "$@"
