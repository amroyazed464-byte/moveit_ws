# Sunyijie MoveIt compound control

## Start

Build the workspace, source `install/setup.bash`, and start MoveIt, RViz,
controllers, and the commander with one launch command:

```bash
ros2 launch my_robot_moveit_config demo.launch.py
```

In a second sourced terminal, publish the following commands one at a time.
The personalized field follows the assignment convention:
`sunyijie_gripper: true` closes the gripper and `false` opens it.

## Recording sequence

1. Move above the pickup point with the gripper open:

```bash
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.7, y: 0.6, z: 0.7, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: false, sunyijie_gripper: false}"
```

2. Descend vertically and close near the ground:

```bash
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.7, y: 0.6, z: 0.4, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: true, sunyijie_gripper: true}"
```

3. Lift vertically while keeping the gripper closed:

```bash
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.7, y: 0.6, z: 0.7, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: true, sunyijie_gripper: true}"
```

4. Rotate around the base and transfer to the new position:

```bash
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.6, y: -0.7, z: 0.7, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: false, sunyijie_gripper: true}"
```

5. Descend vertically and open near the ground:

```bash
ros2 topic pub -1 /pose_command my_moveit_interfaces/msg/PoseCommand "{x: 0.6, y: -0.7, z: 0.4, roll: 3.14, pitch: 0.0, yaw: 0.0, cartesian_path: true, sunyijie_gripper: false}"
```

Wait for each one-shot publisher to report that the message was published and
for RViz motion to finish before sending the next command.
