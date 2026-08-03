cmake_minimum_required(VERSION 3.22)
project(my_robot_commander)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)

add_library(command_utils src/command_utils.cpp)
target_include_directories(command_utils PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(command_utils geometry_msgs tf2)

install(DIRECTORY include/ DESTINATION include)
install(
  TARGETS command_utils
  EXPORT command_utilsTargets
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
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
