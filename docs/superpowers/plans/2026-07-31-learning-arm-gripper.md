# Learning Arm Gripper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a rigidly mounted, symmetrically actuated two-finger gripper to the learning arm and make `gripper_open`, `gripper_half_open`, and `gripper_close` selectable and executable through MoveIt 2.

**Architecture:** Extend the learning URDF with a fixed gripper base, one commanded prismatic finger joint, one mirrored mimic joint, and a grasp-centered `tool_link`. Add an independent MoveIt `gripper` group and ROS 2 gripper action controller while preserving the existing six-joint arm group and trajectory controller.

**Tech Stack:** ROS 2 Jazzy, MoveIt 2, Xacro/URDF, SRDF, ros2_control `mock_components/GenericSystem`, `position_controllers/GripperActionController`, Python `unittest`, YAML, CMake/colcon.

## Global Constraints

- Work in `moveit_ws`; keep `robot_description` unchanged as a reference package.
- Connect to the Ubuntu VM as `jay@192.168.72.200` with `C:\Users\LENOVO\.ssh\codex_ubuntu_vm`; the VM workspace is `/home/jay/moveit_ws`.
- Preserve the arm planning chain `base_link` to `tool_link` and the arm joint order `joint1` through `joint6`.
- Use `gripper_finger_left_joint` as the commanded joint with range `0.000` to `0.034 m`.
- Use `gripper_finger_right_joint` as a mimic joint with multiplier `-1.0`.
- Use exactly `gripper_open = 0.034`, `gripper_half_open = 0.017`, and `gripper_close = 0.000 m`; do not add `gripper_half_opne`.
- Keep the arm and gripper in separate MoveIt groups and separate controllers.
- Preserve the visual-only `tool_link` sphere and keep it free of collision geometry.
- Do not add Gazebo, physics grasping, object attachment, real hardware, or effort-control scope.
- Follow test-driven development: observe each new contract test fail before changing its production configuration.

## File Structure

- `src/my_robot_description/urdf/arm.xacro`: owns the complete learning robot geometry and joint tree, including the gripper and grasp frame.
- `src/my_robot_moveit_config/config/my_robot.srdf`: owns planning groups, named states, end-effector association, and self-collision exclusions.
- `src/my_robot_moveit_config/config/joint_limits.yaml`: owns MoveIt limit overrides for the commanded gripper joint.
- `src/my_robot_moveit_config/config/initial_positions.yaml`: owns fake-hardware startup positions.
- `src/my_robot_moveit_config/config/my_robot.ros2_control.xacro`: exports the commanded gripper joint to the existing fake ros2_control system.
- `src/my_robot_moveit_config/config/ros2_controllers.yaml`: loads and configures the independent gripper action controller.
- `src/my_robot_moveit_config/config/moveit_controllers.yaml`: maps MoveIt execution to the gripper action.
- `src/my_robot_moveit_config/package.xml`: declares the direct `gripper_controllers` runtime dependency.
- `src/my_robot_moveit_config/test/test_moveit_config.py`: statically enforces the robot, MoveIt, controller, and launch contracts.

---

### Task 1: Gripper URDF and grasp frame

**Files:**
- Modify: `src/my_robot_moveit_config/test/test_moveit_config.py:17-206`
- Modify: `src/my_robot_description/urdf/arm.xacro:155-199`

**Interfaces:**
- Consumes: the existing `hand_link`, `joint6`, blue material, and visual-only `tool_link` marker.
- Produces: links `gripper_base`, `gripper_finger_left`, `gripper_finger_right`; joints `gripper_base_joint`, `gripper_finger_left_joint`, `gripper_finger_right_joint`; fixed `tool_joint` from `gripper_base` to `tool_link`.

- [ ] **Step 1: Write the failing robot-model contract**

Rename the arm-only constant and add explicit gripper constants:

```python
EXPECTED_ARM_JOINTS = [
    "joint1",
    "joint2",
    "joint3",
    "joint4",
    "joint5",
    "joint6",
]
GRIPPER_COMMAND_JOINT = "gripper_finger_left_joint"
GRIPPER_MIMIC_JOINT = "gripper_finger_right_joint"
EXPECTED_ACTIVE_JOINTS = EXPECTED_ARM_JOINTS + [
    GRIPPER_COMMAND_JOINT,
    GRIPPER_MIMIC_JOINT,
]
```

