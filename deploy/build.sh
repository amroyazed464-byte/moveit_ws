#!/usr/bin/env bash
set -e
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
bash deploy/install_dependencies.sh --check
if [ -f SHA256SUMS.txt ]; then python3 deploy/verify_package.py; fi
source /opt/ros/jazzy/setup.bash
colcon build --packages-select heritage_hall heritage_robot heritage_tour --parallel-workers 2
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider src/heritage_hall/test src/heritage_robot/test src/heritage_tour/test
echo '构建与检查完成。登录 Ubuntu 桌面后运行：bash deploy/start_demo.sh'
