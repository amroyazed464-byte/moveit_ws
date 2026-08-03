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