Add `gripper_base`, `gripper_finger_left`, and `gripper_finger_right` to
`EXPECTED_LINKS`. Add this geometry to `EXPECTED_LINK_GEOMETRY`:

```python
"gripper_base": ("box", {"size": "0.12 0.08 0.04"}, "0 0 0.02"),
"gripper_finger_left": (
    "box",
    {"size": "0.02 0.04 0.12"},
    "0 0 0.06",
),
"gripper_finger_right": (
    "box",
    {"size": "0.02 0.04 0.12"},
    "0 0 0.06",
),
```

Replace the old `tool_joint` layout and add the new joints:

```python
"gripper_base_joint": (
    "hand_link",
    "gripper_base",
    "fixed",
    "0 0 0.02",
    None,
),
"gripper_finger_left_joint": (
    "gripper_base",
    "gripper_finger_left",
    "prismatic",
    "0.01 0 0.04",
    "1 0 0",
),
"gripper_finger_right_joint": (
    "gripper_base",
    "gripper_finger_right",
    "prismatic",
    "-0.01 0 0.04",
    "1 0 0",
),
"tool_joint": (
    "gripper_base",
    "tool_link",
    "fixed",
    "0 0 0.10",
    None,
),
```

Update `test_learning_urdf_has_expected_arm_chain` to compare the non-fixed
joints with `EXPECTED_ACTIVE_JOINTS`. Add:

```python
def test_gripper_joint_limits_and_mimic_contract(self):
    left = self.urdf_joints[GRIPPER_COMMAND_JOINT]
    left_limit = left.find("limit")
    self.assertEqual("0", left_limit.attrib["lower"])
    self.assertEqual("0.034", left_limit.attrib["upper"])
    self.assertEqual("20", left_limit.attrib["effort"])
    self.assertEqual("0.1", left_limit.attrib["velocity"])

    right = self.urdf_joints[GRIPPER_MIMIC_JOINT]
    right_limit = right.find("limit")
    self.assertEqual("-0.034", right_limit.attrib["lower"])
    self.assertEqual("0", right_limit.attrib["upper"])
    mimic = right.find("mimic")
    self.assertEqual(GRIPPER_COMMAND_JOINT, mimic.attrib["joint"])
    self.assertEqual("-1.0", mimic.attrib["multiplier"])
```

Replace later arm-only uses of `EXPECTED_JOINTS` with
`EXPECTED_ARM_JOINTS`; later tasks will explicitly add the commanded gripper
joint where required.

- [ ] **Step 2: Run the robot-model tests and verify the new contract fails**

Run from `moveit_ws`:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k "learning_urdf or gripper_joint or tool_link" -v
```

Expected: FAIL because the three gripper links and joints do not exist and
`tool_joint` still connects directly to `hand_link`.

- [ ] **Step 3: Add the minimal gripper model**

In `arm.xacro`, replace the old `tool_joint` block and insert these links and
joints before `tool_link`:

```xml
  <link name="gripper_base">
    <visual>
      <origin xyz="0 0 0.02" rpy="0 0 0"/>
      <geometry><box size="0.12 0.08 0.04"/></geometry>
      <material name="blue"/>
    </visual>
    <collision>
      <origin xyz="0 0 0.02" rpy="0 0 0"/>
      <geometry><box size="0.12 0.08 0.04"/></geometry>
    </collision>
  </link>

  <joint name="gripper_base_joint" type="fixed">
    <parent link="hand_link"/>
    <child link="gripper_base"/>
    <origin xyz="0 0 0.02" rpy="0 0 0"/>
  </joint>

  <link name="gripper_finger_left">
    <visual>
      <origin xyz="0 0 0.06" rpy="0 0 0"/>
      <geometry><box size="0.02 0.04 0.12"/></geometry>
      <material name="blue"/>
    </visual>
    <collision>
      <origin xyz="0 0 0.06" rpy="0 0 0"/>
      <geometry><box size="0.02 0.04 0.12"/></geometry>
    </collision>
  </link>

  <joint name="gripper_finger_left_joint" type="prismatic">
    <parent link="gripper_base"/>
    <child link="gripper_finger_left"/>
    <origin xyz="0.01 0 0.04" rpy="0 0 0"/>
    <axis xyz="1 0 0"/>
    <limit lower="0" upper="0.034" effort="20" velocity="0.1"/>
  </joint>

  <link name="gripper_finger_right">
    <visual>
      <origin xyz="0 0 0.06" rpy="0 0 0"/>
      <geometry><box size="0.02 0.04 0.12"/></geometry>
      <material name="blue"/>
    </visual>
    <collision>
      <origin xyz="0 0 0.06" rpy="0 0 0"/>
      <geometry><box size="0.02 0.04 0.12"/></geometry>
    </collision>
  </link>

  <joint name="gripper_finger_right_joint" type="prismatic">
    <parent link="gripper_base"/>
    <child link="gripper_finger_right"/>
    <origin xyz="-0.01 0 0.04" rpy="0 0 0"/>
    <axis xyz="1 0 0"/>
    <mimic joint="gripper_finger_left_joint" multiplier="-1.0"/>
    <limit lower="-0.034" upper="0" effort="20" velocity="0.1"/>
  </joint>
