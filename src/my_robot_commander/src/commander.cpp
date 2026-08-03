#include "my_robot_commander/commander.hpp"

#include <exception>
#include <functional>
#include <utility>

#include <moveit_msgs/msg/robot_trajectory.hpp>

namespace my_robot_commander
{
MyRobotCommander::MyRobotCommander(rclcpp::Node::SharedPtr node)
: node_(std::move(node)),
  arm_move_group_(node_, "arm"),
  gripper_move_group_(node_, "gripper")
{
  command_callback_group_ = node_->create_callback_group(
    rclcpp::CallbackGroupType::MutuallyExclusive);
  rclcpp::SubscriptionOptions options;
  options.callback_group = command_callback_group_;

  gripper_subscription_ = node_->create_subscription<std_msgs::msg::Bool>(
    "/gripper_command", rclcpp::QoS(10),
    std::bind(
      &MyRobotCommander::gripperCommandCallback, this,
      std::placeholders::_1), options);
  joint_subscription_ =
    node_->create_subscription<std_msgs::msg::Float64MultiArray>(
    "/joint_command", rclcpp::QoS(10),
    std::bind(
      &MyRobotCommander::jointCommandCallback, this,
      std::placeholders::_1), options);
  pose_subscription_ =
    node_->create_subscription<my_moveit_interfaces::msg::PoseCommand>(
    "/pose_command", rclcpp::QoS(10),
    std::bind(
      &MyRobotCommander::poseCommandCallback, this,
      std::placeholders::_1), options);

  RCLCPP_INFO(
    node_->get_logger(),
    "MoveIt commander ready on /gripper_command, /joint_command, and /pose_command");
}

bool MyRobotCommander::planAndExecute(MoveGroupInterface & move_group)
{
  MoveGroupInterface::Plan plan;
  const auto plan_result = move_group.plan(plan);
  if (plan_result != moveit::core::MoveItErrorCode::SUCCESS) {
    RCLCPP_ERROR(
      node_->get_logger(), "Planning failed for group %s",
      move_group.getName().c_str());
    return false;
  }

  const auto execute_result = move_group.execute(plan);
  if (execute_result != moveit::core::MoveItErrorCode::SUCCESS) {
    RCLCPP_ERROR(
      node_->get_logger(), "Execution failed for group %s",
      move_group.getName().c_str());
    return false;
  }
  return true;
}

bool MyRobotCommander::goToNamedTarget(
  MoveGroupInterface & move_group, const std::string & target_name)
{
  move_group.setStartStateToCurrentState();
  if (!move_group.setNamedTarget(target_name)) {
    RCLCPP_ERROR(
      node_->get_logger(), "Unknown target %s for group %s",
      target_name.c_str(), move_group.getName().c_str());
    return false;
  }
  return planAndExecute(move_group);
}

bool MyRobotCommander::goToJointTarget(
  const std::vector<double> & joint_values)
{
  arm_move_group_.setStartStateToCurrentState();
  if (!arm_move_group_.setJointValueTarget(joint_values)) {
    RCLCPP_ERROR(
      node_->get_logger(), "Arm joint target violates joint bounds");
    return false;
  }
  return planAndExecute(arm_move_group_);
}

bool MyRobotCommander::goToPoseTarget(
  const PoseCommandValues & values, bool cartesian_path)
{
  const auto pose = makePose(values);
  arm_move_group_.setStartStateToCurrentState();

  if (cartesian_path) {
    const std::vector<geometry_msgs::msg::Pose> waypoints{pose};
    moveit_msgs::msg::RobotTrajectory trajectory;
    const double fraction = arm_move_group_.computeCartesianPath(
      waypoints, 0.01, trajectory, true);
    RCLCPP_INFO(
      node_->get_logger(), "Cartesian path coverage: %.1f%%",
      fraction * 100.0);
    if (fraction < 0.999) {
      RCLCPP_ERROR(
        node_->get_logger(), "Cartesian path is incomplete");
      return false;
    }

    const auto execute_result = arm_move_group_.execute(trajectory);
    if (execute_result != moveit::core::MoveItErrorCode::SUCCESS) {
      RCLCPP_ERROR(
        node_->get_logger(), "Cartesian trajectory execution failed");
      return false;
    }
    return true;
  }

  arm_move_group_.setPoseTarget(pose);
  const bool succeeded = planAndExecute(arm_move_group_);
  arm_move_group_.clearPoseTargets();
  return succeeded;
}

bool MyRobotCommander::moveSunyijieGripper(bool sunyijie_gripper)
{
  return goToNamedTarget(
    gripper_move_group_,
    std::string(gripperNamedTarget(sunyijie_gripper)));
}

void MyRobotCommander::gripperCommandCallback(
  const std_msgs::msg::Bool::SharedPtr msg)
{
  try {
    const bool sunyijie_gripper = msg->data;
    if (!moveSunyijieGripper(sunyijie_gripper)) {
      RCLCPP_ERROR(node_->get_logger(), "Gripper command failed");
    }
  } catch (const std::exception & exception) {
    RCLCPP_ERROR(
      node_->get_logger(), "Gripper command failed: %s",
      exception.what());
  }
}

void MyRobotCommander::jointCommandCallback(
  const std_msgs::msg::Float64MultiArray::SharedPtr msg)
{
  try {
    if (!hasSixFiniteJointValues(msg->data)) {
      RCLCPP_ERROR(
        node_->get_logger(),
        "Joint command must contain exactly six finite values");
      return;
    }
    if (!goToJointTarget(msg->data)) {
      RCLCPP_ERROR(node_->get_logger(), "Joint command failed");
    }
  } catch (const std::exception & exception) {
    RCLCPP_ERROR(
      node_->get_logger(), "Joint command failed: %s",
      exception.what());
  }
}

void MyRobotCommander::poseCommandCallback(
  const my_moveit_interfaces::msg::PoseCommand::SharedPtr msg)
{
  try {
    const PoseCommandValues values{
      msg->x, msg->y, msg->z, msg->roll, msg->pitch, msg->yaw};
    if (!hasFinitePoseValues(values)) {
      RCLCPP_ERROR(
        node_->get_logger(), "Pose command must contain finite values");
      return;
    }

    if (!goToPoseTarget(values, msg->cartesian_path)) {
      RCLCPP_ERROR(
        node_->get_logger(),
        "Arm command failed; sunyijie_gripper was not executed");
      return;
    }
    if (!moveSunyijieGripper(msg->sunyijie_gripper)) {
      RCLCPP_ERROR(
        node_->get_logger(),
        "Arm succeeded but sunyijie_gripper command failed");
      return;
    }

    RCLCPP_INFO(
      node_->get_logger(),
      "Compound command succeeded at [%.3f, %.3f, %.3f]; sunyijie_gripper=%s",
      values.x, values.y, values.z,
      msg->sunyijie_gripper ? "true" : "false");
  } catch (const std::exception & exception) {
    RCLCPP_ERROR(
      node_->get_logger(), "Pose command failed: %s",
      exception.what());
  }
}
}  // namespace my_robot_commander
