# Heritage Hall Implementation Plan

**Goal:** 按参考图片交付可在虚拟机 Gazebo 中加载、具有实体碰撞的展厅。
**Architecture:** 独立 ament_cmake 资源包，本地贴图与基本几何体；生成脚本仅用于离线重建，运行无下载依赖。
**Tech Stack:** ROS 2 Jazzy, Gazebo Harmonic, SDF 1.9, Python 3/Pillow.
**Spec:** `docs/superpowers/specs/2026-11-07-heritage-hall-design.md`

## Constraints and review focus

- 35.4m × 22m，墙高 4.2m，双门洞 2.4m；其它尺寸为图像比例估算。
- 检查地面方向、纹理路径、独立启动的安装路径、墙体碰撞、五区通道连通性。
- 不改变已有 MoveIt 程序，不提交连接凭据、构建产物或用户图片。

## Tasks

- [x] 创建 `src/heritage_hall/test/test_hall.py`，运行确认缺少场景时失败。
- [x] 创建场景生成器、离线纹理、SDF、构建文件、独立启动入口和说明。
- [x] 在虚拟机运行生成器和连通检查；`gz sdf -k` 返回 Valid。
- [x] 构建包，以安装后的 ROS 启动命令加载，检查实际渲染和服务端状态。
- [x] 复核差异、运行相关既有测试，按项目要求提交并同步 main。

验证记录：地面网格补齐显式法线，防止 Ogre2 缺少法线错误；通道测试限定真实地板及门外平台，避免场外绕行误判。
运行中三个临时测试球分别在地板、展柜和墙顶稳定接触，中心高度 0.150 / 2.050 / 4.350m；验证后移除。
独立只读复核未发现重要问题，已采纳地板覆盖范围约束建议。其它材质调试日志不作为实车导航验收。