```

Retain the existing `tool_link` visual and define its joint as:

```xml
  <joint name="tool_joint" type="fixed">
    <parent link="gripper_base"/>
    <child link="tool_link"/>
    <origin xyz="0 0 0.10" rpy="0 0 0"/>
  </joint>
```

- [ ] **Step 4: Run the robot-model tests and verify they pass**

Run:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k "learning_urdf or gripper_joint or tool_link" -v
```

Expected: all selected tests PASS.

- [ ] **Step 5: Commit the robot model**

```powershell
git add src/my_robot_description/urdf/arm.xacro src/my_robot_moveit_config/test/test_moveit_config.py
git commit -m "feat: attach gripper to learning arm"
```

---

### Task 2: MoveIt gripper group and named states

**Files:**
- Modify: `src/my_robot_moveit_config/test/test_moveit_config.py:241-297,367-390`
- Modify: `src/my_robot_moveit_config/config/my_robot.srdf:3-61`
- Modify: `src/my_robot_moveit_config/config/joint_limits.yaml:5-35`

**Interfaces:**
- Consumes: `gripper_base`, `gripper_finger_left_joint`, and `gripper_finger_right_joint` from Task 1.
- Produces: MoveIt group `gripper`, end effector `gripper_end_effector`, and exact named states `gripper_open`, `gripper_half_open`, `gripper_close`.

- [ ] **Step 1: Write the failing MoveIt semantic contract**

Add:

```python
EXPECTED_GRIPPER_STATES = {
    "gripper_open": 0.034,
    "gripper_half_open": 0.017,
    "gripper_close": 0.0,
}
```

Extend the SRDF test with:

```python
gripper_group = next(
    group
    for group in srdf_root.findall("group")
    if group.attrib["name"] == "gripper"
)
self.assertEqual(
    [GRIPPER_COMMAND_JOINT, GRIPPER_MIMIC_JOINT],
    [joint.attrib["name"] for joint in gripper_group.findall("joint")],
)

gripper_states = {
    state.attrib["name"]: float(state.find("joint").attrib["value"])
    for state in srdf_root.findall("group_state")
    if state.attrib["group"] == "gripper"
}
self.assertEqual(EXPECTED_GRIPPER_STATES, gripper_states)
self.assertNotIn("gripper_half_opne", gripper_states)

end_effector = srdf_root.find("end_effector")
self.assertEqual("gripper_end_effector", end_effector.attrib["name"])
self.assertEqual("gripper_base", end_effector.attrib["parent_link"])
self.assertEqual("gripper", end_effector.attrib["group"])
self.assertEqual("arm", end_effector.attrib["parent_group"])
```

Require these collision exclusions:

```python
disabled_links = {
    frozenset((pair.attrib["link1"], pair.attrib["link2"]))
    for pair in disabled_pairs
}
for pair in {
    frozenset(("hand_link", "gripper_base")),
    frozenset(("gripper_base", "gripper_finger_left")),
    frozenset(("gripper_base", "gripper_finger_right")),
    frozenset(("gripper_finger_left", "gripper_finger_right")),
}:
    self.assertIn(pair, disabled_links)
```

Change the joint-limit assertion to expect
`set(EXPECTED_ARM_JOINTS + [GRIPPER_COMMAND_JOINT])`, and add:

```python
gripper_limit = limits["joint_limits"][GRIPPER_COMMAND_JOINT]
self.assertTrue(gripper_limit["has_position_limits"])
self.assertEqual(0.0, float(gripper_limit["min_position"]))
self.assertEqual(0.034, float(gripper_limit["max_position"]))
self.assertEqual(0.1, float(gripper_limit["max_velocity"]))
```

