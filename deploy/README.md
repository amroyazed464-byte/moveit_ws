# 非遗智伴：独立部署工程

本包包含展厅、全身机器人、五区导航导览、网页控制台和36段粤语离线音频。接收方无需原开发目录、旧机械臂工程或虚拟机连接配置。

## 1. 准备环境

验证基线为 **Ubuntu 24.04 Desktop、ROS 2 Jazzy、Gazebo Harmonic、x86_64**。Windows用户应在对应Ubuntu虚拟机中部署。先登录Ubuntu桌面。

如果尚未安装ROS，请先按 [ROS 2 Jazzy官方安装说明](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) 安装 `ros-jazzy-desktop`。本包不会自行添加软件源或修改系统登录配置。[Gazebo官方配套说明](https://gazebosim.org/docs/latest/ros_installation/) 将Jazzy与Harmonic对应；依赖脚本使用ROS提供的配套包。

解压后进入 `heritage-guide-demo` 文件夹，在该目录打开终端。路径可以自行选择，后续不要在别的工作区里运行下面的命令。

## 2. 安装依赖、校验和构建

```bash
# 首次需要联网，可能要求输入本机sudo密码
bash deploy/install_dependencies.sh
# 核对全部交付文件，再在本机编译并运行检查
python3 deploy/verify_package.py
bash deploy/build.sh
```

已安装依赖时可先用 `bash deploy/install_dependencies.sh --check` 只检查，不修改系统。本包不附编译目录；不同机器必须重新构建，不要复制原电脑的 `build` 或 `install`。

## 3. 启动演示

保持Ubuntu桌面已登录，关闭以前运行的同名展厅和导览，再执行：

```bash
bash deploy/start_demo.sh
```

浏览器打开 **http://localhost:8765**；导览大屏为 **http://localhost:8765/display**。

1. 等待页面显示“已就绪”。
2. 先选普通话、粤语（香港）或英文，以及儿童、大众或深度讲解。
3. 可点击“试听粤语”，再勾选“启用离线语音”。粤语自带音频；普通话和英文需要浏览器可用的本机语音，缺失时仍有字幕。
4. 选择“单人到访”或“3人结伴到访”，迎宾后点击“开始导览”。到站后讲解、答题并继续下一站。
5. 暂停、重复、跳过、人工接管及结束返航均可在控制台操作。异常演示后先恢复场景，再“恢复检查”和“继续”。
6. 结束运行时在启动终端按 **Ctrl+C**。

首次启动会加载纹理和导航组件，需要等待就绪；不要反复启动多个进程。端口8765已占用时启动器会退出，避免同时启动两套导览。

默认保留软件渲染、防闪烁设置和四个渲染工作线程。只关闭Gazebo窗口、保留后台演示可用 `bash deploy/start_demo.sh --headless`，但仿真雷达仍需已登录的桌面显示环境。

## 4. 目录与更新

```text
src/heritage_hall/   展厅世界、碰撞、网格、贴图
src/heritage_robot/  全身机器人、差速底盘、雷达、表情和胸屏资源
src/heritage_tour/   定位导航、流程、网页、地图、内容、粤语音频和测试
deploy/             安装、构建、启动和校验工具
RELEASE.json        对应源码版本与部署环境
SHA256SUMS.txt      原始文件校验清单，使用Linux的LF换行
```

脚本启动的事件日志写到本解压目录 `log/heritage_tour/events.jsonl`。直接使用ROS命令启动时，默认写到当前用户的 `~/.local/state/heritage_tour/events.jsonl`，可通过 `HERITAGE_TOUR_LOG_DIR` 修改。

文稿、已核验问答、答题和站点位置在 `src/heritage_tour/config/content.json`。修改内容后重新构建；修改粤语文稿还应按 `src/heritage_tour/CANTONESE.md` 重新制作音频。正常播放粤语不需要联网，不需要安装生成工具。自行修改文件后，原交付校验清单会报告差异，这是预期行为。

## 5. 复测与实现范围

`build.sh` 会运行全部单元检查。仿真启动且处于待命状态后，可在另一个终端执行实际短程运动、暂停和返航检查：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
python3 src/heritage_tour/test/run_final_smoke.py
# 完整五区路线：机器人实际导航，讲解完成与答题由脚本模拟输入
python3 src/heritage_tour/test/run_full_tour.py
```

游客到访、掉队、电量和听不清等是明确标注的模拟输入；没有真实麦克风或人脸识别。模型尺寸根据参考图片估算，适合演示。脸屏是静态表情切换，胸屏是状态卡片，底灯有金/蓝/红色联动；头部与手臂不执行关节动作。

场景与音频均在包内，运行不依赖Gazebo Fuel或外部内容网站。既有视频、截图、旧版本包、旧机械臂工程、Git历史、本机连接资料、构建输出及测试缓存不在本部署包内。原工程中的历史验证资料另外保留。
