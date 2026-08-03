# Sunyijie Compound MoveIt Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the chapter-7 C++ MoveIt commander and extend `/pose_command` so one message moves the six-axis arm and then opens or closes the gripper through the personal field `sunyijie_gripper`.

**Architecture:** Add one ROS interface package and one C++ commander package. A single coordinator node owns separate MoveGroupInterface objects for the existing `arm` and `gripper` groups, serializes user commands, executes the requested arm plan first, and changes the gripper only after arm success. The existing MoveIt demo launch starts the commander with the same robot parameters.

**Tech Stack:** Ubuntu 24.04, ROS 2 Jazzy, MoveIt 2 C++ API, rclcpp, TF2, rosidl, ament_cmake, ament_cmake_gtest, Python pytest, colcon, RViz.

## Global Constraints

- Work from commit `eb3d710` or a descendant in `moveit_ws`.
- Use a feature worktree and branch named `feat/sunyijie-compound-command` during implementation.
- The message, generated C++ access, source variables, tests, README, and CLI commands must use exactly `sunyijie_gripper`.
- `sunyijie_gripper == true` means `gripper_close`; `false` means `gripper_open`.
- Preserve the existing MoveIt groups `arm` and `gripper` and their separate controllers.
- Preserve topics `/gripper_command`, `/joint_command`, and `/pose_command`.
- `/gripper_command` uses `std_msgs/msg/Bool`; `/joint_command` uses `std_msgs/msg/Float64MultiArray`; `/pose_command` uses `my_moveit_interfaces/msg/PoseCommand`.
- Execute the arm first and the gripper second; never change the gripper after an arm planning or execution failure.
- Normal pose planning uses `setStartStateToCurrentState`, `setPoseTarget`, `plan`, and `execute`.
- Cartesian planning uses `eef_step = 0.01`, `jump_threshold = 0.0`, and requires a fraction of at least `0.999`.
- Keep `robot_description` unchanged.
- The VM target is `jay@192.168.72.200`; its workspace is `/home/jay/moveit_ws` and its ROS distribution is Jazzy.
- Follow red-green TDD and run fresh verification before any completion claim.

## File Structure

- `src/my_moveit_interfaces/msg/PoseCommand.msg`: exact compound pose wire contract.
- `src/my_moveit_interfaces/CMakeLists.txt`: rosidl interface generation.
- `src/my_moveit_interfaces/package.xml`: interface package metadata and dependencies.
- `src/my_robot_commander/include/my_robot_commander/command_utils.hpp`: pure validation, pose conversion, and gripper mapping API.
- `src/my_robot_commander/src/command_utils.cpp`: pure utility implementation.
- `src/my_robot_commander/include/my_robot_commander/commander.hpp`: commander class declaration and ROS/MoveIt boundaries.
- `src/my_robot_commander/src/commander.cpp`: planning methods and topic callbacks.
- `src/my_robot_commander/src/main.cpp`: node construction and multi-threaded executor.
- `src/my_robot_commander/test/test_command_utils.cpp`: unit tests for pure behavior.
- `src/my_robot_commander/CMakeLists.txt`: utility library, commander executable, install, and tests.
- `src/my_robot_commander/package.xml`: runtime and test dependencies.
- `src/my_robot_commander/README.md`: launch instructions and verified recording sequence.
- `src/my_robot_moveit_config/launch/demo.launch.py`: start the commander with the MoveIt demo.
- `src/my_robot_moveit_config/package.xml`: runtime dependency on the commander.
- `src/my_robot_moveit_config/test/test_moveit_config.py`: cross-package static contracts.

---

### Task 1: Exact `PoseCommand` interface

**Files:**
- Modify: `src/my_robot_moveit_config/test/test_moveit_config.py`
- Create: `src/my_moveit_interfaces/msg/PoseCommand.msg`
- Create: `src/my_moveit_interfaces/CMakeLists.txt`
- Create: `src/my_moveit_interfaces/package.xml`

**Interfaces:**
- Consumes: no new code; only the existing workspace layout.
- Produces: generated type `my_moveit_interfaces::msg::PoseCommand` with member `bool sunyijie_gripper`.

- [ ] **Step 1: Add the failing interface contract**

Add these constants near the existing path constants in
`test_moveit_config.py`:

```python
INTERFACE_PACKAGE = WORKSPACE_SRC / "my_moveit_interfaces"
POSE_COMMAND_MSG = INTERFACE_PACKAGE / "msg" / "PoseCommand.msg"
EXPECTED_POSE_COMMAND_FIELDS = [
    "float64 x",
    "float64 y",
    "float64 z",
    "float64 roll",
    "float64 pitch",
    "float64 yaw",
    "bool cartesian_path",
    "bool sunyijie_gripper",
]
```

