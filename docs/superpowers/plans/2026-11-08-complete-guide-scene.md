# Complete Guide Scene Implementation Plan

**Goal:** 复刻可操作、可验证的非遗展厅完整导览场景。
**Spec:** `docs/superpowers/specs/2026-11-08-complete-guide-scene.md`
**Architecture:** 保留现有场地和机器人；新增独立 `heritage_tour` 资源包，纯业务核心与 UI 并行实现，主代理集成 ROS/Gazebo/Nav2。

- [x] 纯业务状态机、分层内容、受限问答与异常恢复回归。
- [x] 中文控制台、字幕朗读、展区图、互动卡和运营统计。
- [x] 地图、雷达、TF/时钟桥接、AMCL/Nav2 与实际停靠验证。
- [x] 运行时联动：安全门控、游客/障碍注入、表情灯光/机器人屏/虚拟大屏。
- [x] 完整路线及异常场景实测、独立复核、更新需求覆盖矩阵。
- [ ] 构建测试、同步 main，导出演示截图/完整包和操作说明。
