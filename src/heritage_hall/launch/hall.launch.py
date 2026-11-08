"""Start the museum without changing the existing MoveIt demonstration."""
import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import EnvironmentVariable, LaunchConfiguration


def generate_launch_description():
    share = Path(get_package_share_directory('heritage_hall'))
    resource = [str(share.parent), os.pathsep, EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value='')]
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true'),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', resource),
        ExecuteProcess(cmd=[str(share.parent.parent / 'lib/heritage_hall/start_hall.sh'),
                            LaunchConfiguration('gui'), str(share)], output='screen'),
    ])
