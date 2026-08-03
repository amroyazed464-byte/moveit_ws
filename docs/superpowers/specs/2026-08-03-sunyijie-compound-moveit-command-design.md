# Sunyijie Compound MoveIt Command Design

## Goal

Restore the complete chapter-7 C++ MoveIt commander behavior used by the
course project, then extend its custom pose message so one `/pose_command`
message controls both the six-axis arm and the gripper.

The personal field name is exactly `sunyijie_gripper` in the message
definition, generated C++ access, source variables, documentation, tests, and
terminal commands. Its fixed meaning is:

- `true`: close the gripper
- `false`: open the gripper

The completed ROS 2 Jazzy workspace must build and run on the configured
Ubuntu virtual machine and support a recorded pick-and-place demonstration in
RViz.

## Confirmed Course Baseline

The target material is section 7, Activity 05 solution part 2, from Edouard
Renard's *ROS 2 MoveIt 2 - Control a Robotic Arm*. The complete Bilibili mirror
places the target lecture at part 41:

- <https://www.bilibili.com/video/BV1cFsuzrErZ/?p=41>
- <https://www.udemy.com/course/ros2-moveit2/>

The original `PoseCommand` contract is:

```text
float64 x
float64 y
float64 z
float64 roll
float64 pitch
float64 yaw
bool cartesian_path
```

The chapter-7 C++ baseline includes separate MoveIt interfaces for the `arm`
and `gripper` planning groups, named targets, joint targets, pose targets,
roll/pitch/yaw conversion, Cartesian paths, an object-oriented commander, and
topic subscribers for gripper, joint, and pose commands.

The public course material does not expose an authoritative source archive,
so the implementation will restore the confirmed behavior and interfaces
rather than claim byte-for-byte identity with a private download.

## Selected Architecture

Use one C++ coordinator process with one ROS node and two independent
`moveit::planning_interface::MoveGroupInterface` objects:

- the C++ class is `MyRobotCommander`
- the installed executable and ROS node name are both `my_robot_commander`
- `arm_move_group` controls the existing MoveIt `arm` group.
- `gripper_move_group` controls the existing MoveIt `gripper` group.
- `/gripper_command` uses `std_msgs/msg/Bool` and preserves the chapter's
  independent Boolean gripper command.
- `/joint_command` uses `std_msgs/msg/Float64MultiArray` and preserves the
  chapter's six-value arm joint command.
- `/pose_command` accepts the custom pose interface and performs the new
  compound arm-plus-gripper operation.

All three subscriptions use a reliable keep-last depth of 10.

This preserves the existing separate arm and gripper controllers. It avoids a
new combined SRDF planning group and avoids extra internal topics whose
acknowledgement and ordering would complicate the classroom demonstration.
The CLI publisher, commander, MoveIt `move_group`, controller manager, arm
controller, and gripper controller still form the required multi-node ROS 2
communication path.

## Packages and Files

Add `my_moveit_interfaces` as an `ament_cmake` interface package:

- `src/my_moveit_interfaces/msg/PoseCommand.msg`
- `src/my_moveit_interfaces/CMakeLists.txt`
- `src/my_moveit_interfaces/package.xml`

Add `my_robot_commander` as an `ament_cmake` C++ package:

- `src/my_robot_commander/include/my_robot_commander/commander.hpp`
- `src/my_robot_commander/include/my_robot_commander/command_utils.hpp`
- `src/my_robot_commander/src/commander.cpp`
- `src/my_robot_commander/src/command_utils.cpp`
- `src/my_robot_commander/src/main.cpp`
- `src/my_robot_commander/test/test_command_utils.cpp`
- `src/my_robot_commander/CMakeLists.txt`
- `src/my_robot_commander/package.xml`
- `src/my_robot_commander/README.md`

Integrate the executable into the existing demo:

- update `src/my_robot_moveit_config/launch/demo.launch.py`
- update `src/my_robot_moveit_config/package.xml`
- extend `src/my_robot_moveit_config/test/test_moveit_config.py`

The mature reference package `robot_description` remains unchanged.

## Message Contract

`PoseCommand.msg` will contain exactly these fields and order:

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

All position values are metres. Roll, pitch, and yaw are radians. The pose is
expressed in the arm MoveIt planning frame, which is the existing fixed world
and `base_link` setup used by the demo.

## Commander Behavior

The C++ class will expose focused methods for:

