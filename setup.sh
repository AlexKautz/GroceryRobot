#!/bin/bash
# =============================================================================
# GroceryRobot — Simulation Setup Script
#
# Run this once on a fresh machine after cloning the repository.
# This script never runs sudo. If a system package is missing it will print
# the install command and exit so you can run it yourself first.
#
# Usage:
#   source /opt/ros/kilted/setup.bash
#   bash setup.sh
# =============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$REPO_DIR/code/ros-gazebo-v1/ros2_ws"
SRC_DIR="$WS_DIR/src"
UR_DIR="$SRC_DIR/Universal_Robots_ROS2_Description"

echo ""
echo "============================================="
echo "  GroceryRobot Simulation Setup"
echo "============================================="
echo ""

# ── 1. ROS 2 Kilted ──────────────────────────────────────────────────────────
echo "[1/5] Checking ROS 2 Kilted..."

if [ -z "${ROS_DISTRO:-}" ]; then
    echo ""
    echo "  WARNING: ROS 2 is not sourced."
    echo "  Run this first, then re-run setup.sh:"
    echo ""
    echo "    source /opt/ros/kilted/setup.bash"
    echo ""
    exit 1
elif [ "$ROS_DISTRO" != "kilted" ]; then
    echo ""
    echo "  WARNING: Wrong ROS distro sourced ('$ROS_DISTRO')."
    echo "  This workspace targets 'kilted'. Run:"
    echo ""
    echo "    source /opt/ros/kilted/setup.bash"
    echo ""
    exit 1
else
    echo "  OK — ROS 2 Kilted is sourced."
fi

# ── 2. System packages ────────────────────────────────────────────────────────
echo ""
echo "[2/5] Checking required system packages..."

REQUIRED_PACKAGES=(
    "ros-kilted-gz-sim-vendor"
    "ros-kilted-ros-gz"
    "ros-kilted-gz-ros2-control"
    "ros-kilted-ros2-controllers"
    "ros-kilted-controller-manager"
    "ros-kilted-joint-state-publisher-gui"
    "python3-rosdep"
)

MISSING_PACKAGES=()
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"; then
        echo "  OK — $pkg"
    else
        echo "  MISSING — $pkg"
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo ""
    echo "  WARNING: Missing packages detected."
    echo "  Install them by running the following, then re-run setup.sh:"
    echo ""
    echo "    sudo apt install -y ${MISSING_PACKAGES[*]}"
    echo ""
    exit 1
fi

# ── 3. Universal Robots description package ───────────────────────────────────
echo ""
echo "[3/5] Checking Universal_Robots_ROS2_Description..."

if [ -d "$UR_DIR/.git" ]; then
    echo "  OK — Already cloned at $UR_DIR"
else
    echo "  Cloning (rolling branch)..."
    git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Description.git "$UR_DIR"
    git -C "$UR_DIR" checkout rolling
    echo "  OK — Cloned."
fi

# ── 4. rosdep ─────────────────────────────────────────────────────────────────
echo ""
echo "[4/5] Installing ROS dependencies via rosdep..."

if ! rosdep db &>/dev/null; then
    echo ""
    echo "  WARNING: rosdep is not initialised."
    echo "  Run the following, then re-run setup.sh:"
    echo ""
    echo "    sudo rosdep init"
    echo "    rosdep update"
    echo ""
    exit 1
fi

cd "$WS_DIR"
rosdep install --from-paths src --ignore-src -r -y
echo "  OK — Dependencies installed."

# ── 5. Build ──────────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Building workspace..."
rm -rf "$WS_DIR/build" "$WS_DIR/install"
colcon build --symlink-install
echo "  OK — Build complete."

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "============================================="
echo "  Setup complete!"
echo "============================================="
echo ""
echo "To launch the simulation, open a NATIVE terminal (not VS Code)"
echo "and run:"
echo ""
echo "  source /opt/ros/kilted/setup.bash"
echo "  source $WS_DIR/install/setup.bash"
echo "  ros2 launch ur3e_gazebo ur3e_gazebo.launch.py"
echo ""
echo "Then click Play in Gazebo. The arm will move to its home pose."
echo ""
