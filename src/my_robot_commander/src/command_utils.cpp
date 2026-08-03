#include "my_robot_commander/command_utils.hpp"

#include <algorithm>
#include <array>
#include <cmath>

#include <tf2/LinearMath/Quaternion.h>

namespace my_robot_commander
{
bool hasSixFiniteJointValues(const std::vector<double> & joint_values)
{
  return joint_values.size() == 6 &&
         std::all_of(
    joint_values.begin(), joint_values.end(),
    [](double value) {return std::isfinite(value);});
}

bool hasFinitePoseValues(const PoseCommandValues & values)
{
  const std::array<double, 6> numeric_values{
    values.x, values.y, values.z, values.roll, values.pitch, values.yaw};
  return std::all_of(
    numeric_values.begin(), numeric_values.end(),
    [](double value) {return std::isfinite(value);});
}

geometry_msgs::msg::Pose makePose(const PoseCommandValues & values)
{
  geometry_msgs::msg::Pose pose;
  pose.position.x = values.x;
  pose.position.y = values.y;
  pose.position.z = values.z;

  tf2::Quaternion quaternion;
  quaternion.setRPY(values.roll, values.pitch, values.yaw);
  quaternion.normalize();
  pose.orientation.x = quaternion.x();
  pose.orientation.y = quaternion.y();
  pose.orientation.z = quaternion.z();
  pose.orientation.w = quaternion.w();
  return pose;
}

std::string_view gripperNamedTarget(bool sunyijie_gripper)
{
  return sunyijie_gripper ? "gripper_close" : "gripper_open";
}
}  // namespace my_robot_commander
