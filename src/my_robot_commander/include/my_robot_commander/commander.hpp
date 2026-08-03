#pragma once

#include <memory>
#include <string>
#include <vector>

#include <moveit/move_group_interface/move_group_interface.hpp>
#include <my_moveit_interfaces/msg/pose_command.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>

#include "my_robot_commander/command_utils.hpp"

namespace my_robot_commander
{
class MyRobotCommander
{
public:
  explicit MyRobotCommander(rclcpp::Node::SharedPtr node);

private:
  using MoveGroupInterface =
    moveit::planning_interface::MoveGroupInterface;

  bool planAndExecute(MoveGroupInterface & move_group);
  bool goToNamedTarget(
    MoveGroupInterface & move_group, const std::string & target_name);
  bool goToJointTarget(const std::vector<double> & joint_values);
  bool goToPoseTarget(
    const PoseCommandValues & values, bool cartesian_path);
  bool moveSunyijieGripper(bool sunyijie_gripper);

  void gripperCommandCallback(const std_msgs::msg::Bool::SharedPtr msg);
  void jointCommandCallback(
    const std_msgs::msg::Float64MultiArray::SharedPtr msg);
  void poseCommandCallback(
    const my_moveit_interfaces::msg::PoseCommand::SharedPtr msg);

  rclcpp::Node::SharedPtr node_;
  MoveGroupInterface arm_move_group_;
  MoveGroupInterface gripper_move_group_;
  rclcpp::CallbackGroup::SharedPtr command_callback_group_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr
    gripper_subscription_;
  rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr
    joint_subscription_;
  rclcpp::Subscription<my_moveit_interfaces::msg::PoseCommand>::SharedPtr
    pose_subscription_;
};
}  // namespace my_robot_commander
