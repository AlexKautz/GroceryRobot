#!/bin/bash
# do_the_thing.sh — Fully automated GroceryRobot launch.
# Replaces the manual launch.sh → node selection → Gazebo play → MoveIt → pick node flow.

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$REPO/code/ros-gazebo-v1/ros2_ws"
LOGS_DIR="$REPO/logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

mkdir -p "$LOGS_DIR"

_log()  { echo "  [do_the_thing] $*"; }
_ok()   { echo "  [do_the_thing] ✓ $*"; }
_fail() { echo "  [do_the_thing] ✗ $*"; }

_wait_for_topic() {
    local topic="$1" label="$2" timeout_sec="${3:-60}"
    local elapsed=0
    _log "Waiting for $label ($topic)..."
    until ros2 topic list 2>/dev/null | grep -qx "$topic"; do
        sleep 2; elapsed=$((elapsed + 2))
        if [ "$elapsed" -ge "$timeout_sec" ]; then
            _fail "Timed out waiting for $label after ${timeout_sec}s"
            exit 1
        fi
    done
    _ok "$label is up"
}

_wait_for_action() {
    local action="$1" label="$2" timeout_sec="${3:-60}"
    local elapsed=0
    _log "Waiting for $label ($action)..."
    until ros2 action list 2>/dev/null | grep -qx "$action"; do
        sleep 2; elapsed=$((elapsed + 2))
        if [ "$elapsed" -ge "$timeout_sec" ]; then
            _fail "Timed out waiting for $label after ${timeout_sec}s"
            exit 1
        fi
    done
    _ok "$label is ready"
}

cleanup() {
    echo ""
    _log "Shutting down..."
    bash "$REPO/teardown.sh"
    exit 0
}
trap cleanup INT TERM

echo ""
echo "============================================="
echo "  GroceryRobot — Automated Launch"
echo "  $TIMESTAMP"
echo "============================================="
echo ""

# ── 1. Source ROS + workspace ────────────────────────────────────────────────
source /opt/ros/kilted/setup.bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
source "$WS/install/setup.bash"

VENV="$REPO/venv"
if [ -d "$VENV" ]; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    export PYTHONPATH="$VENV/lib/python${PY_VER}/site-packages${PYTHONPATH:+:$PYTHONPATH}"
fi

# ── 2. Teardown any leftover processes ──────────────────────────────────────
bash "$REPO/teardown.sh"

# ── 3. Start Simulation ──────────────────────────────────────────────────────
_log "Starting Simulation..."
ros2 launch ur3e_gazebo ur3e_gazebo.launch.py \
    > "$LOGS_DIR/simulation_$TIMESTAMP.log" 2>&1 &

# ── 4. Wait for Gazebo to boot (clock = sim is publishing) ──────────────────
_wait_for_topic /clock "Gazebo clock" 90
_log "Letting controllers settle (5s)..."
sleep 5

# ── 5. Unpause Gazebo ────────────────────────────────────────────────────────
_log "Unpausing Gazebo..."
if gz service -s /world/empty/control \
       --reqtype gz.msgs.WorldControl \
       --reptype gz.msgs.Boolean \
       --timeout 3000 \
       --req 'pause: false' 2>/dev/null; then
    _ok "Gazebo unpaused"
else
    _fail "gz service call failed — Gazebo may already be running or world name changed"
fi

# ── 6. Start Overhead Camera Localizer ──────────────────────────────────────
_log "Starting Overhead Camera Localizer..."
ros2 run ur3e_gazebo overhead_camera_localizer \
    > "$LOGS_DIR/overhead_camera_localizer_$TIMESTAMP.log" 2>&1 &

# ── 7. Start MoveIt ──────────────────────────────────────────────────────────
_log "Starting MoveIt..."
ros2 launch ur3e_moveit_config move_group.launch.py \
    > "$LOGS_DIR/moveit_$TIMESTAMP.log" 2>&1 &

# ── 8. Wait for MoveIt action server ────────────────────────────────────────
_wait_for_action /move_action "MoveIt /move_action" 90

# ── 9. Start MoveIt Pick from Camera ────────────────────────────────────────
_log "Starting MoveIt Pick from Camera..."
ros2 launch ur3e_gazebo moveit_pick_from_camera.launch.py \
    > "$LOGS_DIR/moveit_pick_from_camera_$TIMESTAMP.log" 2>&1 &

echo ""
echo "============================================="
_ok "All nodes running"
echo ""
echo "  Logs:"
echo "    simulation:               logs/simulation_$TIMESTAMP.log"
echo "    overhead_camera:          logs/overhead_camera_localizer_$TIMESTAMP.log"
echo "    moveit:                   logs/moveit_$TIMESTAMP.log"
echo "    moveit_pick_from_camera:  logs/moveit_pick_from_camera_$TIMESTAMP.log"
echo ""
echo "  Ctrl+C to stop everything."
echo "============================================="
echo ""

wait
