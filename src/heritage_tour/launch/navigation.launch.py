"""AMCL and Nav2 against the actual hall collision map."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share=Path(get_package_share_directory('heritage_tour'))
    params=str(share/'config/nav2.yaml')
    nodes=[Node(package='nav2_map_server',executable='map_server',name='map_server',
                parameters=[params,{'yaml_filename':str(share/'maps/hall.yaml')}],output='screen'),
           Node(package='nav2_amcl',executable='amcl',name='amcl',parameters=[params],output='screen'),
           Node(package='nav2_lifecycle_manager',executable='lifecycle_manager',name='lifecycle_manager_localization',
                parameters=[{'use_sim_time':True,'autostart':True,'node_names':['map_server','amcl'],'bond_timeout':30.0}],output='screen')]
    names=['planner_server','controller_server','smoother_server','behavior_server','bt_navigator']
    packages=['nav2_planner','nav2_controller','nav2_smoother','nav2_behaviors','nav2_bt_navigator']
    for package,name in zip(packages,names):
        nodes.append(Node(package=package,executable=name,name=name,parameters=[params],
                          remappings=[('cmd_vel','/nav2_cmd_vel'),('odom','/heritage_robot/odom')],output='screen'))
    nodes.append(Node(package='nav2_lifecycle_manager',executable='lifecycle_manager',name='lifecycle_manager_navigation',
                      parameters=[{'use_sim_time':True,'autostart':True,'node_names':names,'bond_timeout':30.0}],output='screen'))
    return LaunchDescription(nodes)