Add this test method:

```python
def test_pose_command_interface_uses_exact_personal_contract(self):
    fields = [
        line.strip()
        for line in POSE_COMMAND_MSG.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    self.assertEqual(EXPECTED_POSE_COMMAND_FIELDS, fields)

    cmake = (INTERFACE_PACKAGE / "CMakeLists.txt").read_text(
        encoding="utf-8"
    )
    self.assertIn("rosidl_generate_interfaces", cmake)
    self.assertIn('"msg/PoseCommand.msg"', cmake)

    manifest = ET.parse(INTERFACE_PACKAGE / "package.xml").getroot()
    build_dependencies = {
        element.text.strip()
        for element in manifest.findall("buildtool_depend")
        + manifest.findall("build_depend")
    }
    self.assertIn("ament_cmake", build_dependencies)
    self.assertIn("rosidl_default_generators", build_dependencies)
    self.assertEqual(
        ["rosidl_interface_packages"],
        [element.text.strip() for element in manifest.findall("member_of_group")],
    )
```

- [ ] **Step 2: Run the interface contract and verify RED**

Run from the feature worktree root:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k pose_command_interface -v
```

Expected: FAIL with `FileNotFoundError` for
`src/my_moveit_interfaces/msg/PoseCommand.msg`.

- [ ] **Step 3: Create the exact message**

Create `PoseCommand.msg` with exactly:

```text
float64 x
float64 y
float64 z
float64 roll
float64 pitch
float64 yaw
bool cartesian_path
bool sunyijie_gripper
```

- [ ] **Step 4: Create the interface build metadata**

Create `CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.22)
project(my_moveit_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/PoseCommand.msg"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
```

Create `package.xml`:

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>my_moveit_interfaces</name>
  <version>0.1.0</version>
  <description>Custom command interfaces for the learning MoveIt arm.</description>
  <maintainer email="3099307805@qq.com">Jay</maintainer>
  <license>BSD-3-Clause</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <build_depend>rosidl_default_generators</build_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>
```

- [ ] **Step 5: Run the interface contract and verify GREEN**

Run:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k pose_command_interface -v
```

Expected: one selected test PASS.

- [ ] **Step 6: Commit the interface**

```powershell
git add src/my_moveit_interfaces src/my_robot_moveit_config/test/test_moveit_config.py
git commit -m "feat: add Sunyijie pose command interface"
```

---

### Task 2: Pure command validation and mapping

**Files:**
- Create: `src/my_robot_commander/test/test_command_utils.cpp`
- Create: `src/my_robot_commander/include/my_robot_commander/command_utils.hpp`
- Create: `src/my_robot_commander/src/command_utils.cpp`
- Create: `src/my_robot_commander/CMakeLists.txt`
- Create: `src/my_robot_commander/package.xml`

**Interfaces:**
- Consumes: `geometry_msgs::msg::Pose` and TF2 quaternion conversion.
- Produces:
  - `PoseCommandValues`
  - `bool hasSixFiniteJointValues(const std::vector<double>&)`
  - `bool hasFinitePoseValues(const PoseCommandValues&)`
  - `geometry_msgs::msg::Pose makePose(const PoseCommandValues&)`
  - `std::string_view gripperNamedTarget(bool sunyijie_gripper)`

- [ ] **Step 1: Scaffold the commander package and write the failing C++ test**

Create `test/test_command_utils.cpp`:

```cpp
#include <cmath>
#include <limits>
#include <vector>

#include <gtest/gtest.h>

#include "my_robot_commander/command_utils.hpp"

namespace my_robot_commander
{
TEST(CommandUtils, RequiresExactlySixFiniteJointValues)
{
  EXPECT_TRUE(hasSixFiniteJointValues({0.0, 0.1, 0.2, 0.3, 0.4, 0.5}));
  EXPECT_FALSE(hasSixFiniteJointValues({0.0, 0.1, 0.2, 0.3, 0.4}));
  EXPECT_FALSE(hasSixFiniteJointValues(
    {0.0, 0.1, 0.2, std::numeric_limits<double>::quiet_NaN(), 0.4, 0.5}));
}

TEST(CommandUtils, ValidatesPoseAndConvertsRollPitchYaw)
{
  constexpr double pi = 3.14159265358979323846;
  PoseCommandValues values{0.7, 0.6, 0.4, pi, 0.0, 0.0};
  EXPECT_TRUE(hasFinitePoseValues(values));

  const auto pose = makePose(values);
  EXPECT_DOUBLE_EQ(0.7, pose.position.x);
  EXPECT_DOUBLE_EQ(0.6, pose.position.y);
  EXPECT_DOUBLE_EQ(0.4, pose.position.z);
  EXPECT_NEAR(1.0, pose.orientation.x, 1e-9);
  EXPECT_NEAR(0.0, pose.orientation.y, 1e-9);
  EXPECT_NEAR(0.0, pose.orientation.z, 1e-9);
  EXPECT_NEAR(0.0, pose.orientation.w, 1e-9);

  values.y = std::numeric_limits<double>::infinity();
  EXPECT_FALSE(hasFinitePoseValues(values));
}

TEST(CommandUtils, MapsPersonalBooleanToExistingNamedTargets)
{
  EXPECT_EQ("gripper_close", gripperNamedTarget(true));
  EXPECT_EQ("gripper_open", gripperNamedTarget(false));
}
}  // namespace my_robot_commander
```

Create initial `CMakeLists.txt` that only configures the failing test:

```cmake
cmake_minimum_required(VERSION 3.22)
project(my_robot_commander)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_command_utils test/test_command_utils.cpp)
  target_include_directories(test_command_utils PRIVATE include)
  ament_target_dependencies(test_command_utils geometry_msgs)
