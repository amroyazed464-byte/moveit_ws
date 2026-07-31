# Learning Arm Gripper Design

## Goal

Add an executable two-finger gripper to the learning robot in
`my_robot_description`, connect it rigidly to the existing arm, and expose
three selectable MoveIt named states:

- `gripper_open`
- `gripper_half_open`
- `gripper_close`

The result must run in the existing ROS 2 Jazzy and MoveIt 2 demonstration on
the Ubuntu virtual machine. The existing mature model in `robot_description`
remains an unchanged reference package.

## Selected Approach

Use a separate MoveIt planning group and a separate ROS 2 gripper controller.
The arm keeps its existing six-joint trajectory controller. A single actuated
prismatic joint drives one finger, while the second finger mirrors it through a
URDF mimic relationship.

This keeps arm motion and gripping independent, matches the control boundary
used by a typical physical gripper, and permits the three gripper states to be
planned and executed directly from RViz.

## Robot Structure

Extend `my_robot_description/urdf/arm.xacro` with these components:

- `gripper_base`, rigidly attached to `hand_link`
- `gripper_finger_left`
- `gripper_finger_right`
- `gripper_finger_left_joint`, the commanded prismatic joint
- `gripper_finger_right_joint`, which mimics the left joint with a multiplier
  of `-1.0`

Both fingers translate symmetrically along the local X axis. The commanded
joint range is `0.000` to `0.034 m`, where zero is closed and the upper limit
is fully open. The right joint uses the corresponding mirrored range.

Use simple primitive geometry consistent with the learning arm:

- base: `0.12 x 0.08 x 0.04 m`
- each finger: `0.02 x 0.04 x 0.12 m`

At the closed position, the inner faces of the fingers meet on the gripper
centerline. At the open position, each finger moves `0.034 m` away from that
centerline. Visual and collision geometry must use the same dimensions and
origins.

Replace the current direct `hand_link` to `tool_link` attachment with
`gripper_base_joint`, a fixed joint from `hand_link` to `gripper_base`.
Retain `tool_joint`, but make it a fixed joint from `gripper_base` to
`tool_link`. Place `tool_link` on the gripper centerline, halfway along the
gripping region. Its existing small visual-only marker remains available for
the RViz trail and continues to have no collision geometry. The arm planning
chain remains `base_link` to `tool_link`.

## MoveIt Semantics

Keep the existing `arm` planning group unchanged in purpose and add a
`gripper` planning group for the finger joints. Register the gripper as the
end effector associated with the arm and its fixed mounting link.

Add these `gripper` group states to the SRDF:

| State | Commanded joint position |
| --- | ---: |
| `gripper_open` | `0.034 m` |
| `gripper_half_open` | `0.017 m` |
| `gripper_close` | `0.000 m` |

Only the left, commanded joint supplies an independent state variable. The
right finger position is derived from its mimic relationship. The spelling
`gripper_half_open` is canonical; the misspelled `gripper_half_opne` alias is
not added.

Update the self-collision configuration for the new links. Disable collisions
that are structurally unavoidable or adjacent, including parent-child pairs
and the opposing fingers at their closed boundary, while preserving collision
checking between the fingers and external objects.

## Control Architecture

Extend the existing `mock_components/GenericSystem` ros2_control system with a
position command interface and position/velocity state interfaces for
`gripper_finger_left_joint`. Initialize it to `0.0`.

Keep these existing controllers:

- `arm_controller`
- `joint_state_broadcaster`

Add `gripper_controller` using the ROS 2 position gripper action controller.
It controls only `gripper_finger_left_joint` and exposes a gripper command
action. Configure `MoveItSimpleControllerManager` with a `GripperCommand`
entry that maps the MoveIt `gripper` group to that action.

The MoveIt demonstration launch must spawn all three controllers. Arm
trajectories continue through `arm_controller`; gripper targets travel through
`gripper_controller`. Joint states from the mock hardware drive the left
finger, and the URDF mimic relationship drives the right finger in the robot
model and RViz.

## User Flow

In the Motion Planning panel:

1. Select the `gripper` planning group.
2. Select `gripper_open`, `gripper_half_open`, or `gripper_close`.
3. Plan and execute.

MoveIt resolves the named state to the commanded joint value, sends it to the
gripper action controller, and displays the resulting symmetric motion from
the returned joint state. Selecting the `arm` group continues to operate the
six arm joints independently.

## Limits and Failure Handling

- URDF joint limits are the primary source of the `0.000` to `0.034 m`
  permitted range.
- MoveIt joint limits must agree with the URDF and must not widen the range.
- The controller rejects goals outside its permitted range or tolerance.
- A gripper controller failure must not change the arm controller
  configuration or joint order.
- The demo launch must fail visibly if the gripper controller cannot be
  loaded or activated rather than silently omitting it.

## Files in Scope

Expected implementation changes are limited to:

- `src/my_robot_description/urdf/arm.xacro`
- MoveIt SRDF, ros2_control, joint-limit, and controller configuration under
  `src/my_robot_moveit_config/config`
- controller spawning configuration or launch code where required
- `src/my_robot_moveit_config/test/test_moveit_config.py`

Package metadata is changed only if the gripper controller introduces a direct
dependency not already declared.

## Validation

Static tests must prove:

- all XML/Xacro, YAML, and launch Python files parse
- the gripper base is connected to `hand_link`
- `tool_link` is fixed to the gripper at the grasp center
- the left joint has the required prismatic range
- the right joint correctly mimics the left joint
- all three named states exist with the exact names and values above
- MoveIt, ros2_control, and controller joint names agree
- the six-joint arm controller order remains unchanged
- the gripper controller is separate and controls only the commanded finger
- the demo launch spawns the gripper controller

Runtime validation on the Ubuntu VM must run:

- Xacro expansion
- `check_urdf`
- `colcon build`
- the package test suite
- the MoveIt demo launch
- controller-manager inspection proving all three controllers are active
- open, half-open, and close action goals, with observed joint positions of
  `0.034`, `0.017`, and `0.000 m` within controller tolerance

## Delivery

Implement the feature on an isolated branch when appropriate, merge the
verified change into `main`, push `origin/main`, and confirm that the local
workspace, Ubuntu VM workspace, and remote `main` resolve to the same commit.

## Out of Scope

- modifying the reference `robot_description` package
- Gazebo or physics-based grasping
- object attachment or pick-and-place task logic
- real gripper hardware drivers
- force or effort control
