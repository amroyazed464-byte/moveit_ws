#pragma once

#include <string_view>
#include <vector>

#include <geometry_msgs/msg/pose.hpp>

namespace my_robot_commander
{
struct PoseCommandValues
{
  double x;
  double y;
  double z;
  double roll;
  double pitch;
  double yaw;
};

bool hasSixFiniteJointValues(const std::vector<double> & joint_values);
bool hasFinitePoseValues(const PoseCommandValues & values);
geometry_msgs::msg::Pose makePose(const PoseCommandValues & values);
std::string_view gripperNamedTarget(bool sunyijie_gripper);
}  // namespace my_robot_commander
