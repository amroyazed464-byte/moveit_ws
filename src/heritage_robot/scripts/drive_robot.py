#!/usr/bin/env python3
"""Send a bounded velocity command, then explicitly stop the simulated guide."""
import argparse
import math
import time
import rclpy
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linear', type=float, default=0.0, help='Forward speed in m/s (-0.35..0.35)')
    parser.add_argument('--angular', type=float, default=0.0, help='Turn speed in rad/s (-0.8..0.8)')
    parser.add_argument('--seconds', type=float, default=3.0, help='Wall-clock duration (0..30 seconds)')
    args, ros_args = parser.parse_known_args()
    if not all(math.isfinite(v) for v in (args.linear,args.angular,args.seconds)) or abs(args.linear)>.35 or abs(args.angular)>.8 or not 0<args.seconds<=30:
        parser.error('Use finite speeds within the stated limits and 0 < seconds <= 30')
    rclpy.init(args=ros_args, signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('heritage_guide_drive')
    publisher = node.create_publisher(Twist, '/heritage_robot/cmd_vel', 10)
    ready = False
    def on_odometry(_message):
        nonlocal ready
        ready = True
    node.create_subscription(Odometry, '/heritage_robot/odom', on_odometry, 10)
    command = Twist(); command.linear.x=args.linear; command.angular.z=args.angular
    try:
        deadline=time.monotonic()+10
        while publisher.get_subscription_count()==0 or not ready:
            if time.monotonic()>deadline:
                raise RuntimeError('Robot control/odometry not ready; start exhibition.launch.py first')
            rclpy.spin_once(node,timeout_sec=.1)
        deadline=time.monotonic()+args.seconds
        while time.monotonic()<deadline:
            publisher.publish(command)
            rclpy.spin_once(node,timeout_sec=.05)
    except KeyboardInterrupt:
        pass
    finally:
        for _ in range(5):
            publisher.publish(Twist())
            rclpy.spin_once(node,timeout_sec=.05)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
