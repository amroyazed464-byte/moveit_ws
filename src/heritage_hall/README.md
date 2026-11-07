# 非遗展厅机器人仿真场地

依据用户提供的俯视平面图建立，适配 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic。

## 建模约定

- 图示面积约 780㎡、层高 4.2m；采用 35.4m × 22m（778.8㎡）矩形场地。
- 图片不是带尺寸施工图。展柜、房间和隔断的位置按图像比例估算，不作为实测尺寸。
- 世界原点在展厅中心，+X 向图右，+Y 向图上，+Z 向上。
- 五个地面分区、中央展柱、主要展柜、工艺桌凳、互动桌、信息屏、服务房和两处出入口均保留。
- 墙高 4.2m，入口中心 (-12.5, -11)，出口中心 (9.4, -11)，门洞各宽 2.4m。无顶棚便于观察。
- 墙体、隔断、展柜、桌凳和中央展柱具有静态碰撞；地面标识与装饰没有额外碰撞。
- 展品采用简化几何体；不生成导航机器人或导航控制程序。地面导览起点标记不是机器人。
- 白色虚线是图片的参观动线示意，不是控制器轨迹。

## 启动

在工作空间根目录运行：

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select heritage_hall
source install/setup.bash
ros2 launch heritage_hall hall.launch.py
```

仅服务器：`ros2 launch heritage_hall hall.launch.py gui:=false`。

不构建也能启动：`bash src/heritage_hall/scripts/start_hall.sh`。
模型及纹理全部本地提供，不需要 Gazebo Fuel 下载。

## 重建与检查

```bash
python3 src/heritage_hall/scripts/build_hall.py
python3 -m unittest discover -s src/heritage_hall/test -v
GZ_SIM_RESOURCE_PATH="$PWD/src" gz sdf -k src/heritage_hall/worlds/heritage_hall.sdf
```

重建脚本仅需 Python 3 和 Pillow（`python3-pil`），中文地面文字优先使用系统 Noto CJK 字体。
测试按 0.1m 网格、半径 0.3m 机器人检查入口、五区停靠点和出口连通性。
连通性检查不是实车导航、激光雷达或 Nav2 验收。

## 本次验证（2026-11-07）

- 虚拟机软件包构建成功，SDF 官方检查返回 `Valid.`。
- 两项资源/通道检查通过，既有 MoveIt 配置的 20 项测试通过。
- Gazebo 运行中投放半径 0.15m 测试球：地板接触中心高度 0.150m，展柜 2.050m，墙顶 4.350m，均与几何预期一致；测试球已移除。
- 已实际加载 GUI，并通过 Gazebo 相机渲染核对地面文字、分区与设施布局。
