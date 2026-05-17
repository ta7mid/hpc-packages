cmake_minimum_required(VERSION 3.18)
project(test_package C)

find_package(GlobalArrays REQUIRED CONFIG)
find_package(MPI          REQUIRED)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE GlobalArrays::ga MPI::MPI_C)