- [ ] **Step 2: Run the semantic tests and verify they fail**

Run:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k "srdf or joint_limits" -v
```

Expected: FAIL because the gripper group, named states, end-effector entry,
collision exclusions, and gripper limit override are absent.

- [ ] **Step 3: Add the MoveIt group, states, and end-effector entry**

Add to `my_robot.srdf` after the arm group:

```xml
  <group name="gripper">
    <joint name="gripper_finger_left_joint"/>
    <joint name="gripper_finger_right_joint"/>
  </group>

  <group_state name="gripper_open" group="gripper">
    <joint name="gripper_finger_left_joint" value="0.034"/>
  </group_state>
  <group_state name="gripper_half_open" group="gripper">
    <joint name="gripper_finger_left_joint" value="0.017"/>
  </group_state>
  <group_state name="gripper_close" group="gripper">
    <joint name="gripper_finger_left_joint" value="0.0"/>
  </group_state>

  <end_effector
    name="gripper_end_effector"
    parent_link="gripper_base"
    group="gripper"
    parent_group="arm"/>
```

Append these exclusions before `</robot>`:

```xml
  <disable_collisions link1="gripper_base" link2="hand_link" reason="Adjacent"/>
  <disable_collisions link1="gripper_base" link2="gripper_finger_left" reason="Adjacent"/>
  <disable_collisions link1="gripper_base" link2="gripper_finger_right" reason="Adjacent"/>
  <disable_collisions link1="gripper_finger_left" link2="gripper_finger_right" reason="Never"/>
```

- [ ] **Step 4: Add the MoveIt joint-limit override**

Append under `joint_limits`:

```yaml
  gripper_finger_left_joint:
    has_position_limits: true
    min_position: 0.0
    max_position: 0.034
    has_velocity_limits: true
    max_velocity: 0.1
    has_acceleration_limits: true
    max_acceleration: 0.1
```

- [ ] **Step 5: Run the semantic tests and verify they pass**

Run:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k "srdf or joint_limits" -v
```

Expected: all selected tests PASS.

- [ ] **Step 6: Commit the semantic configuration**

```powershell
git add src/my_robot_moveit_config/config/my_robot.srdf src/my_robot_moveit_config/config/joint_limits.yaml src/my_robot_moveit_config/test/test_moveit_config.py
git commit -m "feat: add MoveIt gripper states"
```

---

### Task 3: ros2_control and MoveIt execution mapping

**Files:**
- Modify: `src/my_robot_moveit_config/test/test_moveit_config.py:298-410`
- Modify: `src/my_robot_moveit_config/config/initial_positions.yaml:2-8`
- Modify: `src/my_robot_moveit_config/config/my_robot.ros2_control.xacro:13-55`
- Modify: `src/my_robot_moveit_config/config/ros2_controllers.yaml:2-26`
- Modify: `src/my_robot_moveit_config/config/moveit_controllers.yaml:4-18`
- Modify: `src/my_robot_moveit_config/package.xml:16-32`

**Interfaces:**
- Consumes: MoveIt group `gripper` and independent joint `gripper_finger_left_joint`.
- Produces: action `/gripper_controller/gripper_cmd` using `control_msgs/action/GripperCommand`; fake hardware position and velocity state for the commanded joint.

- [ ] **Step 1: Write the failing controller contract**

Update `test_controller_joint_order_and_interfaces_match` to require:

```python
self.assertEqual(
    ["arm_controller", "gripper_controller"],
    moveit_manager["controller_names"],
)
self.assertEqual(EXPECTED_ARM_JOINTS, moveit_manager["arm_controller"]["joints"])
gripper_moveit = moveit_manager["gripper_controller"]
self.assertEqual("GripperCommand", gripper_moveit["type"])
self.assertEqual("gripper_cmd", gripper_moveit["action_ns"])
self.assertTrue(gripper_moveit["default"])
self.assertEqual([GRIPPER_COMMAND_JOINT], gripper_moveit["joints"])
```

Add the ROS 2 controller assertions:

```python
manager = ros2["controller_manager"]["ros__parameters"]
self.assertEqual(
    "position_controllers/GripperActionController",
    manager["gripper_controller"]["type"],
)
gripper_ros2 = ros2["gripper_controller"]["ros__parameters"]
self.assertEqual(GRIPPER_COMMAND_JOINT, gripper_ros2["joint"])
self.assertEqual(0.002, float(gripper_ros2["goal_tolerance"]))
self.assertEqual(20.0, float(gripper_ros2["max_effort"]))
```

