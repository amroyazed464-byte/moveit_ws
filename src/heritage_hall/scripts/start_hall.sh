#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
# Avoid VMware SVGA3D flicker while retaining Ogre2 materials and textures.
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QPA_PLATFORM=xcb
hall_dir="${2:-$(cd "$(dirname "$0")/.." && pwd)}"
export GZ_SIM_RESOURCE_PATH="$(dirname "$hall_dir"):${GZ_SIM_RESOURCE_PATH:-}"
if [ "${1:-true}" = false ]; then
  exec gz sim -s -r "$hall_dir/worlds/heritage_hall.sdf"
fi
exec gz sim -r "$hall_dir/worlds/heritage_hall.sdf"