endif()

ament_package()
```

Create `package.xml` with the dependencies used by the final package:

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>my_robot_commander</name>
  <version>0.1.0</version>
  <description>C++ MoveIt commander for the learning arm and gripper.</description>
  <maintainer email="3099307805@qq.com">Jay</maintainer>
  <license>BSD-3-Clause</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>geometry_msgs</depend>
  <depend>moveit_msgs</depend>
  <depend>moveit_ros_planning_interface</depend>
  <depend>my_moveit_interfaces</depend>
  <depend>rclcpp</depend>
  <depend>std_msgs</depend>
  <depend>tf2</depend>
  <test_depend>ament_cmake_gtest</test_depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
```

- [ ] **Step 2: Publish the RED test to the feature branch and verify it fails on the VM**

```powershell
git add src/my_robot_commander
git commit -m "test: define commander utility contract"
git push -u origin feat/sunyijie-compound-command
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && git fetch origin && git switch -C feat/sunyijie-compound-command origin/feat/sunyijie-compound-command && source /opt/ros/jazzy/setup.bash && colcon build --packages-select my_moveit_interfaces my_robot_commander --event-handlers console_direct+"
```

Expected: build FAIL because `my_robot_commander/command_utils.hpp` does not
exist. This is the required RED evidence.

- [ ] **Step 3: Implement the utility header**

Create `command_utils.hpp`:

```cpp
#pragma once

#include <string_view>
#include <vector>

#include <geometry_msgs/msg/pose.hpp>

namespace my_robot_commander
{
struct PoseCommandValues
{
  double x;
  double y;
  double z;
  double roll;
  double pitch;
  double yaw;
};

bool hasSixFiniteJointValues(const std::vector<double> & joint_values);
bool hasFinitePoseValues(const PoseCommandValues & values);
geometry_msgs::msg::Pose makePose(const PoseCommandValues & values);
std::string_view gripperNamedTarget(bool sunyijie_gripper);
}  // namespace my_robot_commander
```

- [ ] **Step 4: Implement the utility source**

Create `command_utils.cpp`:

```cpp
#include "my_robot_commander/command_utils.hpp"

#include <algorithm>
#include <array>
#include <cmath>

#include <tf2/LinearMath/Quaternion.h>

namespace my_robot_commander
{
bool hasSixFiniteJointValues(const std::vector<double> & joint_values)
{
  return joint_values.size() == 6 &&
         std::all_of(joint_values.begin(), joint_values.end(),
           [](double value) { return std::isfinite(value); });
}

bool hasFinitePoseValues(const PoseCommandValues & values)
{
  const std::array<double, 6> numeric_values{
    values.x, values.y, values.z, values.roll, values.pitch, values.yaw};
  return std::all_of(numeric_values.begin(), numeric_values.end(),
    [](double value) { return std::isfinite(value); });
}

geometry_msgs::msg::Pose makePose(const PoseCommandValues & values)
{
  geometry_msgs::msg::Pose pose;
  pose.position.x = values.x;
  pose.position.y = values.y;
  pose.position.z = values.z;
  tf2::Quaternion quaternion;
  quaternion.setRPY(values.roll, values.pitch, values.yaw);
  quaternion.normalize();
  pose.orientation.x = quaternion.x();
  pose.orientation.y = quaternion.y();
  pose.orientation.z = quaternion.z();
  pose.orientation.w = quaternion.w();
  return pose;
}

std::string_view gripperNamedTarget(bool sunyijie_gripper)
{
  return sunyijie_gripper ? "gripper_close" : "gripper_open";
}
}  // namespace my_robot_commander
```

- [ ] **Step 5: Update CMake to build and link the utility**

