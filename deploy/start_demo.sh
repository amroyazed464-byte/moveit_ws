#!/usr/bin/env bash
set -e
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "$#" -gt 1 ] || { [ "$#" = 1 ] && [ "$1" != --headless ]; }; then
  echo '用法：bash deploy/start_demo.sh [--headless]' >&2
  exit 2
fi
if [ ! -f "$project_dir/install/setup.bash" ]; then
  echo '请先运行 bash deploy/build.sh 完成构建。' >&2
  exit 2
fi
if [ -z "${DISPLAY:-}" ] && [ ! -S /tmp/.X11-unix/X0 ]; then
  echo '请先登录 Ubuntu 桌面。无窗口模式的仿真雷达也需要桌面显示环境。' >&2
  exit 2
fi
python3 - <<'PY'
import socket
try:
    with socket.socket() as sock:
        sock.bind(('0.0.0.0', 8765))
except OSError:
    raise SystemExit('导览端口8765已被占用，请先关闭旧的导览程序；本次未启动新仿真。')
PY
cd "$project_dir"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export HERITAGE_TOUR_LOG_DIR="$project_dir/log/heritage_tour"
gui=true
if [ "${1:-}" = --headless ]; then gui=false; fi
echo '导览控制台：http://localhost:8765 ；结束运行请按 Ctrl+C。'
exec ros2 run heritage_tour start_tour.sh "$gui"
