#!/usr/bin/env bash
set -e
source /etc/os-release
if [ "$ID" != ubuntu ] || [ "$VERSION_ID" != 24.04 ]; then
  echo '本部署包验证环境为 Ubuntu 24.04 + ROS 2 Jazzy。请使用对应桌面环境。' >&2
  exit 2
fi
if [ ! -f /opt/ros/jazzy/setup.bash ]; then
  echo '请先按官方文档安装 ROS 2 Jazzy Desktop，再运行本脚本：' >&2
  echo 'https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html' >&2
  exit 2
fi
packages=(build-essential cmake python3-colcon-common-extensions python3-pytest python3-pil
  fonts-noto-cjk libgl1-mesa-dri ros-jazzy-ament-cmake ros-jazzy-ament-cmake-python
  ros-jazzy-ros-gz ros-jazzy-navigation2 ros-jazzy-nav2-bringup
  ros-jazzy-gz-sim-vendor ros-jazzy-gz-transport-vendor ros-jazzy-gz-msgs-vendor)
if [ "${1:-}" = --check ]; then
  missing=0
  for package in "${packages[@]}"; do
    if [ "$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)" != installed ]; then
      echo "缺少依赖：$package" >&2
      missing=1
    fi
  done
  if [ "$missing" = 0 ]; then echo '部署依赖检查通过。'; fi
  exit "$missing"
fi
if [ "$#" != 0 ]; then echo '用法：bash deploy/install_dependencies.sh [--check]' >&2; exit 2; fi
sudo apt-get update
sudo apt-get install -y "${packages[@]}"
echo '依赖安装完成。下一步：bash deploy/build.sh'