Change the fake-hardware expected joint order to:

```python
EXPECTED_ARM_JOINTS + [GRIPPER_COMMAND_JOINT]
```

Change the initial-position expectation to:

```python
{
    **{joint: 0 for joint in EXPECTED_ARM_JOINTS},
    GRIPPER_COMMAND_JOINT: 0,
}
```

Extend the package dependency test:

```python
self.assertIn("gripper_controllers", runtime_dependencies)
```

- [ ] **Step 2: Run the execution-contract tests and verify they fail**

Run:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k "controller or fake_hardware or initial_positions or package_select" -v
```

Expected: FAIL because the gripper has no fake-hardware interface, controller,
MoveIt action mapping, initial position, or package dependency.

- [ ] **Step 3: Export the commanded gripper joint from fake hardware**

Add to `initial_positions.yaml`:

```yaml
  gripper_finger_left_joint: 0
```

Add before `</ros2_control>` in `my_robot.ros2_control.xacro`:

```xml
      <joint name="gripper_finger_left_joint">
        <command_interface name="position"/>
        <state_interface name="position">
          <param name="initial_value">${initial_positions['gripper_finger_left_joint']}</param>
        </state_interface>
        <state_interface name="velocity"/>
      </joint>
```

Do not export `gripper_finger_right_joint`; robot state publisher and MoveIt
derive it from the URDF mimic relationship.

- [ ] **Step 4: Configure the ROS 2 gripper action controller**

Add under `controller_manager.ros__parameters` in `ros2_controllers.yaml`:

```yaml
    gripper_controller:
      type: position_controllers/GripperActionController
```

Add the controller parameters:

```yaml
gripper_controller:
  ros__parameters:
    joint: gripper_finger_left_joint
    action_monitor_rate: 20.0
    goal_tolerance: 0.002
    max_effort: 20.0
    allow_stalling: false
    stall_velocity_threshold: 0.001
    stall_timeout: 1.0
```

- [ ] **Step 5: Map MoveIt to the gripper action**

Add `gripper_controller` to `controller_names` and append:

```yaml
  gripper_controller:
    type: GripperCommand
    action_ns: gripper_cmd
    default: true
    joints:
      - gripper_finger_left_joint
```

The standard `generate_spawn_controllers_launch` helper reads this controller
list, so `spawn_controllers.launch.py` needs no custom controller names.

- [ ] **Step 6: Declare the runtime dependency**

Add to `package.xml` beside the other controller dependencies:

```xml
  <exec_depend>gripper_controllers</exec_depend>
```

- [ ] **Step 7: Run the execution-contract tests and verify they pass**

Run:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -k "controller or fake_hardware or initial_positions or package_select" -v
```

Expected: all selected tests PASS.

- [ ] **Step 8: Run the complete local static suite**

Run:

```powershell
python -m pytest src/my_robot_moveit_config/test/test_moveit_config.py -v
```

Expected: all tests PASS with no duplicate YAML keys or mature-model joint
names in the learning MoveIt package.

- [ ] **Step 9: Commit the control configuration**

```powershell
git add src/my_robot_moveit_config/config/initial_positions.yaml src/my_robot_moveit_config/config/my_robot.ros2_control.xacro src/my_robot_moveit_config/config/ros2_controllers.yaml src/my_robot_moveit_config/config/moveit_controllers.yaml src/my_robot_moveit_config/package.xml src/my_robot_moveit_config/test/test_moveit_config.py
git commit -m "feat: execute learning gripper states"
```

---

### Task 4: Ubuntu VM build and runtime acceptance

**Files:**
- Verify: `src/my_robot_description/urdf/arm.xacro`
- Verify: `src/my_robot_moveit_config/config/*`
- Verify: `src/my_robot_moveit_config/launch/demo.launch.py`
- Verify: `src/my_robot_moveit_config/test/test_moveit_config.py`

**Interfaces:**
- Consumes: the committed feature branch produced by Tasks 1-3.
- Produces: a verified ROS 2 Jazzy build, active controllers, successful open/half-open/close goals, and synchronized `main`.

- [ ] **Step 1: Publish the feature branch for VM validation**

From the implementation worktree:

```powershell
git status --short
git push -u origin feat/learning-arm-gripper
```

Expected: the worktree is clean and the remote feature branch points to the
Task 3 commit.

