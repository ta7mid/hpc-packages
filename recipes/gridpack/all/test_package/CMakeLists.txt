cmake_minimum_required(VERSION 3.22)
project(test_package CXX)

find_package(GridPACK REQUIRED CONFIG)
find_package(MPI      REQUIRED)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE GridPACK::GridPACK MPI::MPI_CXX)
