cmake_minimum_required(VERSION 3.8)
project(drone_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch meshes urdf config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()