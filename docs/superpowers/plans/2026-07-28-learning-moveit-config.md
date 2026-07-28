# Learning Robot MoveIt Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `my_robot_moveit_config` with a ROS 2 Jazzy MoveIt 2 configuration for `my_robot_description/urdf/arm.xacro`.

**Architecture:** Keep `my_robot_description` as the sole robot model source and wrap it once inside the MoveIt package to add one `mock_components/GenericSystem` ros2_control system. Keep the conventional package name and standard MoveIt launch entry points, while replacing all mature-model semantic, joint, controller, and package dependency data.

**Tech Stack:** ROS 2 Jazzy, MoveIt 2, Xacro, SRDF, ros2_control, JointTrajectoryController, CMake/ament, Python unittest, PyYAML.

## Global Constraints

- Do not modify or delete `robot_description`.
- Do not modify `my_robot_description/urdf/arm.xacro`.
- Keep the package name `my_robot_moveit_config`.
- Use joint order `joint1`, `joint2`, `joint3`, `joint4`, `joint5`, `joint6`.
- Clamp `pose_2/joint2` to the URDF upper limit `1.57`.
- Export exactly one position command interface per arm joint.
- Use zero final trajectory velocity enforcement.
- Do not create Git commits until the user configures repository Git identity.

---

## File Structure

- `src/my_robot_moveit_config/test/test_moveit_config.py`: permanent static contract test for model, SRDF, named poses, controllers, ros2_control, and package dependencies.
- `src/my_robot_moveit_config/config/my_robot.srdf`: planning group, world joint, collision exclusions, and named states.
- `src/my_robot_moveit_config/config/my_robot.urdf.xacro`: learning-model wrapper and single ros2_control macro invocation.
- `src/my_robot_moveit_config/config/my_robot.ros2_control.xacro`: six-joint GenericSystem definition.
- `src/my_robot_moveit_config/config/*.yaml`: initial positions, limits, kinematics, MoveIt controller, ros2_control controller, and Pilz Cartesian limits.
- `src/my_robot_moveit_config/package.xml`: direct runtime and test dependencies.
- `src/my_robot_moveit_config/CMakeLists.txt`: resource installation and static test registration.
- `src/my_robot_moveit_config/.setup_assistant`: Setup Assistant source metadata with unique YAML keys.
- `src/my_robot_moveit_config/launch/*.launch.py`: standard MoveItConfigsBuilder launch entry points.
- `src/my_robot_moveit_config/config/moveit.rviz`: learning-arm RViz MotionPlanning layout.

### Task 1: Add the Static Configuration Contract

**Files:**
- Create: `src/my_robot_moveit_config/test/test_moveit_config.py`

**Interfaces:**
- Consumes: current package files and `my_robot_description/urdf/arm.xacro`.
- Produces: `python -B -m unittest discover -s src/my_robot_moveit_config/test -v` acceptance command.

- [ ] **Step 1: Write the failing contract tests**

Create unittest cases that assert:

```python
EXPECTED_JOINTS = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
EXPECTED_POSES = {
    "home": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "pose_1": [1.1705, 1.1686, 0.9172, 1.2449, 0.9940, 1.0596],
    "pose_2": [1.5421, 1.57, 0.5030, 0.2787, 1.3285, 1.7659],
}
```

The tests must validate source package selection, SRDF references and limits,
joint ordering, one ros2_control system, controller interfaces, package
dependencies, unique Setup Assistant keys, and absence of mature-model joint
names.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
python -B -m unittest discover -s src/my_robot_moveit_config/test -v
```

Expected: failures showing that the current package references
`robot_description` and uses `base_yaw_joint` and the other mature-model joint
names.

### Task 2: Replace Robot Semantics and Fake Hardware

**Files:**
- Replace: `src/my_robot_moveit_config/config/my_robot.srdf`
- Replace: `src/my_robot_moveit_config/config/my_robot.urdf.xacro`
- Replace: `src/my_robot_moveit_config/config/my_robot.ros2_control.xacro`
- Replace: `src/my_robot_moveit_config/config/initial_positions.yaml`
- Replace: `src/my_robot_moveit_config/config/joint_limits.yaml`
- Replace: `src/my_robot_moveit_config/config/kinematics.yaml`
- Replace: `src/my_robot_moveit_config/config/moveit_controllers.yaml`
- Replace: `src/my_robot_moveit_config/config/ros2_controllers.yaml`
- Retain with validation: `src/my_robot_moveit_config/config/pilz_cartesian_limits.yaml`

**Interfaces:**
- Consumes: `my_robot_description/urdf/arm.xacro` link names, joint names, and limits.
- Produces: `arm` chain from `base_link` to `tool_link`, six-joint trajectory controller, and one GenericSystem.

- [ ] **Step 1: Replace SRDF semantics**

Define the `arm` chain, `home`, `pose_1`, `pose_2`, fixed `world` joint, and only
adjacent-link collision exclusions.

- [ ] **Step 2: Replace the MoveIt Xacro wrapper**

Include:

```xml
<xacro:include filename="$(find my_robot_description)/urdf/arm.xacro"/>
<xacro:include filename="my_robot.ros2_control.xacro"/>
<xacro:my_robot_ros2_control
  name="FakeSystem"
  initial_positions_file="$(arg initial_positions_file)"/>
