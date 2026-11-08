"""One launch for robot, perception, navigation, and offline guide console."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    tour=Path(get_package_share_directory('heritage_tour'))
    robot=Path(get_package_share_directory('heritage_robot'))
    return LaunchDescription([
        DeclareLaunchArgument('gui',default_value='true'),
        DeclareLaunchArgument('port',default_value='8765'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(robot/'launch/exhibition.launch.py')),
                                 launch_arguments={'gui':LaunchConfiguration('gui')}.items()),
        Node(package='ros_gz_bridge',executable='parameter_bridge',name='tour_sensor_bridge',
             parameters=[{'config_file':str(tour/'config/bridge.yaml')}],output='screen'),
        Node(package='tf2_ros',executable='static_transform_publisher',name='tour_laser_tf',
             arguments=['--x','0','--y','0','--z','1.58','--frame-id','base_link','--child-frame-id','laser_frame'],
             parameters=[{'use_sim_time':True}],output='screen'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(tour/'launch/navigation.launch.py'))),
        Node(package='heritage_tour',executable='tour_runtime.py',name='heritage_tour',
             parameters=[{'use_sim_time':True,'port':LaunchConfiguration('port')}],output='screen'),
    ])