Replace `CMakeLists.txt` with this complete GREEN configuration:

```cmake
cmake_minimum_required(VERSION 3.22)
project(my_robot_commander)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)

add_library(command_utils src/command_utils.cpp)
target_include_directories(command_utils PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
ament_target_dependencies(command_utils geometry_msgs tf2)

install(DIRECTORY include/ DESTINATION include)
install(TARGETS command_utils EXPORT command_utilsTargets
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_command_utils test/test_command_utils.cpp)
  target_include_directories(test_command_utils PRIVATE include)
  target_link_libraries(test_command_utils command_utils)
  ament_target_dependencies(test_command_utils geometry_msgs)
endif()

ament_export_targets(command_utilsTargets HAS_LIBRARY_TARGET)
ament_export_dependencies(geometry_msgs tf2)
ament_package()
```

- [ ] **Step 6: Verify GREEN on the VM**

Copy only the uncommitted Task 2 implementation into the already checked-out
VM feature branch, then build it before committing:

```powershell
scp -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm -r src/my_robot_commander/include src/my_robot_commander/src src/my_robot_commander/CMakeLists.txt jay@192.168.72.200:/home/jay/moveit_ws/src/my_robot_commander/
```

```bash
source /opt/ros/jazzy/setup.bash
cd /home/jay/moveit_ws
colcon build --cmake-clean-cache --packages-select my_moveit_interfaces my_robot_commander --event-handlers console_direct+
source install/setup.bash
colcon test --packages-select my_robot_commander --event-handlers console_direct+
colcon test-result --verbose
```

Expected: build succeeds and all three GTests pass with zero failures.

- [ ] **Step 7: Commit the utility implementation**

```powershell
git add src/my_robot_commander
git commit -m "feat: validate MoveIt command values"
git push origin feat/sunyijie-compound-command
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && git fetch origin && git reset --mixed origin/feat/sunyijie-compound-command && git status --short"
```

Expected: the VM worktree becomes clean without discarding its verified file
contents.

---

### Task 3: Restore the C++ commander and add compound sequencing

**Files:**
- Modify: `src/my_robot_moveit_config/test/test_moveit_config.py`
- Create: `src/my_robot_commander/include/my_robot_commander/commander.hpp`
- Create: `src/my_robot_commander/src/commander.cpp`
- Create: `src/my_robot_commander/src/main.cpp`
- Modify: `src/my_robot_commander/CMakeLists.txt`

**Interfaces:**
- Consumes: Task 1 message and Task 2 utilities.
- Produces: executable `my_robot_commander`; subscribers on
  `/gripper_command`, `/joint_command`, and `/pose_command`.

- [ ] **Step 1: Add the failing commander source contract**

Add:

```python
COMMANDER_PACKAGE = WORKSPACE_SRC / "my_robot_commander"
COMMANDER_SOURCE = COMMANDER_PACKAGE / "src" / "commander.cpp"
COMMANDER_MAIN = COMMANDER_PACKAGE / "src" / "main.cpp"
```

Add this test:

```python
def test_cpp_commander_restores_course_topics_and_compound_field(self):
    source = COMMANDER_SOURCE.read_text(encoding="utf-8")
    main = COMMANDER_MAIN.read_text(encoding="utf-8")
    for topic in ("/gripper_command", "/joint_command", "/pose_command"):
        self.assertIn(topic, source)
    for method in (
        "planAndExecute",
        "goToNamedTarget",
        "goToJointTarget",
        "goToPoseTarget",
        "poseCommandCallback",
    ):
        self.assertIn(method, source)
    self.assertIn("msg->sunyijie_gripper", source)
    self.assertIn("moveSunyijieGripper", source)
    self.assertLess(
        source.index("goToPoseTarget(values, msg->cartesian_path)"),
        source.index("moveSunyijieGripper(msg->sunyijie_gripper)"),
    )
    self.assertIn("MultiThreadedExecutor", main)
```

- [ ] **Step 2: Run the source contract and verify RED**

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k cpp_commander -v
```

Expected: FAIL because `commander.cpp` does not exist.

- [ ] **Step 3: Declare `MyRobotCommander`**

Create `commander.hpp` with these exact members:

```cpp
#pragma once

#include <memory>
#include <string>
#include <vector>

#include <moveit/move_group_interface/move_group_interface.h>
#include <my_moveit_interfaces/msg/pose_command.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>

#include "my_robot_commander/command_utils.hpp"

namespace my_robot_commander
{
class MyRobotCommander
{
public:
  explicit MyRobotCommander(rclcpp::Node::SharedPtr node);

private:
  using MoveGroupInterface =
    moveit::planning_interface::MoveGroupInterface;