```

- [ ] **Step 3: Define one six-joint GenericSystem**

Each joint exports one `position` command interface and `position` plus
`velocity` state interfaces. Initial position values come from
`initial_positions.yaml`.

- [ ] **Step 4: Replace controller and planning YAML**

Use identical six-joint order in both controller files, KDL timeout `0.05`,
velocity and acceleration scaling `0.1`, and per-joint acceleration limit
`1.0`.

- [ ] **Step 5: Run the focused tests**

Run:

```powershell
python -B -m unittest discover -s src/my_robot_moveit_config/test -v
```

Expected: robot semantics and controller tests pass; package metadata tests
remain failing until Task 3.

### Task 3: Replace Package Metadata and Setup Assistant State

**Files:**
- Replace: `src/my_robot_moveit_config/package.xml`
- Replace: `src/my_robot_moveit_config/CMakeLists.txt`
- Replace: `src/my_robot_moveit_config/.setup_assistant`

**Interfaces:**
- Consumes: static contract test and standard MoveIt launch/config directories.
- Produces: self-contained ament package depending on `my_robot_description`.

- [ ] **Step 1: Replace package dependencies**

Declare `my_robot_description`, MoveIt runtime packages, Xacro,
`controller_manager`, `ros2_control`, `joint_trajectory_controller`,
`joint_state_broadcaster`, RViz, robot state publisher, warehouse support, and
test dependencies `ament_cmake_pytest` and `python3-yaml`. Do not declare
`robot_description`.

- [ ] **Step 2: Register the validation test**

Under `BUILD_TESTING`, use:

```cmake
find_package(ament_cmake_pytest REQUIRED)
ament_add_pytest_test(
  moveit_config_validation
  test/test_moveit_config.py
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
)
```

Install `launch`, `config`, and `.setup_assistant`, then call
`ament_package()`.

- [ ] **Step 3: Replace Setup Assistant metadata**

Point the URDF source to package `my_robot_description`, path
`urdf/arm.xacro`, and keep exactly one `control_xacro` key.

- [ ] **Step 4: Run the full static contract**

Run:

```powershell
python -B -m unittest discover -s src/my_robot_moveit_config/test -v
```

Expected: all tests pass.

### Task 4: Validate the Replacement Package

**Files:**
- Verify: `src/my_robot_moveit_config/**`
- Verify unchanged: `src/robot_description/**`
- Verify unchanged: `src/my_robot_description/urdf/arm.xacro`

**Interfaces:**
- Consumes: completed replacement package.
- Produces: static verification evidence and ROS-environment follow-up commands.

- [ ] **Step 1: Parse every text configuration**

Run a read-only validation that parses Python with `ast`, XML/Xacro/SRDF with
`xml.etree.ElementTree`, and YAML with a duplicate-key loader.

- [ ] **Step 2: Run the complete static contract again**

Run:

```powershell
python -B -m unittest discover -s src/my_robot_moveit_config/test -v
```

Expected: all tests pass with zero failures.

- [ ] **Step 3: Check repository scope**

Run:

```powershell
git diff --check
git status --short
git diff -- src/robot_description src/my_robot_description/urdf/arm.xacro
```

Expected: no whitespace errors and no changes to either protected target.

- [ ] **Step 4: Run ROS validation when Jazzy is sourced**

Run:

```bash
colcon build --packages-select my_robot_description my_robot_moveit_config
source install/setup.bash
xacro install/my_robot_moveit_config/share/my_robot_moveit_config/config/my_robot.urdf.xacro > /tmp/my_robot.urdf
check_urdf /tmp/my_robot.urdf
ros2 launch my_robot_moveit_config demo.launch.py
```

Expected: build succeeds, URDF validates, `arm_controller` and
`joint_state_broadcaster` become active, and `home`, `pose_1`, and `pose_2` can be
planned and executed in RViz.
