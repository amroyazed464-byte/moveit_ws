cmake_minimum_required(VERSION 3.22)
project(my_robot_commander)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(moveit_msgs REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(my_moveit_interfaces REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2 REQUIRED)

add_library(command_utils src/command_utils.cpp)
target_include_directories(command_utils PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(command_utils geometry_msgs tf2)

add_executable(my_robot_commander
  src/main.cpp
  src/commander.cpp
)
target_include_directories(my_robot_commander PRIVATE include)
target_link_libraries(my_robot_commander command_utils)
ament_target_dependencies(my_robot_commander
  geometry_msgs
  moveit_msgs
  moveit_ros_planning_interface
  my_moveit_interfaces
  rclcpp
  std_msgs
)

install(DIRECTORY include/ DESTINATION include)
install(
  TARGETS command_utils
  EXPORT command_utilsTargets
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(
  TARGETS my_robot_commander
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_command_utils test/test_command_utils.cpp)
  target_include_directories(test_command_utils PRIVATE include)
  target_link_libraries(test_command_utils command_utils)
  ament_target_dependencies(test_command_utils geometry_msgs)
endif()

ament_export_targets(command_utilsTargets HAS_LIBRARY_TARGET)
ament_export_dependencies(geometry_msgs tf2)
ament_package()
