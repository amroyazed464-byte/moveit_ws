# Learning Robot MoveIt Configuration Design

## Goal

Replace the existing `my_robot_moveit_config` package with a ROS 2 Jazzy and
MoveIt 2 configuration for the learning model in
`my_robot_description/urdf/arm.xacro`, while keeping `robot_description`
unchanged as a reference package.

## Package Strategy

- Keep the package name `my_robot_moveit_config` so existing build and launch
  commands remain stable.
- Remove configuration inherited from the mature `robot_description` model.
- Make `my_robot_description` the only description dependency of the new
  MoveIt package.
- Keep `robot_description` installed in the workspace, but do not reference it
  from the new MoveIt package.

This provides one MoveIt configuration package and avoids duplicate package
names, launch files, controllers, and ROS parameters.

## Robot Model and Semantics

- Robot name: `my_robot`
- Planning group: `arm`
- Planning chain: `base_link` to `tool_link`
- Active joints, in trajectory order:
  `joint1`, `joint2`, `joint3`, `joint4`, `joint5`, `joint6`
- Virtual joint: fixed `world` to `base_link`
- Named states:
  - `home`: all six joints at `0.0`
- `pose_1`: `[1.1705, 1.1686, 0.9172, 1.2449, 0.9940, 1.0596]`
- `pose_2`: `[1.5421, 1.57, 0.5030, 0.2787, 1.3285, 1.7659]`

The screenshot value `pose_2/joint2 = 1.5828` is clamped to the current URDF
upper limit `1.57`; the learning URDF is not changed.

## Motion Planning

- Use `kdl_kinematics_plugin/KDLKinematicsPlugin`.
- Use a 0.05 second IK timeout.
- Load the standard planning pipelines supplied by
  `moveit_configs_utils`, with OMPL selected by default.
- Preserve conservative default motion scaling:
  - velocity scaling: `0.1`
  - acceleration scaling: `0.1`
- Override acceleration limits to `1.0 rad/s^2` for all six joints while
  preserving URDF position and velocity limits.

## Fake Execution

- Add exactly one `ros2_control` system to the MoveIt wrapper Xacro.
- Use `mock_components/GenericSystem`.
- Expose position command interfaces and position/velocity state interfaces
  for all six joints.
- Start all joints at the `home` position.
- Configure:
  - `arm_controller` as
    `joint_trajectory_controller/JointTrajectoryController`
  - `joint_state_broadcaster` as
    `joint_state_broadcaster/JointStateBroadcaster`
- Use `arm_controller/follow_joint_trajectory` through
  `MoveItSimpleControllerManager`.
- Require zero velocity at the final trajectory point.

## Launching

Generate the standard MoveIt 2 Jazzy launch entry points:

- `demo.launch.py`
- `move_group.launch.py`
- `moveit_rviz.launch.py`
- `rsp.launch.py`
- `spawn_controllers.launch.py`
- `static_virtual_joint_tfs.launch.py`
- `setup_assistant.launch.py`
- `warehouse_db.launch.py`

`demo.launch.py` is the primary acceptance path and must start the robot state
publisher, fixed world transform, Move Group, RViz, controller manager,
`arm_controller`, and `joint_state_broadcaster`.

## Package Metadata

- Declare direct runtime dependencies for MoveIt, RViz, Xacro,
  `my_robot_description`, ros2_control, the joint trajectory controller, and
  the joint state broadcaster.
- Install all configuration and launch resources.
- Store Setup Assistant metadata without duplicate YAML keys.

## Validation

Static validation must prove:

- All XML/Xacro, YAML, and launch Python files parse.
- SRDF link and joint references exist in `arm.xacro`.
- Named states stay within URDF limits.
- The six-joint order is identical in MoveIt and ros2_control controllers.
- Exactly one `ros2_control` system exports the six position command
  interfaces.
- The MoveIt package depends on `my_robot_description` and not
  `robot_description`.
- The old mature-model joint names do not remain in the replacement package.

When a sourced ROS 2 Jazzy environment is available, runtime validation must
also run Xacro expansion, `check_urdf`, `colcon build`, and the demo launch.

## Out of Scope

- Modifying or deleting `robot_description`
- Adding inertial properties to the learning URDF
- Real hardware drivers
- Gazebo or other physics simulation
- Gripper configuration