- plan and execute a target for any MoveGroupInterface
- move a group to a named target
- move the arm to six joint values
- move the arm to a position and RPY orientation
- compute and execute a Cartesian path to a pose
- map `sunyijie_gripper` to the exact existing named targets
  `gripper_close` and `gripper_open`

RPY values are converted to a normalized quaternion using TF2.

For a normal pose command (`cartesian_path: false`), the node sets the current
state as the start state, sets the pose target, plans, and executes only a
successful plan.

For a Cartesian command (`cartesian_path: true`), the node builds one waypoint
from the requested pose and calls `computeCartesianPath` with an end-effector
step of `0.01 m` and jump threshold `0.0`. It executes only when the computed
fraction is at least `0.999`.

## Compound Command Ordering

The `/pose_command` callback is deliberately sequential:

1. Validate that all six numeric pose values are finite.
2. Plan and execute the arm motion selected by `cartesian_path`.
3. If and only if the arm execution succeeds, read
   `sunyijie_gripper` and execute `gripper_close` or `gripper_open`.
4. Log the result of both stages with the requested pose and personal field.

This ordering makes a near-ground `true` command close only after reaching the
pickup pose, and a destination `false` command open only after reaching the
placement pose. A failed arm plan does not unexpectedly release or close the
gripper.

## Concurrency

MoveIt planning and execution are synchronous from the callback's point of
view, but their action and state callbacks must continue to run. The executable
therefore uses a multi-threaded executor. Command subscriptions use a dedicated
mutually-exclusive callback group, while MoveIt client callbacks remain in the
node's default group. This prevents action-client deadlock and prevents two
user commands from planning against the same robot simultaneously.

## Input and Failure Handling

- Reject a joint command unless it contains exactly six finite values.
- Reject a pose command containing NaN or infinity.
- Clear pose targets after normal pose planning.
- Report planning, Cartesian fraction, execution, and gripper failures.
- Do not send a gripper command after an arm failure.
- Catch standard exceptions at callback boundaries so one invalid command does
  not terminate the node.
- Preserve the existing velocity, acceleration, collision, and controller
  limits; the commander does not bypass MoveIt or ros2_control.

## Launch and User Flow

The existing `my_robot_moveit_config` demo launch will also start the commander
and pass the same robot description, semantic model, kinematics, and planning
parameters used by MoveIt. The recording flow becomes:

1. Launch `my_robot_moveit_config demo.launch.py` once.
2. In a visible terminal, publish successive one-shot `/pose_command`
   messages.
3. Observe arm motion, Cartesian vertical segments, base rotation, and gripper
   state changes in RViz.

The commander README will contain a verified command sequence for approach,
near-ground close, vertical lift, base rotation and transfer, near-ground
placement, and open release. Every command will use `sunyijie_gripper`.

## Testing Strategy

Follow a red-green sequence before production logic:

1. Add failing static contracts for the exact message fields, package
   dependencies, installed executable, demo-launch integration, topic names,
   and required personal identifier.
2. Add failing C++ unit tests for finite-value validation, RPY conversion, and
   `true`/`false` named-target mapping.
3. Implement the minimum message package, utilities, commander, and launch
   integration required to pass.
4. Run all local static tests, then build and test the ROS packages on Ubuntu
   24.04 with ROS 2 Jazzy.

Runtime acceptance on the VM must prove:

- `ros2 interface show my_moveit_interfaces/msg/PoseCommand` displays the
  exact eight-field contract.
- the demo launch starts the commander and all three existing controllers are
  active.
- `/pose_command` has the expected subscriber.
- a normal planned pose succeeds.
- a complete Cartesian segment succeeds.
- a `true` command reaches the closed joint value and a `false` command reaches
  the open joint value.
- a multi-command sequence visibly performs pickup, lift, rotation/transfer,
  placement, and release in RViz.

## Delivery

After fresh verification, commit intentional changes, synchronize local
`main`, `origin/main`, and `/home/jay/moveit_ws` on the VM, and leave the VM at
the verified commit. The user will perform the final screen recording; no
video recording or external group upload is in scope.

## Out of Scope

- physics-based object attachment or grasp simulation
- Gazebo integration
- real hardware drivers
- changing the existing gripper geometry, MoveIt group, or controller limits
- simultaneous arm and gripper trajectory execution
- automatic recording or sending a video to the class group
