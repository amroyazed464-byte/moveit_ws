#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
hall_dir="${2:-$(cd "$(dirname "$0")/.." && pwd)}"
export GZ_SIM_RESOURCE_PATH="$(dirname "$hall_dir"):${GZ_SIM_RESOURCE_PATH:-}"
if [ "${1:-true}" = false ]; then
  exec gz sim -s -r "$hall_dir/worlds/heritage_hall.sdf"
fi
exec gz sim -r "$hall_dir/worlds/heritage_hall.sdf"
