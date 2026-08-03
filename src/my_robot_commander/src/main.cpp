#include <memory>

#include <rclcpp/rclcpp.hpp>

#include "my_robot_commander/commander.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  const auto options = rclcpp::NodeOptions()
    .automatically_declare_parameters_from_overrides(true);
  auto node = std::make_shared<rclcpp::Node>(
    "my_robot_commander", options);
  auto commander =
    std::make_shared<my_robot_commander::MyRobotCommander>(node);

  rclcpp::executors::MultiThreadedExecutor executor(
    rclcpp::ExecutorOptions(), 2);
  executor.add_node(node);
  executor.spin();
  executor.remove_node(node);

  commander.reset();
  node.reset();
  rclcpp::shutdown();
  return 0;
}
