# 非遗智伴导览机器人

按用户提供的概念图片建立，在现有非遗展厅中运行。适用 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic。

## 外观与结构

- 约高 1.55m、底座直径约 0.60m：圆头、黑色表情面罩、耳部圆环、胸前屏幕、白金外壳、双臂、云纹和底部灯带。
- 使用本地轻量网格和纹理，无需在线模型。单独启动本包时表情和屏幕为静态图案，手臂及头部为固定外观；完整导览可切换屏幕、表情和灯带。
- 隐藏式双轮差速底盘：轮半径 0.085m，轮距 0.44m，前后低摩擦球形支撑点。
- 总质量假设约 39.3kg，重心和惯性以稳定仿真为目的估算；不是制造设计或真实动力学辨识结果。
- 最大线速度 ±0.35m/s，最大角速度 ±0.8rad/s，具有加速度限制。

## 启动

先关闭此前单独打开的展厅，再在虚拟机终端运行：

```bash
cd ~/moveit_ws  # 或实际解压后的工作空间目录
source /opt/ros/jazzy/setup.bash
colcon build --packages-select heritage_hall heritage_robot
source install/setup.bash
ros2 launch heritage_robot exhibition.launch.py
```

该命令自动打开展厅，在导览起点 (-13.27, -7.73) 生成机器人，并启动速度/里程计桥接。
保留展厅的软件渲染防闪烁设置。仅服务器使用 `gui:=false`。
启动后机器人静止待命，不会自动巡游。

## 移动演示

在另一个已加载 `install/setup.bash` 的终端中，逐条运行：

```bash
# 前进，然后停止
ros2 run heritage_robot drive_robot.py --linear 0.2 --seconds 3
# 后退，然后停止
ros2 run heritage_robot drive_robot.py --linear -0.15 --seconds 2
# 原地左转，然后停止
ros2 run heritage_robot drive_robot.py --angular 0.45 --seconds 2
```

时长按实际经过时间计算；仿真速度较慢时，实际移动距离相应减少。
脚本等待控制连接和机器人里程计就绪后才开始计时，在正常结束或 Ctrl+C 时连续发送零速度。
若脚本被强制杀死，停止逻辑无法执行。
手动立即停止：

```bash
ros2 topic pub --once /heritage_robot/cmd_vel geometry_msgs/msg/Twist '{}'
```

控制话题为 `/heritage_robot/cmd_vel`（Twist），反馈为 `/heritage_robot/odom`（Odometry）。
直接发速度指令时需自行发零停止；Gazebo 差速插件会保留最后接收到的速度。
上述命令仅启动模型与基础驾驶。自主导航、激光雷达、离线讲解和网页交互请使用 [heritage_tour](../heritage_tour/README.md) 的完整启动流程。

## 重建与检查

```bash
python3 src/heritage_robot/scripts/build_robot.py
GZ_SIM_RESOURCE_PATH="$PWD/src/heritage_robot/models" gz sdf -k src/heritage_robot/models/heritage_guide/model.sdf
python3 -m pytest -q
# 隔离运行真实桥接/延迟生成回归检查（需先构建并加载 install/setup.bash）
python3 src/heritage_robot/test/check_readiness.py
```

离线重建需要 Pillow 和中文字体；直接使用已生成的模型不需要 Pillow。

## 2026-11-08 实际验证

- 两个资源包构建成功，SDF 官方检查返回 `Valid.`，项目 23 项测试通过。
- 通过 ROS 2 控制链路前进约 0.676m、后退约 0.190m、左转约 0.998rad。
- 从 Gazebo 世界位姿核对真实运动，停止后 2 秒位置漂移小于 0.035m，底盘贴地且无侧翻。
- 西墙碰撞检查：接触后机器人中心 X 约 -17.286m，没有穿墙；随后已放回导览起点。
- Ctrl+C 实测：正常退出，停止后继续观察 2 秒漂移约 0.00000m。
- 独立 ROS 域和 Gazebo 分区中验证桥接先启动、模型延迟生成：就绪前不发运动指令，收到里程计后再执行移动并停止。
- 上述证据限于此次仿真工况，不代表全场自主导航验收。
