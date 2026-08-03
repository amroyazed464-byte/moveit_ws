#include <cmath>
#include <limits>
#include <vector>

#include <gtest/gtest.h>

#include "my_robot_commander/command_utils.hpp"

namespace my_robot_commander
{
TEST(CommandUtils, RequiresExactlySixFiniteJointValues)
{
  EXPECT_TRUE(hasSixFiniteJointValues({0.0, 0.1, 0.2, 0.3, 0.4, 0.5}));
  EXPECT_FALSE(hasSixFiniteJointValues({0.0, 0.1, 0.2, 0.3, 0.4}));
  EXPECT_FALSE(hasSixFiniteJointValues(
    {0.0, 0.1, 0.2, std::numeric_limits<double>::quiet_NaN(), 0.4, 0.5}));
}

TEST(CommandUtils, ValidatesPoseAndConvertsRollPitchYaw)
{
  constexpr double pi = 3.14159265358979323846;
  PoseCommandValues values{0.7, 0.6, 0.4, pi, 0.0, 0.0};
  EXPECT_TRUE(hasFinitePoseValues(values));

  const auto pose = makePose(values);
  EXPECT_DOUBLE_EQ(0.7, pose.position.x);
  EXPECT_DOUBLE_EQ(0.6, pose.position.y);
  EXPECT_DOUBLE_EQ(0.4, pose.position.z);
  EXPECT_NEAR(1.0, pose.orientation.x, 1e-9);
  EXPECT_NEAR(0.0, pose.orientation.y, 1e-9);
  EXPECT_NEAR(0.0, pose.orientation.z, 1e-9);
  EXPECT_NEAR(0.0, pose.orientation.w, 1e-9);

  values.y = std::numeric_limits<double>::infinity();
  EXPECT_FALSE(hasFinitePoseValues(values));
}

TEST(CommandUtils, MapsPersonalBooleanToExistingNamedTargets)
{
  EXPECT_EQ("gripper_close", gripperNamedTarget(true));
  EXPECT_EQ("gripper_open", gripperNamedTarget(false));
}
}  // namespace my_robot_commander
