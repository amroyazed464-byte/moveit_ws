#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
export LIBGL_ALWAYS_SOFTWARE=1
export LP_NUM_THREADS=4
export QT_QPA_PLATFORM=xcb
# GPU lidar still needs a desktop display when Gazebo runs without its GUI.
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [ -z "${XAUTHORITY:-}" ]; then
  for authority in "$XDG_RUNTIME_DIR"/.mutter-Xwaylandauth.*; do
    if [ -f "$authority" ]; then export XAUTHORITY="$authority"; break; fi
  done
fi
exec ros2 launch heritage_tour tour.launch.py "gui:=${1:-true}"
