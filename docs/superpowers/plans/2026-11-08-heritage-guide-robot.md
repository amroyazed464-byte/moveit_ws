# Heritage Guide Robot Implementation Plan

**Goal:** 在既有展厅运行按图片建立的可控轮式导览机器人。
**Architecture:** 独立 ament_cmake 资源包；本地网格/纹理 + 动态 SDF + Gazebo DiffDrive + ROS 2 bridge。
**Tech Stack:** Python 3/Pillow, SDF 1.9, ROS 2 Jazzy, Gazebo Harmonic.
**Spec:** `docs/superpowers/specs/2026-11-08-heritage-guide-robot-design.md`

- [x] 检查原项目、启动虚拟机、确认现有渲染稳定设置。
- [x] 先运行底盘和资源测试，确认缺少模型时失败。
- [x] 创建网格/纹理生成器、动态模型、独立安装与展厅集成启动入口。
- [x] 创建速度/里程计桥接和有时限的移动脚本，验证停止行为。
- [x] 在虚拟机构建、检查 SDF、真实前进/转向/停止与落地稳定性，保存预览。
- [x] 独立复核、运行全部相关测试、提交并同步 main，更新模型包。

关注：轮轴方向、正定惯性、支撑点摩擦、出生点碰撞、资源路径、连接等待、移动结束后的零速度。

独立复核指出桥接先启动但模型未生成时，原就绪判断会过早开始移动计时。
已在独立 ROS 域/Gazebo 分区真实复现失败，改为同时等待控制连接及首条里程计；延迟生成回归、Ctrl+C 停止检查和全套 23 项测试通过。
模型尺寸/质量为明确估算，固定头臂和静态屏幕按既定范围交付；未接入自主导航。
