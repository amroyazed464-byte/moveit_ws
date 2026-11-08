# 非遗导览完整场景：实现范围与接口

用户要求依据四张任务书截图，尽可能覆盖八项必做内容和六类已显示创新方向，并确认先完成离线完整演示。
原截图的第六项创新末尾截断，只实现可确认的多语/个性化，不声称已获取完整任务书。

## 实际实现与仿真边界

真实仿真链：Gazebo 动态机器人 + 激光雷达 + 地图 + AMCL 定位 + Nav2 路径规划/控制 + 安全速度门控。
业务链：迎宾/单多人、五区路线、三层中英文讲解、受限知识问答、互动题、暂停/重复/跳过/继续/结束返航、异常恢复和人工接管。
创新：分层讲解、字幕/浏览器朗读/表情灯光屏幕联动、任务卡与答题、虚拟大屏、统计日志、语言与讲解偏好。
游客到访/掉队、电量及故障注入为明确标注的仿真输入；不是摄像头、麦克风识别或真实电池测量。
浏览器离线语音是否可用取决于本机语音包，必须保留字幕及状态提示，不上传游客音频。

## 分工接口（文件不重叠）

### 业务核心 `heritage_tour/guide_logic.py` 与 `config/content.json`

纯 Python 类 `GuideSession(content: dict)`，`apply(event: dict) -> list[dict]`，`snapshot() -> dict`。
事件以 `type` 区分：`visitor(count)`、`start(mode,language,auto_advance)`、`arrived(zone_id)`、`speech_done(speech_id)`、
`pause`、`resume`、`repeat`、`skip`、`next`、`end`、`question(text)`、`quiz_answer(answer)`、`fault(kind)`、`recover`、`manual`、`home_arrived`。
返回效果 `navigate(zone_id,pose)`、`cancel_navigation`、`speak(id,text,language)`、`theme(expression,color,zone_id)`、`human_help(reason)`、`log(record)`。
每次讲解产生唯一 speech id，过期到点/播报事件不得跳过当前流程。故障/暂停/人工状态禁止自动继续移动。
快照最低字段：`state`、`mode`、`language`、`auto_advance`、`zone_id`、`zone_index`、`message`、`speech`、`quiz`、`qa`、`events`、`stats`。
状态：IDLE/WELCOMING/NAVIGATING/PRESENTING/READY_NEXT/QUIZ/PAUSED/FAULT/MANUAL/RETURNING/COMPLETE。
内容结构：`zones` 五区，每区 `id,name,pose:[x,y,yaw],narrations:{child,general,deep},english,quiz,qa`；`home:[x,y,yaw]`；`sources`。
五区停靠点：overview [-13.6,0,0], craft [-2,4.8,1.5708], masterpieces [-2,-7.3,-1.5708], history [7,-1,0], interactive [10,5.8,1.5708]。
待命点 [-13.27,-7.73,1.5708]。展品讲解为示范策展内容，不编造具体馆藏年代/作者/真实性。

### 离线控制台 `heritage_tour/web/index.html`

标准库 HTTP 服务由主代理实现。GET `/api/state`：业务快照加 `ready,robot_pose:{x,y,yaw},navigation,safety,route,visitors,map`。
`map` 为 {width:35.4,height:22}，另提供 GET `/api/map.png`。GET `/display` 为大屏模式（同页面 query 或 pathname）。
POST `/api/command` JSON `{type:...}`，返回 `{ok,error?}`。
除上述业务事件外，支持 `visitors(count)`、`scenario(name)`，name=clear/static_obstacle/crossing/visitor_lost/localization_lost/battery_low/unclear。
UI 不直接发送 arrived/home_arrived，仅由实际导航结果触发。浏览器语音结束可发 speech_done，亦有无浏览器时的运行时后备计时。
字幕/大屏/导览图/任务卡/知识出处/人工提示/日志统计要明确；人流和故障按钮标为仿真。

### 运行时与导航（主代理）

主代理实现传感器、地图与 Nav2 参数、ROS 动作客户端、HTTP 适配、安全门控、Gazebo 游客/障碍场景和材质联动。
所有动作处理串行进入 ROS 线程；图形服务异步处理。安全与定位故障应取消导航并发零。
知识问题限定配置来源，无法回答时转工作人员；不调用不受限大模型回答未知问题。

## 验收

逐项需求矩阵，纯逻辑回归、仿真导航实际到点与完整五区流程、暂停停止、动态人流/受阻、掉队/定位/电量/听不清/未知问答人工边界。
所有模拟输入在 UI 与说明中可见。保留软件渲染防闪烁设置。按仓库要求验证后同步 main 并导出完整代码包。