- [ ] **Step 2: Check out the exact feature commit on the VM**

Run from Windows:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && git fetch origin && git switch -C feat/learning-arm-gripper origin/feat/learning-arm-gripper && git status --short && git rev-parse HEAD"
```

Expected: clean status and the same commit hash as the local feature branch.

- [ ] **Step 3: Expand and validate the URDF**

Run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && source /opt/ros/jazzy/setup.bash && xacro src/my_robot_moveit_config/config/my_robot.urdf.xacro initial_positions_file:=src/my_robot_moveit_config/config/initial_positions.yaml > /tmp/my_robot_gripper.urdf && check_urdf /tmp/my_robot_gripper.urdf"
```

Expected: `robot name is: my_robot`, a valid tree rooted at `base_link`, and
no XML, mimic-joint, or disconnected-tree error.

- [ ] **Step 4: Build and test both packages on ROS 2 Jazzy**

Run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install --packages-select my_robot_description my_robot_moveit_config && source install/setup.bash && colcon test --packages-select my_robot_moveit_config --event-handlers console_direct+ && colcon test-result --verbose"
```

Expected: both packages build; `my_robot_moveit_config` tests pass with zero
failures.

- [ ] **Step 5: Start the complete MoveIt demo**

Run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 'cd /home/jay/moveit_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && DISPLAY=:0 nohup ros2 launch my_robot_moveit_config demo.launch.py > /tmp/my_robot_gripper_demo.log 2>&1 & echo $! > /tmp/my_robot_gripper_demo.pid && cat /tmp/my_robot_gripper_demo.pid'
```

Expected: a numeric launch PID is returned.

- [ ] **Step 6: Verify all controllers are active**

Run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "source /opt/ros/jazzy/setup.bash && source /home/jay/moveit_ws/install/setup.bash && ros2 control list_controllers"
```

Expected output contains:

```text
arm_controller
gripper_controller
joint_state_broadcaster
```

Each controller must report `active`. If activation is not complete on the
first query, poll the same read-only command for up to 30 seconds before
inspecting `/tmp/my_robot_gripper_demo.log`.

- [ ] **Step 7: Execute the fully open goal**

Run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "source /opt/ros/jazzy/setup.bash && source /home/jay/moveit_ws/install/setup.bash && ros2 action send_goal /gripper_controller/gripper_cmd control_msgs/action/GripperCommand '{command: {position: 0.034, max_effort: 20.0}}' && ros2 topic echo /joint_states --once"
```

Expected: the action succeeds and `gripper_finger_left_joint` reports
`0.034 m` within `0.002 m`.

- [ ] **Step 8: Execute the half-open goal**

Run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "source /opt/ros/jazzy/setup.bash && source /home/jay/moveit_ws/install/setup.bash && ros2 action send_goal /gripper_controller/gripper_cmd control_msgs/action/GripperCommand '{command: {position: 0.017, max_effort: 20.0}}' && ros2 topic echo /joint_states --once"
```

Expected: the action succeeds and `gripper_finger_left_joint` reports
`0.017 m` within `0.002 m`.

- [ ] **Step 9: Execute the closed goal**

Run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "source /opt/ros/jazzy/setup.bash && source /home/jay/moveit_ws/install/setup.bash && ros2 action send_goal /gripper_controller/gripper_cmd control_msgs/action/GripperCommand '{command: {position: 0.000, max_effort: 20.0}}' && ros2 topic echo /joint_states --once"
```

Expected: the action succeeds and `gripper_finger_left_joint` reports
`0.000 m` within `0.002 m`.

- [ ] **Step 10: Stop only the demo process started in Step 5**

Run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 'if test -f /tmp/my_robot_gripper_demo.pid; then kill $(cat /tmp/my_robot_gripper_demo.pid); fi'
```

Expected: the recorded launch process exits; no unrelated process is
targeted.

- [ ] **Step 11: Complete branch integration**

Invoke `superpowers:finishing-a-development-branch`. Choose the merge-to-main
path, rerun the complete local static test, push `origin/main`, and then run:

```powershell
ssh -i C:\Users\LENOVO\.ssh\codex_ubuntu_vm jay@192.168.72.200 "cd /home/jay/moveit_ws && git switch main && git pull --ff-only origin main && git status --short && git rev-parse HEAD"
git rev-parse main
git rev-parse origin/main
```

Expected: the VM is clean and all three hashes are identical.