  bool planAndExecute(MoveGroupInterface & move_group);
  bool goToNamedTarget(MoveGroupInterface & move_group,
    const std::string & target_name);
  bool goToJointTarget(const std::vector<double> & joint_values);
  bool goToPoseTarget(const PoseCommandValues & values, bool cartesian_path);
  bool moveSunyijieGripper(bool sunyijie_gripper);

  void gripperCommandCallback(const std_msgs::msg::Bool::SharedPtr msg);
  void jointCommandCallback(
    const std_msgs::msg::Float64MultiArray::SharedPtr msg);
  void poseCommandCallback(
    const my_moveit_interfaces::msg::PoseCommand::SharedPtr msg);

  rclcpp::Node::SharedPtr node_;
  MoveGroupInterface arm_move_group_;
  MoveGroupInterface gripper_move_group_;
  rclcpp::CallbackGroup::SharedPtr command_callback_group_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr gripper_subscription_;
  rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr
    joint_subscription_;
  rclcpp::Subscription<my_moveit_interfaces::msg::PoseCommand>::SharedPtr
    pose_subscription_;
};
}  // namespace my_robot_commander
```

- [ ] **Step 4: Implement subscriptions and MoveIt methods**

Implement `commander.cpp` using:

```cpp
#include "my_robot_commander/commander.hpp"

#include <exception>
#include <functional>
#include <utility>

#include <moveit_msgs/msg/robot_trajectory.hpp>

namespace my_robot_commander
{
MyRobotCommander::MyRobotCommander(rclcpp::Node::SharedPtr node)
: node_(std::move(node)),
  arm_move_group_(node_, "arm"),
  gripper_move_group_(node_, "gripper")
{
  command_callback_group_ = node_->create_callback_group(
    rclcpp::CallbackGroupType::MutuallyExclusive);
  rclcpp::SubscriptionOptions options;
  options.callback_group = command_callback_group_;

  gripper_subscription_ = node_->create_subscription<std_msgs::msg::Bool>(
    "/gripper_command", rclcpp::QoS(10),
    std::bind(&MyRobotCommander::gripperCommandCallback, this,
      std::placeholders::_1), options);
  joint_subscription_ =
    node_->create_subscription<std_msgs::msg::Float64MultiArray>(
      "/joint_command", rclcpp::QoS(10),
      std::bind(&MyRobotCommander::jointCommandCallback, this,
        std::placeholders::_1), options);
  pose_subscription_ =
    node_->create_subscription<my_moveit_interfaces::msg::PoseCommand>(
      "/pose_command", rclcpp::QoS(10),
      std::bind(&MyRobotCommander::poseCommandCallback, this,
        std::placeholders::_1), options);
}

bool MyRobotCommander::planAndExecute(MoveGroupInterface & move_group)
{
  MoveGroupInterface::Plan plan;
  const auto plan_result = move_group.plan(plan);
  if (plan_result != moveit::core::MoveItErrorCode::SUCCESS) {
    RCLCPP_ERROR(node_->get_logger(), "Planning failed for group %s",
      move_group.getName().c_str());
    return false;
  }
  const auto execute_result = move_group.execute(plan);
  if (execute_result != moveit::core::MoveItErrorCode::SUCCESS) {
    RCLCPP_ERROR(node_->get_logger(), "Execution failed for group %s",
      move_group.getName().c_str());
    return false;
  }
  return true;
}

bool MyRobotCommander::goToNamedTarget(
  MoveGroupInterface & move_group, const std::string & target_name)
{
  move_group.setStartStateToCurrentState();
  if (!move_group.setNamedTarget(target_name)) {
    RCLCPP_ERROR(node_->get_logger(), "Unknown target %s for group %s",
      target_name.c_str(), move_group.getName().c_str());
    return false;
  }
  return planAndExecute(move_group);
}

bool MyRobotCommander::goToJointTarget(
  const std::vector<double> & joint_values)
{
  arm_move_group_.setStartStateToCurrentState();
  if (!arm_move_group_.setJointValueTarget(joint_values)) {
    RCLCPP_ERROR(node_->get_logger(), "Arm joint target violates bounds");
    return false;
  }
  return planAndExecute(arm_move_group_);
}

bool MyRobotCommander::goToPoseTarget(
  const PoseCommandValues & values, bool cartesian_path)
{
  const auto pose = makePose(values);
  arm_move_group_.setStartStateToCurrentState();
  if (cartesian_path) {
    std::vector<geometry_msgs::msg::Pose> waypoints{pose};
    moveit_msgs::msg::RobotTrajectory trajectory;
    const double fraction = arm_move_group_.computeCartesianPath(
      waypoints, 0.01, 0.0, trajectory);
    if (fraction < 0.999) {
      RCLCPP_ERROR(node_->get_logger(),
        "Cartesian path incomplete: %.1f%%", fraction * 100.0);
      return false;
    }
    return arm_move_group_.execute(trajectory) ==
      moveit::core::MoveItErrorCode::SUCCESS;
  }

  arm_move_group_.setPoseTarget(pose);
  const bool succeeded = planAndExecute(arm_move_group_);
  arm_move_group_.clearPoseTargets();
  return succeeded;
}

bool MyRobotCommander::moveSunyijieGripper(bool sunyijie_gripper)
{
  return goToNamedTarget(
    gripper_move_group_, std::string(gripperNamedTarget(sunyijie_gripper)));
}
```

Implement the callbacks with exception boundaries and the exact compound
ordering:

```cpp
void MyRobotCommander::gripperCommandCallback(
  const std_msgs::msg::Bool::SharedPtr msg)
{
  try {
    const bool sunyijie_gripper = msg->data;
    moveSunyijieGripper(sunyijie_gripper);
  } catch (const std::exception & exception) {
    RCLCPP_ERROR(node_->get_logger(), "Gripper command failed: %s",
      exception.what());
  }
}

void MyRobotCommander::jointCommandCallback(
  const std_msgs::msg::Float64MultiArray::SharedPtr msg)
{
  try {
    if (!hasSixFiniteJointValues(msg->data)) {
      RCLCPP_ERROR(node_->get_logger(),
        "Joint command must contain exactly six finite values");
      return;
    }
    goToJointTarget(msg->data);
  } catch (const std::exception & exception) {
    RCLCPP_ERROR(node_->get_logger(), "Joint command failed: %s",
      exception.what());
  }
}

void MyRobotCommander::poseCommandCallback(
  const my_moveit_interfaces::msg::PoseCommand::SharedPtr msg)
{
  try {
    const PoseCommandValues values{
      msg->x, msg->y, msg->z, msg->roll, msg->pitch, msg->yaw};
    if (!hasFinitePoseValues(values)) {
      RCLCPP_ERROR(node_->get_logger(),
        "Pose command must contain finite values");
      return;
    }
    if (!goToPoseTarget(values, msg->cartesian_path)) {
      RCLCPP_ERROR(node_->get_logger(),
        "Arm command failed; sunyijie_gripper was not executed");
      return;
    }
    if (!moveSunyijieGripper(msg->sunyijie_gripper)) {
      RCLCPP_ERROR(node_->get_logger(),
        "Arm succeeded but sunyijie_gripper command failed");
      return;
    }
    RCLCPP_INFO(node_->get_logger(),
      "Compound command succeeded; sunyijie_gripper=%s",
      msg->sunyijie_gripper ? "true" : "false");
  } catch (const std::exception & exception) {
    RCLCPP_ERROR(node_->get_logger(), "Pose command failed: %s",
      exception.what());
  }
}
}  // namespace my_robot_commander
```

- [ ] **Step 5: Add the multi-threaded executable entry point**

Create `main.cpp`:

```cpp
#include <memory>

