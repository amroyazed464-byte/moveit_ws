"""Start the existing stable hall, spawn the guide, and bridge control/odometry."""
import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot = Path(get_package_share_directory('heritage_robot'))
    hall = Path(get_package_share_directory('heritage_hall'))
    paths = str(robot / 'models') + os.pathsep + os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true'),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', paths),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(hall / 'launch/hall.launch.py')),
                                 launch_arguments={'gui': LaunchConfiguration('gui')}.items()),
        Node(package='ros_gz_sim', executable='create', name='spawn_heritage_guide', output='screen',
             arguments=['-world', 'heritage_hall', '-file', str(robot / 'models/heritage_guide/model.sdf'),
                        '-name', 'heritage_guide', '-x', '-13.27', '-y', '-7.73', '-z', '.012', '-Y', '1.5707963']),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='heritage_guide_bridge',
             parameters=[{'config_file': str(robot / 'config/bridge.yaml')}], output='screen'),
    ])
