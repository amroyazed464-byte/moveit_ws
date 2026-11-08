#!/usr/bin/env python3
"""Real ROS/Gazebo regression: bridge exists before delayed robot creation.

Run after building and sourcing install/setup.bash. Uses a separate ROS domain
and Gazebo partition, leaving the exhibition session untouched.
"""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

os.environ['ROS_DOMAIN_ID']='147'
os.environ['GZ_PARTITION']='heritage_robot_readiness_check'

import rclpy
from geometry_msgs.msg import Twist
from ament_index_python.packages import get_package_share_directory, get_package_prefix


def main():
    share=Path(get_package_share_directory('heritage_robot'))
    os.environ['GZ_SIM_RESOURCE_PATH']=str(share/'models')
    rclpy.init()
    node=rclpy.create_node('readiness_check')
    probe=node.create_publisher(Twist,'/heritage_robot/cmd_vel',10)
    commands=[]
    node.create_subscription(Twist,'/heritage_robot/cmd_vel',lambda msg: commands.append(msg.linear.x),10)
    processes=[]
    with tempfile.TemporaryDirectory(prefix='heritage-ready-') as directory:
        directory=Path(directory)
        log=(directory/'process.log').open('w')
        def start(args):
            process=subprocess.Popen(args,stdout=log,stderr=log,start_new_session=True)
            processes.append(process)
            return process
        def spin(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                rclpy.spin_once(node,timeout_sec=.05)
        try:
            start(['ros2','run','ros_gz_bridge','parameter_bridge','--ros-args','-p','config_file:='+str(share/'config/bridge.yaml')])
            deadline=time.monotonic()+8
            # Includes our own subscriber; the second subscriber is the bridge.
            while probe.get_subscription_count()<2:
                assert time.monotonic()<deadline,'Bridge did not connect'
                spin(.1)
            executable=Path(get_package_prefix('heritage_robot'))/'lib/heritage_robot/drive_robot.py'
            driver=start([str(executable),'--linear','.2','--seconds','.5'])
            spin(3)
            assert not any(abs(v)>.001 for v in commands),'Motion sent before robot odometry exists'
            assert driver.poll() is None,'Motion timer expired before the robot was ready'
            world=directory/'check.sdf'
            world.write_text('''<sdf version="1.9"><world name="ready_check">
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
<model name="floor"><static>true</static><link name="body"><collision name="floor"><geometry><plane><normal>0 0 1</normal><size>10 10</size></plane></geometry></collision></link></model>
<include><uri>model://heritage_guide</uri><pose>0 0 .012 0 0 0</pose></include>
</world></sdf>''')
            start(['gz','sim','-s','-r',str(world)])
            deadline=time.monotonic()+8
            while driver.poll() is None and time.monotonic()<deadline:
                spin(.1)
            spin(.2)
            assert driver.poll()==0,'Driver failed after robot became ready'
            assert any(abs(v-.2)<.001 for v in commands),'No motion after robot readiness'
            assert abs(commands[-1])<.001,'Final command must stop the robot'
            print('PASS: no premature motion; delayed robot starts command, then receives stop')
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
            for process in processes:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL)
                    process.wait()
            log.close()
            node.destroy_node()
            rclpy.shutdown()


if __name__=='__main__':
    main()