#include <rclcpp/rclcpp.hpp>

#include "my_robot_commander/commander.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  const auto options = rclcpp::NodeOptions()
    .automatically_declare_parameters_from_overrides(true);
  auto node = std::make_shared<rclcpp::Node>(
    "my_robot_commander", options);
  auto commander =
    std::make_shared<my_robot_commander::MyRobotCommander>(node);

  rclcpp::executors::MultiThreadedExecutor executor(
    rclcpp::ExecutorOptions(), 2);
  executor.add_node(node);
  executor.spin();
  executor.remove_node(node);
  commander.reset();
  node.reset();
  rclcpp::shutdown();
  return 0;
}
```

- [ ] **Step 6: Build and install the executable**

Add these package lookups to `CMakeLists.txt`:

```cmake
find_package(moveit_msgs REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(my_moveit_interfaces REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
```

Add the executable and install rule:

```cmake
add_executable(my_robot_commander
  src/main.cpp
  src/commander.cpp)
target_include_directories(my_robot_commander PRIVATE include)
target_link_libraries(my_robot_commander command_utils)
ament_target_dependencies(my_robot_commander
  geometry_msgs
  moveit_msgs
  moveit_ros_planning_interface
  my_moveit_interfaces
  rclcpp
  std_msgs)

install(TARGETS my_robot_commander
  RUNTIME DESTINATION lib/${PROJECT_NAME})
```

- [ ] **Step 7: Verify the static source contract and utility tests**

Run locally:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k "cpp_commander or pose_command_interface" -v
```

Copy the uncommitted commander header, sources, and CMake file to the VM, then
run the ROS build and tests before committing:

```powershell
scp -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm -r src/my_robot_commander/include src/my_robot_commander/src src/my_robot_commander/CMakeLists.txt jay@192.168.72.200:/home/jay/moveit_ws/src/my_robot_commander/
```

```bash
source /opt/ros/jazzy/setup.bash
cd /home/jay/moveit_ws
colcon build --cmake-clean-cache --packages-select my_moveit_interfaces my_robot_commander --event-handlers console_direct+
source install/setup.bash
colcon test --packages-select my_robot_commander --event-handlers console_direct+
colcon test-result --verbose
```

Expected: static tests pass, both packages build, and all utility tests pass.

- [ ] **Step 8: Commit the commander**

```powershell
git add src/my_robot_commander src/my_robot_moveit_config/test/test_moveit_config.py
git commit -m "feat: add compound MoveIt commander"
git push origin feat/sunyijie-compound-command
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && git fetch origin && git reset --mixed origin/feat/sunyijie-compound-command && git status --short"
```

---

### Task 4: Demo launch integration and recording commands

**Files:**
- Modify: `src/my_robot_moveit_config/test/test_moveit_config.py`
- Modify: `src/my_robot_moveit_config/launch/demo.launch.py`
- Modify: `src/my_robot_moveit_config/package.xml`
- Create: `src/my_robot_commander/README.md`

**Interfaces:**
- Consumes: executable `my_robot_commander` and the existing MoveIt config.
- Produces: one launch command that starts the complete demo and a five-command recording sequence.

- [ ] **Step 1: Add the failing launch contract**

Extend the launch test with:

```python
demo_text = (LAUNCH_DIR / "demo.launch.py").read_text(encoding="utf-8")
self.assertIn("from launch_ros.actions import Node", demo_text)
self.assertIn('package="my_robot_commander"', demo_text)
self.assertIn('executable="my_robot_commander"', demo_text)
self.assertIn("parameters=[moveit_config.to_dict()]", demo_text)
```

Extend the package dependency test:

```python
self.assertIn("my_robot_commander", runtime_dependencies)
```

- [ ] **Step 2: Run the launch contract and verify RED**

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k "launch_files or package_select" -v
```

Expected: FAIL because the demo does not start the commander and the manifest
does not depend on it.

- [ ] **Step 3: Add the commander to `demo.launch.py`**

Replace the function body with:

```python
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_demo_launch


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder(
        "my_robot", package_name="my_robot_moveit_config"
    ).to_moveit_configs()
    launch_description = generate_demo_launch(moveit_config)
    launch_description.add_action(
        Node(
            package="my_robot_commander",
            executable="my_robot_commander",
            name="my_robot_commander",
            output="screen",
            parameters=[moveit_config.to_dict()],
        )
    )
    return launch_description
```

Add to `package.xml`:

```xml
<exec_depend>my_robot_commander</exec_depend>
```

- [ ] **Step 4: Create the recording README**

Document the launch command:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/moveit_ws
source install/setup.bash
ros2 launch my_robot_moveit_config demo.launch.py
```

Document these five commands in order:

```bash
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.7, y: 0.6, z: 0.7, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: false, sunyijie_gripper: false}"
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.7, y: 0.6, z: 0.4, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: true, sunyijie_gripper: true}"
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.7, y: 0.6, z: 0.7, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: true, sunyijie_gripper: true}"
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.6, y: -0.7, z: 0.7, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: false, sunyijie_gripper: true}"
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.6, y: -0.7, z: 0.4, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: true, sunyijie_gripper: false}"
```

Explain that command 1 approaches and opens, command 2 descends and closes,
command 3 lifts vertically, command 4 rotates/transfers, and command 5
descends and opens. If VM validation proves a coordinate unreachable, replace
only that coordinate with the nearest empirically verified value and rerun all
five commands before finalizing the README.

- [ ] **Step 5: Verify all local static tests**

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit launch integration and documentation**

```powershell
git add src/my_robot_moveit_config src/my_robot_commander/README.md
git commit -m "feat: launch compound MoveIt control"
```

---

### Task 5: Ubuntu build and runtime acceptance

**Files:**
- Verify: all Task 1-4 files.
- Modify only if runtime evidence identifies a concrete build or reachability defect.

**Interfaces:**
- Consumes: pushed feature branch.
- Produces: verified ROS interface, executable, controllers, compound commands, and final recording sequence.

- [ ] **Step 1: Push and synchronize the exact feature commit**

```powershell
git status --short
git push -u origin feat/sunyijie-compound-command
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && git fetch origin && git switch -C feat/sunyijie-compound-command origin/feat/sunyijie-compound-command && git status --short && git rev-parse HEAD"
```

Expected: clean VM status and identical local/VM commit hashes.

- [ ] **Step 2: Cleanly build the four affected packages**

```bash
cd /home/jay/moveit_ws
source /opt/ros/jazzy/setup.bash
colcon build --cmake-clean-cache --symlink-install --packages-select my_moveit_interfaces my_robot_commander my_robot_description my_robot_moveit_config --event-handlers console_direct+
```

Expected: all four packages finish successfully with exit code 0.

- [ ] **Step 3: Run all package tests**

```bash
source install/setup.bash
colcon test --packages-select my_robot_commander my_robot_moveit_config --event-handlers console_direct+
colcon test-result --verbose
```

Expected: zero failures and zero errors.

- [ ] **Step 4: Verify the generated interface**

```bash
source /opt/ros/jazzy/setup.bash
source /home/jay/moveit_ws/install/setup.bash
ros2 interface show my_moveit_interfaces/msg/PoseCommand
```

Expected: the exact eight fields from Task 1, ending in
`bool sunyijie_gripper`.

- [ ] **Step 5: Start the demo under the VM desktop**

```bash
cd /home/jay/moveit_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
DISPLAY=:0 nohup ros2 launch my_robot_moveit_config demo.launch.py > /tmp/sunyijie_moveit_demo.log 2>&1 &
echo $! > /tmp/sunyijie_moveit_demo.pid
```

Poll the log for up to 30 seconds and fail acceptance if the commander,
move_group, RViz, or a controller exits.

- [ ] **Step 6: Inspect nodes, topics, and controllers**

```bash
ros2 node list
ros2 topic info /pose_command -v
ros2 control list_controllers
```

Expected:

- `/my_robot_commander` is present.
- `/pose_command` has one subscriber of type
  `my_moveit_interfaces/msg/PoseCommand`.
- `arm_controller`, `gripper_controller`, and `joint_state_broadcaster` are
  all `active`.

- [ ] **Step 7: Execute and verify the five-command sequence**

Run the five README commands one at a time. After the close command and after
the final open command, run:

```bash
ros2 topic echo /joint_states --once
```

Expected:

- command 1 succeeds through ordinary pose planning and opens to `0.034 m`.
- command 2 reports a Cartesian fraction of at least `0.999`, then closes to
  `0.000 m`.
- command 3 produces a vertical lift while staying closed.
- command 4 visibly rotates/transfers around the base while staying closed.
- command 5 produces a vertical descent and opens to `0.034 m`.
- `/tmp/sunyijie_moveit_demo.log` contains five compound-success messages and
  no planning or execution failure for the accepted sequence.

- [ ] **Step 8: Fix only evidence-backed runtime defects and rerun acceptance**

For a compiler error, preserve the declared interfaces and make the smallest
API-compatible change. For an unreachable coordinate, change the README to
the nearest verified reachable coordinate while retaining the same five-stage
motion and at least `0.30 m` of vertical lift/descent. After any change, rerun
Steps 2-7 in full and commit with a focused `fix:` message.

- [ ] **Step 9: Stop only the demo started by this task**

```bash
if test -f /tmp/sunyijie_moveit_demo.pid; then
  kill "$(cat /tmp/sunyijie_moveit_demo.pid)"
fi
```

Expected: the recorded launch process exits without targeting unrelated
processes.

---

### Task 6: Final integration and synchronization

**Files:**
- Verify: complete repository diff and history.

**Interfaces:**
- Consumes: runtime-verified feature branch.
- Produces: identical verified `main` commits locally, on GitHub, and on the VM.

- [ ] **Step 1: Run fresh local verification**

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -v
git diff --check main...HEAD
git status --short
```

Expected: all tests pass, no whitespace errors, and a clean worktree.

- [ ] **Step 2: Review the feature diff against the design**

Verify every requirement in
`docs/superpowers/specs/2026-08-03-sunyijie-compound-moveit-command-design.md`
has a corresponding file, test, or runtime result. Confirm
`src/robot_description` has no diff.

- [ ] **Step 3: Finish the branch**

Invoke `superpowers:finishing-a-development-branch`, choose local merge to
`main`, and rerun the full local static test after the merge.

- [ ] **Step 4: Push and align all three repositories**

```powershell
git push origin main
git rev-parse main
git rev-parse origin/main
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && git switch main && git pull --ff-only origin main && git status --short && git rev-parse HEAD"
```

Expected: local `main`, `origin/main`, and VM `main` print the same commit hash
and both worktrees are clean.

- [ ] **Step 5: Hand off recording instructions**

Report:

- the verified commit hash
- the launch command
- the absolute path to `src/my_robot_commander/README.md`
- the five verified `ros2 topic pub -1` commands
- confirmation that build, tests, controllers, topic subscription, Cartesian
  motion, close, and open were observed successfully

Do not record or upload the video; the user owns that final step.
